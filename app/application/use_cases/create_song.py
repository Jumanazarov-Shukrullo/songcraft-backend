"""Create Song Use Case"""

from typing import Optional
from datetime import datetime
from ...domain.entities.song import Song
from ...domain.value_objects.entity_ids import SongId, UserId, OrderId
from ...domain.value_objects.song_content import Lyrics
from ...domain.enums import GenerationStatus, MusicStyle
from ...domain.repositories.unit_of_work import IUnitOfWork
from ...infrastructure.external_services.ai_service import AIService
from ...application.dtos.song_dtos import CreateSongRequest, SongResponse


class CreateSongUseCase:
    """Use case for creating a new song"""
    
    def __init__(self, unit_of_work: IUnitOfWork, ai_service: AIService):
        self.unit_of_work = unit_of_work
        self.ai_service = ai_service
    
    async def execute(self, song_data: CreateSongRequest, user_id: int) -> SongResponse:
        """Execute the create song use case"""
        async with self.unit_of_work:
            # Create song entity
            song = Song(
                id=SongId.generate(),
                user_id=UserId(user_id),
                order_id=OrderId(song_data.order_id),
                music_style=song_data.music_style,
                title=f"Song for Order {song_data.order_id}"
            )
            
            # Generate lyrics using AI service
            try:
                song.start_lyrics_generation()
                
                lyrics_content = await self.ai_service.generate_lyrics(
                    description=song_data.description,
                    music_style=song_data.music_style.value
                )
                lyrics = Lyrics(lyrics_content)
                song.complete_lyrics_generation(lyrics)
                
            except Exception as e:
                # If lyrics generation fails, leave status as in progress
                pass
            
            # Save to repository
            song_repo = self.unit_of_work.song_repository
            saved_song = song_repo.add(song)
            
            await self.unit_of_work.commit()
            
            # Convert to response DTO
            return SongResponse(
                id=saved_song.id.value,
                user_id=saved_song.user_id.value,
                order_id=saved_song.order_id.value,
                description=song_data.description,
                music_style=saved_song.music_style.value,
                status=saved_song.lyrics_status.value,
                lyrics=saved_song.lyrics.content if saved_song.lyrics else None,
                audio_url=saved_song.audio_url.url if saved_song.audio_url else None,
                video_url=saved_song.video_url.url if saved_song.video_url else None,
                duration=saved_song.duration.duration if saved_song.duration else None,
                created_at=saved_song.created_at
            ) 