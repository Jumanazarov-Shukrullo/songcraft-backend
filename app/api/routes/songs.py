"""Song routes with individual use case imports"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from ...application.use_cases.create_song import CreateSongUseCase
from ...application.use_cases.upload_song_images import UploadSongImagesUseCase
from ...application.dtos.song_dtos import CreateSongRequest, SongResponse, GenerateLyricsRequest
from ...api.dependencies import get_unit_of_work, get_storage_service, get_ai_service, get_current_user
from ...domain.entities.user import User
from ...domain.enums import MusicStyle, EmotionalTone


router = APIRouter(tags=["songs"])


@router.get("/music-styles")
async def get_music_styles():
    """Get available music styles"""
    return {
        "styles": [
            {"value": style.value, "label": style.value.title()}
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
    return await use_case.execute(song_data, current_user.id)


@router.post("/{song_id}/images")
async def upload_song_images(
    song_id: int,
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work),
    storage_service = Depends(get_storage_service)
):
    """Upload images for a song"""
    use_case = UploadSongImagesUseCase(unit_of_work, storage_service)
    return await use_case.execute(song_id, images, current_user.id)


@router.get("/{song_id}", response_model=SongResponse)
async def get_song(
    song_id: int,
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work)
):
    """Get song by ID"""
    song_repo = unit_of_work.song_repository
    song = song_repo.get_by_id(song_id)
    
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
        description=song.content.description,
        music_style=song.content.music_style.value,
        status=song.generation_status.value,
        lyrics=song.content.lyrics.content if song.content.lyrics else None,
        audio_url=song.content.audio_url.url if song.content.audio_url else None,
        video_url=song.content.video_url.url if song.content.video_url else None,
        duration=song.content.duration.duration if song.content.duration else None,
        created_at=song.created_at
    )


@router.get("/", response_model=List[SongResponse])
async def get_user_songs(
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work)
):
    """Get all songs for current user"""
    song_repo = unit_of_work.song_repository
    songs = song_repo.get_by_user_id(current_user.id)
    
    response_songs = []
    for song in songs:
        response_songs.append(SongResponse(
            id=song.id.value,
            user_id=song.user_id.value,
            order_id=song.order_id.value,
            description=song.content.description,
            music_style=song.content.music_style.value,
            status=song.generation_status.value,
            lyrics=song.content.lyrics.content if song.content.lyrics else None,
            audio_url=song.content.audio_url.url if song.content.audio_url else None,
            video_url=song.content.video_url.url if song.content.video_url else None,
            duration=song.content.duration.duration if song.content.duration else None,
            created_at=song.created_at
        ))
    
    return response_songs


@router.get("/health")
async def songs_health():
    """Songs health check"""
    return {"status": "ok", "service": "songs"}
