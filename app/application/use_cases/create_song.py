"""Create Song Use Case"""

from typing import Optional
from datetime import datetime
from decimal import Decimal
from ...domain.entities.song import Song
from ...domain.entities.order import Order
from ...domain.value_objects.entity_ids import SongId, UserId, OrderId
from ...domain.value_objects.song_content import Lyrics, AudioUrl, Duration
from ...domain.value_objects.money import Money
from ...domain.enums import GenerationStatus, MusicStyle, ProductType, OrderStatus, EmotionalTone
from ...domain.repositories.unit_of_work import IUnitOfWork
from ...infrastructure.external_services.ai_service import AIService
from ...application.dtos.song_dtos import CreateSongRequest, SongResponse
from ...api.event_broadcaster import broadcaster


class CreateSongUseCase:
    """Use case for creating a new song"""
    
    def __init__(self, unit_of_work: IUnitOfWork, ai_service: AIService):
        self.unit_of_work = unit_of_work
        self.ai_service = ai_service
    
    async def execute(self, song_data: CreateSongRequest, user_id: int) -> SongResponse:
        """Execute the create song use case - now auto-creates a free order & triggers Suno audio"""
        async with self.unit_of_work:
            # 1. Create a free order automatically (no payment)
            order_repo = self.unit_of_work.orders
            # Temporary placeholder ID (will be replaced after flush)
            order = Order(
                id=OrderId(1),
                user_id=UserId(user_id),
                product_type=ProductType.AUDIO_ONLY,
                amount=Money(Decimal(0)),
                status=OrderStatus.PAID
            )
            saved_order = await order_repo.add(order)

            # 2. Create song entity linked to this order
            style_enum = song_data.music_style if isinstance(song_data.music_style, MusicStyle) else MusicStyle(song_data.music_style)

            # Map emotional tone if provided
            tone_enum = None
            if song_data.tone:
                tone_enum = song_data.tone if isinstance(song_data.tone, EmotionalTone) else EmotionalTone(song_data.tone)

            song = Song(
                id=SongId(1),  # Placeholder, will be updated by repository
                user_id=UserId(user_id),
                order_id=saved_order.id,
                title=song_data.title,
                description=song_data.description,
                music_style=style_enum,
                tone=tone_enum,
            )

            # 2a. Lyrics handling
            if song_data.lyrics:
                # Client already provided lyrics – mark as completed
                lyrics_vo = Lyrics(song_data.lyrics)
                song.start_lyrics_generation()
                song.complete_lyrics_generation(lyrics_vo)
                await broadcaster.notify(song.id.value, {
                    "lyrics_status": song.lyrics_status.value,
                    "status": song.generation_status.value,
                    "lyrics": song_data.lyrics
                })
            else:
                # We need to generate lyrics via AI
                song.start_lyrics_generation()
                ai_lyrics = await self.ai_service.generate_lyrics(
                    description=song_data.description,
                    music_style=style_enum.value
                )
                song.complete_lyrics_generation(Lyrics(ai_lyrics))
                await broadcaster.notify(song.id.value, {
                    "lyrics_status": song.lyrics_status.value,
                    "status": song.generation_status.value,
                    "lyrics": ai_lyrics
                })

            # 2b. Title handling – use client title if provided else generate
            if song_data.title:
                song.title = song_data.title
            else:
                generated_title = await self.ai_service.generate_title(song.lyrics.content)
                song.title = generated_title
                await broadcaster.notify(song.id.value, {"title": generated_title})

            # Save song to repository (ID will be set)
            song_repo = self.unit_of_work.songs
            saved_song = await song_repo.add(song)

            # Commit DB so song ID is generated before calling external services
            await self.unit_of_work.commit()

            # 3. Trigger Suno audio generation (fire-and-forget for now)
            if saved_song.lyrics:
                audio_result = await self.ai_service.generate_audio(
                    lyrics=saved_song.lyrics.content,
                    music_style=style_enum.value
                )
                if audio_result.get('status') == 'completed':
                    saved_song.complete_audio_generation(
                        AudioUrl(audio_result['audio_url']),
                        Duration(audio_result.get('duration', 180))
                    )
                    # Persist audio details
                    await song_repo.update(saved_song)
                    await self.unit_of_work.commit()
                    await broadcaster.notify(saved_song.id.value, {
                        "audio_status": saved_song.audio_status.value,
                        "video_status": saved_song.video_status.value,
                        "status": saved_song.generation_status.value,
                        "audio_url": audio_result['audio_url'],
                        "title": saved_song.title
                    })
                else:
                    # Mark audio generation failed for transparency
                    saved_song.audio_status = GenerationStatus.FAILED
                    saved_song.video_status = GenerationStatus.FAILED  # cascade fail
                    await song_repo.update(saved_song)
                    await self.unit_of_work.commit()
                    await broadcaster.notify(saved_song.id.value, {
                        "audio_status": saved_song.audio_status.value,
                        "video_status": saved_song.video_status.value,
                        "status": saved_song.generation_status.value,
                        "title": saved_song.title
                    })

            # 4. Return response DTO
            return SongResponse(
                id=saved_song.id.value,
                user_id=saved_song.user_id.value,
                order_id=saved_song.order_id.value,
                description=saved_song.description,
                music_style=style_enum.value,
                status=saved_song.generation_status.value,
                lyrics_status=saved_song.lyrics_status.value,
                audio_status=saved_song.audio_status.value,
                video_status=saved_song.video_status.value,
                lyrics=saved_song.lyrics.content if saved_song.lyrics else None,
                audio_url=saved_song.audio_url.url if saved_song.audio_url else None,
                video_url=saved_song.video_url.url if saved_song.video_url else None,
                duration=saved_song.duration.duration if saved_song.duration else None,
                created_at=saved_song.created_at,
                title=saved_song.title
            ) 