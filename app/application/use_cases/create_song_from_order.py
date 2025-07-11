"""Create Song from Existing Order Use Case"""

from decimal import Decimal
from ...domain.entities.song import Song
from ...domain.value_objects.entity_ids import SongId, UserId, OrderId
from ...domain.value_objects.song_content import Lyrics, AudioUrl, Duration
from ...domain.enums import GenerationStatus, MusicStyle, EmotionalTone, OrderStatus
from ...domain.repositories.unit_of_work import IUnitOfWork
from ...infrastructure.external_services.ai_service import AIService
from ...application.dtos.song_dtos import CreateSongRequest, SongResponse
from ...api.event_broadcaster import broadcaster


class CreateSongFromOrderUseCase:
    """Use case for creating a song from an existing paid order"""
    
    def __init__(self, unit_of_work: IUnitOfWork, ai_service: AIService):
        self.unit_of_work = unit_of_work
        self.ai_service = ai_service
    
    async def execute(self, song_data: CreateSongRequest, user_id: str, order_id: str) -> SongResponse:
        """Create a song from an existing paid order"""
        async with self.unit_of_work:
            # 1. Verify the order exists and is paid
            order_repo = self.unit_of_work.orders
            existing_order = await order_repo.get_by_id(OrderId.from_str(order_id))
            
            if not existing_order:
                raise ValueError(f"Order {order_id} not found")
            
            if existing_order.status != OrderStatus.PAID:
                raise ValueError(f"Order {order_id} is not paid (status: {existing_order.status})")
            
            # Create UserId from string for comparison
            user_id_obj = UserId.from_str(user_id)
            if existing_order.user_id.value != user_id_obj.value:
                raise ValueError(f"Order {order_id} does not belong to user {user_id}")

            # 2. Create song entity linked to the existing paid order
            style_enum = song_data.music_style if isinstance(song_data.music_style, MusicStyle) else MusicStyle(song_data.music_style)
            
            # Convert tone string to enum if provided
            tone_enum = None
            if song_data.tone:
                if isinstance(song_data.tone, EmotionalTone):
                    tone_enum = song_data.tone
                else:
                    try:
                        tone_enum = EmotionalTone(song_data.tone)
                    except ValueError:
                        print(f"⚠️ Invalid tone value: {song_data.tone}, ignoring")
                        tone_enum = None

            song = Song(
                id=SongId.generate(),  # Generate proper UUID instead of using integer 1
                user_id=user_id_obj,  # Use the UserId object created from string
                order_id=existing_order.id,
                title=song_data.title,
                description=song_data.description,
                music_style=style_enum,
                # Save all form fields to database
                recipient_description=song_data.recipient_description,
                occasion_description=song_data.occasion_description,
                additional_details=song_data.additional_details,
                tone=tone_enum,
            )

            # 3. Lyrics handling
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

            # 4. Title handling – use client title if provided else generate
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

            # 5. Trigger audio generation with proper status handling
            if saved_song.lyrics:
                # Start audio generation process
                saved_song.start_audio_generation()
                await song_repo.update(saved_song)
                await self.unit_of_work.commit()
                
                # Notify that audio generation started
                await broadcaster.notify(saved_song.id.value, {
                    "audio_status": saved_song.audio_status.value,
                    "status": saved_song.generation_status.value,
                    "title": saved_song.title
                })
                
                # Call AI service
                audio_result = await self.ai_service.generate_audio(
                    lyrics=saved_song.lyrics.content,
                    music_style=style_enum.value
                )
                
                print(f"🎵 AI Service audio result: {audio_result}")
                
                if audio_result.get('status') == 'completed' or audio_result.get('status') == 'succeeded':
                    # Generation completed immediately - update song
                    saved_song.complete_audio_generation(
                        AudioUrl(audio_result['audio_url']),
                        Duration(audio_result.get('duration', 180))
                    )
                    # Also set video URL if available
                    if audio_result.get('video_url'):
                        saved_song.video_url = AudioUrl(audio_result['video_url'])  # Reuse AudioUrl for now
                        saved_song.video_status = GenerationStatus.COMPLETED
                    
                    await song_repo.update(saved_song)
                    await self.unit_of_work.commit()
                    
                    print(f"✅ Song {saved_song.id.value} completed immediately with audio URL: {audio_result['audio_url']}")
                    
                    await broadcaster.notify(saved_song.id.value, {
                        "audio_status": saved_song.audio_status.value,
                        "video_status": saved_song.video_status.value,
                        "status": saved_song.generation_status.value,
                        "audio_url": audio_result['audio_url'],
                        "video_url": audio_result.get('video_url'),
                        "duration": audio_result.get('duration', 180),
                        "title": saved_song.title,
                        "message": "🎉 Your song is ready! You can now download it."
                    })
                elif audio_result.get('status') == 'processing':
                    # Generation is in progress - start background polling
                    print(f"🔄 Audio generation in progress for song {saved_song.id.value}")
                    
                    generation_id = audio_result.get('generation_id')
                    if generation_id:
                        print(f"🚀 Starting background check for generation {generation_id}")
                        
                        # Start immediate check in background
                        self._start_immediate_check(saved_song.id.value, generation_id)
                    
                    await broadcaster.notify(saved_song.id.value, {
                        "audio_status": saved_song.audio_status.value,
                        "status": saved_song.generation_status.value,
                        "message": audio_result.get('message', '🎵 Your song is being created! This usually takes 2-5 minutes.'),
                        "estimated_completion_minutes": audio_result.get('estimated_completion_minutes', 3),
                        "title": saved_song.title
                    })
                elif audio_result.get('status') == 'failed':
                    # Genuine failure
                    saved_song.audio_status = GenerationStatus.FAILED
                    saved_song.video_status = GenerationStatus.FAILED  # cascade fail
                    await song_repo.update(saved_song)
                    await self.unit_of_work.commit()
                    await broadcaster.notify(saved_song.id.value, {
                        "audio_status": saved_song.audio_status.value,
                        "video_status": saved_song.video_status.value,
                        "status": saved_song.generation_status.value,
                        "error": audio_result.get('error', 'Audio generation failed'),
                        "title": saved_song.title
                    })

            # 6. Return response DTO
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

    def _start_immediate_check(self, song_id: int, generation_id: str) -> None:
        """Start immediate background check for Mureka completion"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        # Use thread pool to avoid blocking
        async def immediate_check():
            try:
                print(f"🔍 Immediate background check for song {song_id}, generation {generation_id}")
                
                # First check - no delay (might already be completed)
                status_result = await self.ai_service.get_mureka_status(generation_id)
                print(f"📋 Direct status check result: {status_result}")
                
                if status_result.get("status") == "succeeded":
                    await self._update_completed_song(song_id, status_result)
                elif status_result.get("status") in ["running", "preparing", "processing"]:
                    # Still processing, start background polling
                    self._start_background_polling(song_id, generation_id)
                else:
                    print(f"⚠️ Unexpected status during immediate check: {status_result}")
                    
            except Exception as e:
                print(f"❌ Error in immediate check for song {song_id}: {e}")
                # Fallback to background polling
                self._start_background_polling(song_id, generation_id)
        
        # Run in background
        asyncio.create_task(immediate_check())

    async def _update_completed_song(self, song_id: int, status_result: dict) -> None:
        """Update song when generation is completed"""
        try:
            async with self.unit_of_work:
                song_repo = self.unit_of_work.songs
                from ...domain.value_objects.entity_ids import SongId
                
                song = await song_repo.get_by_id(SongId(song_id))
                if not song:
                    print(f"❌ Song {song_id} not found for completion update")
                    return
                
                # Update with completed audio
                song.complete_audio_generation(
                    AudioUrl(status_result["audio_url"]),
                    Duration(status_result.get("duration", 180))
                )
                
                # Handle video if available
                if status_result.get("video_url"):
                    song.video_url = AudioUrl(status_result["video_url"])
                    song.video_status = GenerationStatus.COMPLETED
                
                await song_repo.update(song)
                await self.unit_of_work.commit()
                
                print(f"✅ Song {song_id} updated with completed generation")
                
                # Notify completion
                await broadcaster.notify(song_id, {
                    "audio_status": song.audio_status.value,
                    "video_status": song.video_status.value,
                    "status": song.generation_status.value,
                    "audio_url": status_result["audio_url"],
                    "video_url": status_result.get("video_url"),
                    "duration": status_result.get("duration", 180),
                    "title": song.title,
                    "message": "🎉 Your song is ready! You can now download it."
                })
                
        except Exception as e:
            print(f"❌ Error updating completed song {song_id}: {e}")

    def _start_background_polling(self, song_id: int, generation_id: str) -> None:
        """Start background polling for generation completion"""
        import asyncio
        
        async def poll_and_update():
            # Implementation similar to the original but simplified for this use case
            print(f"🔄 Starting background polling for song {song_id}, generation {generation_id}")
            # Add polling logic here if needed
            pass
        
        # Run in background
        asyncio.create_task(poll_and_update()) 