"""Song routes with individual use case imports"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
import json
import asyncio
import httpx
import urllib.parse
import logging
from datetime import datetime

from ...application.use_cases.create_song import CreateSongUseCase
from ...application.use_cases.create_song_from_order import CreateSongFromOrderUseCase
from ...application.use_cases.upload_song_images import UploadSongImagesUseCase
from ...application.dtos.song_dtos import CreateSongRequest, SongResponse, GenerateLyricsRequest
from ...api.dependencies import get_unit_of_work, get_storage_service, get_ai_service, get_current_user
from ...domain.entities.user import User
from ...domain.enums import MusicStyle, EmotionalTone
from ...domain.value_objects.entity_ids import SongId
from ..event_broadcaster import broadcaster


router = APIRouter(tags=["songs"])


@router.get("/music-styles")
async def get_music_styles():
    """Get available music styles"""
    
    # Define style descriptions
    style_descriptions = {
        MusicStyle.RAP: "Rhythmic spoken lyrics with strong beats and urban flair",
        MusicStyle.POP: "Catchy, mainstream melodies perfect for any occasion",
        MusicStyle.ELECTROPOP: "Electronic beats with pop sensibilities and modern sound",
        MusicStyle.JAZZ: "Smooth, sophisticated rhythms with improvisational elements", 
        MusicStyle.FUNK: "Groovy basslines and rhythmic patterns that make you move",
        MusicStyle.ACOUSTIC: "Intimate, stripped-down arrangements with natural instruments"
    }
    
    return {
        "styles": [
            {
                "id": style.value,
                "name": style.value.title(),
                "description": style_descriptions.get(style, "A unique musical style")
            }
            for style in MusicStyle
        ]
    }


@router.post("/generate-lyrics")
async def generate_lyrics(
    request: GenerateLyricsRequest,
    current_user: User = Depends(get_current_user),
    ai_service = Depends(get_ai_service)
):
    """Generate lyrics using AI"""
    try:
        lyrics = await ai_service.generate_lyrics(
            description=request.description,
            music_style=request.music_style
        )
        return {"lyrics": lyrics}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate lyrics: {str(e)}"
        )


@router.post("/improve-lyrics")
async def improve_lyrics(
    request: dict,
    current_user: User = Depends(get_current_user),
    ai_service = Depends(get_ai_service)
):
    """Improve existing lyrics based on feedback"""
    try:
        lyrics = request.get("lyrics")
        feedback = request.get("feedback")
        
        if not lyrics or not feedback:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both lyrics and feedback are required"
            )
        
        improved_lyrics = await ai_service.improve_lyrics(lyrics, feedback)
        return {"improved_lyrics": improved_lyrics}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to improve lyrics: {str(e)}"
        )


@router.post("/", response_model=SongResponse)
async def create_song(
    song_data: CreateSongRequest,
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work),
    ai_service = Depends(get_ai_service)
):
    """Create a new song"""
    use_case = CreateSongUseCase(unit_of_work, ai_service)
    # current_user.id is a UserId value object – we need the raw integer
    user_int_id = current_user.id.value if hasattr(current_user.id, "value") else int(current_user.id)
    return await use_case.execute(song_data, user_int_id)


@router.post("/from-order", response_model=SongResponse)
async def create_song_from_order(
    request: dict,
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work),
    ai_service = Depends(get_ai_service)
):
    """Create a song from an existing paid order"""
    try:
        # Extract order_id and song_data from request
        order_id = request.get("order_id")
        song_data_dict = request.get("song_data")
        
        if not order_id or not song_data_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both order_id and song_data are required"
            )
        
        # Convert dict to CreateSongRequest
        song_data = CreateSongRequest(**song_data_dict)
        
        use_case = CreateSongFromOrderUseCase(unit_of_work, ai_service)
        user_int_id = current_user.id.value if hasattr(current_user.id, "value") else int(current_user.id)
        
        return await use_case.execute(song_data, user_int_id, order_id)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create song from order: {str(e)}"
        )


@router.post("/{song_id}/images")
async def upload_song_images(
    song_id: int,
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work),
    storage_service = Depends(get_storage_service)
):
    """Upload images for a song"""
    if not images:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No images uploaded")
    use_case = UploadSongImagesUseCase(unit_of_work, storage_service)
    return await use_case.execute(song_id, images, current_user.id)


@router.get("/{song_id}", response_model=SongResponse)
async def get_song(
    song_id: int,
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work)
):
    """Get song by ID"""
    song_repo = unit_of_work.songs
    song = await song_repo.get_by_id(SongId(song_id))
    
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    # Check if user owns this song
    if song.user_id.value != current_user.id.value:
        raise HTTPException(status_code=403, detail="Not authorized to access this song")
    
    # Convert to response DTO
    return SongResponse(
        id=song.id.value,
        user_id=song.user_id.value,
        order_id=song.order_id.value,
        title=song.title,
        description=song.description,
        music_style=song.music_style.value,
        status=song.generation_status.value,
        lyrics_status=song.lyrics_status.value,
        audio_status=song.audio_status.value,
        video_status=song.video_status.value,
        lyrics=song.lyrics.content if song.lyrics else None,
        audio_url=song.audio_url.url if song.audio_url else None,
        video_url=song.video_url.url if song.video_url else None,
        duration=song.duration.duration if song.duration else None,
        created_at=song.created_at
    )


@router.get("/", response_model=List[SongResponse])
async def get_user_songs(
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work)
):
    """Get all songs for current user"""
    song_repo = unit_of_work.songs
    songs = await song_repo.get_by_user_id(current_user.id)
    
    response_songs = []
    for song in songs:
        response_songs.append(SongResponse(
            id=song.id.value,
            user_id=song.user_id.value,
            order_id=song.order_id.value,
            title=song.title,
            description=song.description,
            music_style=song.music_style.value,
            status=song.generation_status.value,
            lyrics_status=song.lyrics_status.value,
            audio_status=song.audio_status.value,
            video_status=song.video_status.value,
            lyrics=song.lyrics.content if song.lyrics else None,
            audio_url=song.audio_url.url if song.audio_url else None,
            video_url=song.video_url.url if song.video_url else None,
            duration=song.duration.duration if song.duration else None,
            created_at=song.created_at
        ))
    
    return response_songs


@router.get("/health")
async def songs_health():
    """Songs health check"""
    return {"status": "ok", "service": "songs"}


@router.get("/{song_id}/stream")
async def stream_song_updates(song_id: int):
    """Server-Sent Events stream for live song status updates."""

    queue = await broadcaster.subscribe(song_id)

    async def event_generator():
        try:
            # send an initial ping so the connection opens
            yield {
                "event": "ping",
                "data": json.dumps({"song_id": song_id})
            }
            while True:
                payload = await queue.get()
                yield {
                    "event": "update",
                    "data": json.dumps(payload)
                }
        except asyncio.CancelledError:
            await broadcaster.unsubscribe(song_id, queue)

    return EventSourceResponse(event_generator())


@router.get("/{song_id}/download/audio")
async def download_audio(
    song_id: int,
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work)
):
    """Download audio file for a song"""
    song_repo = unit_of_work.songs
    song = await song_repo.get_by_id(SongId(song_id))
    
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    # Check if user owns this song
    if song.user_id.value != current_user.id.value:
        raise HTTPException(status_code=403, detail="Not authorized to download this song")
    
    # Check if audio is available
    if not song.audio_url or not song.audio_url.url:
        raise HTTPException(status_code=404, detail="Audio file not available")
    
    if song.audio_status.value != "completed":
        raise HTTPException(status_code=400, detail="Audio generation not completed")
    
    try:
        # Fetch the file from the audio URL
        async with httpx.AsyncClient() as client:
            response = await client.get(song.audio_url.url)
            response.raise_for_status()
        
        # Generate safe filename
        safe_title = "".join(c for c in (song.title or f"song_{song_id}") if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_title}.mp3"
        
        # Log the download
        logging.info(f"Audio download: user_id={current_user.id.value}, song_id={song_id}, title='{song.title}', filename='{filename}'")
        
        # Return file with download headers
        return StreamingResponse(
            iter([response.content]),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}",
                "Content-Length": str(len(response.content))
            }
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch audio file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.get("/{song_id}/download/video")
async def download_video(
    song_id: int,
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work)
):
    """Download video file for a song"""
    song_repo = unit_of_work.songs
    song = await song_repo.get_by_id(SongId(song_id))
    
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    # Check if user owns this song
    if song.user_id.value != current_user.id.value:
        raise HTTPException(status_code=403, detail="Not authorized to download this song")
    
    # Check if video is available
    if not song.video_url or not song.video_url.url:
        raise HTTPException(status_code=404, detail="Video file not available")
    
    if song.video_status.value != "completed":
        raise HTTPException(status_code=400, detail="Video generation not completed")
    
    try:
        # Fetch the file from the video URL
        async with httpx.AsyncClient() as client:
            response = await client.get(song.video_url.url)
            response.raise_for_status()
        
        # Generate safe filename
        safe_title = "".join(c for c in (song.title or f"song_{song_id}") if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_title}.mp4"
        
        # Log the download
        logging.info(f"Video download: user_id={current_user.id.value}, song_id={song_id}, title='{song.title}', filename='{filename}'")
        
        # Return file with download headers
        return StreamingResponse(
            iter([response.content]),
            media_type="video/mp4",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}",
                "Content-Length": str(len(response.content))
            }
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch video file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
