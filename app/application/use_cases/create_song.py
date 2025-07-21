"""Create Song Use Case"""

import asyncio
from typing import Optional
from datetime import datetime
from decimal import Decimal
from typing import Union
from ...domain.entities.song import Song
from ...domain.entities.order import Order
from ...domain.value_objects.entity_ids import SongId, UserId, OrderId
from ...domain.value_objects.song_content import Lyrics, AudioUrl, Duration
from ...domain.value_objects.money import Money
from ...domain.enums import GenerationStatus, MusicStyle, ProductType, OrderStatus, EmotionalTone
from ...domain.repositories.unit_of_work import IUnitOfWork
from ...infrastructure.external_services.ai_service import AIService
from ...infrastructure.repositories.unit_of_work_impl import UnitOfWorkImpl
from ...db.database import SessionLocal
from ...application.dtos.song_dtos import CreateSongRequest, SongResponse
from ...api.event_broadcaster import broadcaster
from uuid import UUID


class CreateSongUseCase:
    """Use case for creating a new song"""
    
    def __init__(self, unit_of_work: IUnitOfWork, ai_service: AIService):
        self.unit_of_work = unit_of_work
        self.ai_service = ai_service
    
    async def execute(self, song_data: CreateSongRequest, user_id: Union[int, UserId]) -> SongResponse:
        """Execute the create song use case - creates a free order and song"""
        async with self.unit_of_work:
            # Handle user_id - it might already be a UserId object or a string/integer
            if isinstance(user_id, UserId):
                user_id_obj = user_id
            else:
                # Convert to string first, then create UserId from string
                user_id_str = str(user_id)
                user_id_obj = UserId.from_str(user_id_str)
            
            # 1. Check and consume user's song credit before creating song
            user_repo = self.unit_of_work.users
            user = await user_repo.get_by_id(user_id_obj)
            if not user:
                raise ValueError("User not found")
                
            if not user.has_song_credits():
                raise ValueError("No song credits available. Please purchase credits to create a song.")
                
            # Consume one credit
            user.consume_song_credit()
            await user_repo.update(user)
            print(f"💳 Consumed 1 credit for user {user_id_obj.value}. Remaining credits: {user.song_credits}")
            
            # 2. Create a free order for direct song creation (backwards compatibility)
            order_repo = self.unit_of_work.orders
            # Generate proper UUID for the order
            order = Order(
                id=OrderId.generate(),
                user_id=user_id_obj,
                product_type=ProductType.AUDIO_ONLY,
                amount=Money(Decimal(0)),
                status=OrderStatus.PAID
            )
            saved_order = await order_repo.add(order)

            # 3. Create song entity linked to this order
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
                id=SongId.generate(),  # Generate proper UUID for the song
                user_id=user_id_obj,
                order_id=saved_order.id,
                title=song_data.title,
                description=song_data.description,
                music_style=style_enum,
                # Save all form fields to database
                recipient_description=song_data.recipient_description,
                occasion_description=song_data.occasion_description,
                additional_details=song_data.additional_details,
                tone=tone_enum,
            )

            # 3a. Lyrics handling
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

            # 3b. Title handling – use client title if provided else generate
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

            # 3. Trigger audio generation with proper status handling
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
                    # We'll update the song status later when polling completes
                    print(f"🔄 Audio generation in progress for song {saved_song.id.value}")
                    
                    generation_id = audio_result.get('generation_id')
                    if generation_id:
                        print(f"🚀 Starting background check for generation {generation_id}")
                        
                        # Since Mureka often completes very quickly, check immediately in background
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

    def _start_immediate_check(self, song_id: UUID, generation_id: str) -> None:
        """Start immediate background check for Mureka completion"""
        async def immediate_check():
            try:
                print(f"🔍 Immediate background check for song {song_id}, generation {generation_id}")
                
                # First check - no delay (might already be completed)
                status_result = await self.ai_service.get_mureka_status(generation_id)
                print(f"📋 Direct status check result: {status_result}")
                
                if status_result.get("status") == "succeeded":
                    await self._update_completed_song(song_id, status_result)
                elif status_result.get("status") in ["running", "preparing", "processing"]:
                    print(f"⏳ Song {song_id} still processing, will check again in 30 seconds...")
                    
                    # Wait and check again
                    await asyncio.sleep(30)
                    
                    # Check one more time
                    final_status = await self.ai_service.get_mureka_status(generation_id)
                    if final_status.get("status") == "succeeded":
                        await self._update_completed_song(song_id, final_status)
                    else:
                        print(f"⏳ Song {song_id} still not ready after second check")
                        await broadcaster.notify(song_id, {
                            "message": "🎵 Your song is still being created. Check your Dashboard in a few minutes.",
                            "estimated_completion_minutes": 3
                        })
                else:
                    print(f"❌ Unexpected status for song {song_id}: {status_result.get('status')}")
                    
            except Exception as e:
                print(f"❌ Error in immediate check for song {song_id}: {e}")
                import traceback
                traceback.print_exc()
        
        # Start the immediate check task
        import asyncio
        loop = asyncio.get_event_loop()
        task = loop.create_task(immediate_check())
        
        # Add task reference to prevent garbage collection
        if not hasattr(self, '_check_tasks'):
            self._check_tasks = set()
        self._check_tasks.add(task)
        task.add_done_callback(self._check_tasks.discard)
        
        print(f"🚀 Immediate check task started for song {song_id}")

    async def _update_completed_song(self, song_id: UUID, status_result: dict) -> None:
        """Helper method to update a completed song in the database"""
        try:
            print(f"✅ Song {song_id} completed! Updating database...")
            
            # Create new database session
            session = SessionLocal()
            try:
                unit_of_work = UnitOfWorkImpl(session)
                async with unit_of_work:
                    song_repo = unit_of_work.songs
                    song = await song_repo.get_by_id(SongId(song_id))  # song_id is already UUID
                    
                    if not song:
                        print(f"❌ Song {song_id} not found")
                        return
                    
                    # Extract audio URL from the response
                    audio_url = status_result.get("audio_url")
                    duration = status_result.get("duration", 180)
                    
                    if audio_url:
                        print(f"🎧 Updating song {song_id} with audio URL: {audio_url}")
                        print(f"⏱️ Duration: {duration} seconds")
                        
                        # Update song with completed audio
                        song.complete_audio_generation(
                            AudioUrl(audio_url),
                            Duration(duration)
                        )
                        
                        await song_repo.update(song)
                        await unit_of_work.commit()
                        
                        print(f"💾 Song {song_id} successfully updated in database")
                        
                        # Broadcast completion to frontend
                        await broadcaster.notify(song_id, {
                            "audio_status": song.audio_status.value,
                            "video_status": song.video_status.value,
                            "status": song.generation_status.value,
                            "audio_url": audio_url,
                            "duration": duration,
                            "title": song.title,
                            "message": "🎉 Your song is ready! You can now download it."
                        })
                        
                        print(f"📡 Completion notification sent for song {song_id}")
                    else:
                        print(f"❌ No audio URL found in status result for song {song_id}")
            
            except Exception as e:
                print(f"❌ Error updating song {song_id}: {e}")
                import traceback
                traceback.print_exc()
            finally:
                session.close()
                
        except Exception as e:
            print(f"❌ Error in _update_completed_song for song {song_id}: {e}")
            import traceback
            traceback.print_exc()

    def _start_background_polling(self, song_id: UUID, generation_id: str) -> None:
        """Start background task to poll for completion and update song when done"""
        async def poll_and_update():
            try:
                print(f"🔄 Starting background polling for song {song_id}, generation {generation_id}")
                
                # Wait before starting polling - songs typically take 2-5 minutes  
                await asyncio.sleep(20)  # Initial 20s delay before first poll
                
                # Continue polling until completion
                final_result = await self.ai_service.poll_generation_completion(generation_id)
                
                print(f"📋 Background polling result for song {song_id}: {final_result}")
                
                # Update the song in database using new session for background task
                session = SessionLocal()
                
                try:
                    unit_of_work = UnitOfWorkImpl(session)
                    async with unit_of_work:
                        song_repo = unit_of_work.songs
                        song = await song_repo.get_by_id(SongId(song_id))  # song_id is already UUID
                        
                        if not song:
                            print(f"❌ Song {song_id} not found for update")
                            return
                        
                        if final_result.get('status') == 'completed' and final_result.get('audio_url'):
                            print(f"✅ Updating song {song_id} with completed audio")
                            print(f"🎧 Audio URL: {final_result.get('audio_url')}")
                            
                            # Update song with completed audio
                            song.complete_audio_generation(
                                AudioUrl(final_result['audio_url']),
                                Duration(final_result.get('duration', 180))
                            )
                            
                            # Also update video if available
                            if final_result.get('video_url'):
                                from ...domain.value_objects.song_content import VideoUrl
                                song.video_url = VideoUrl(final_result['video_url'])
                                song.video_status = GenerationStatus.COMPLETED
                                print(f"🎬 Video URL: {final_result.get('video_url')}")
                            
                            await song_repo.update(song)
                            await unit_of_work.commit()
                            
                            print(f"💾 Song {song_id} successfully updated in database")
                            
                            # Broadcast completion to frontend
                            await broadcaster.notify(song_id, {
                                "audio_status": song.audio_status.value,
                                "video_status": song.video_status.value,
                                "status": song.generation_status.value,
                                "audio_url": final_result['audio_url'],
                                "video_url": final_result.get('video_url'),
                                "duration": final_result.get('duration', 180),
                                "title": song.title,
                                "message": "🎉 Your song is ready! You can now download it."
                            })
                            
                            print(f"📡 Completion notification sent for song {song_id}")
                        else:
                            print(f"❌ Background polling failed for song {song_id}: {final_result}")
                            
                            # Mark as failed
                            song.audio_status = GenerationStatus.FAILED
                            song.video_status = GenerationStatus.FAILED
                            await song_repo.update(song)
                            await unit_of_work.commit()
                            
                            await broadcaster.notify(song_id, {
                                "audio_status": song.audio_status.value,
                                "video_status": song.video_status.value,
                                "status": song.generation_status.value,
                                "error": final_result.get('error', 'Generation failed'),
                                "title": song.title
                            })
                            
                except Exception as e:
                    print(f"❌ Error during background polling update for song {song_id}: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    session.close()
                    
            except Exception as e:
                print(f"❌ Error in background polling for song {song_id}: {e}")
                import traceback
                traceback.print_exc()
        
        # Start the background polling task
        import asyncio
        loop = asyncio.get_event_loop()
        task = loop.create_task(poll_and_update())
        
        # Add task reference to prevent garbage collection
        if not hasattr(self, '_polling_tasks'):
            self._polling_tasks = set()
        self._polling_tasks.add(task)
        task.add_done_callback(self._polling_tasks.discard)
        
        print(f"🚀 Background polling task started for song {song_id}") 