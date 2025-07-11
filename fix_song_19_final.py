#!/usr/bin/env python3
"""
Final fix for song 19 - trigger the completion manually
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.database import SessionLocal
from app.infrastructure.repositories.unit_of_work_impl import UnitOfWorkImpl
from app.domain.value_objects.entity_ids import SongId
from app.domain.value_objects.song_content import AudioUrl, Duration
from app.api.event_broadcaster import broadcaster

async def fix_song_19():
    """Fix song 19 with the correct audio data from Mureka"""
    
    # Data from successful Mureka generation (from logs)
    audio_url = "https://cdn.mureka.ai/cos-prod/open/song/20250709/76634189201409-NN2hMYwrwQqWoYudm3vA6D.mp3"
    duration_ms = 100771  # From Mureka response
    duration_seconds = duration_ms // 1000  # Convert to seconds
    
    try:
        # Use synchronous session for now
        session = SessionLocal()
        try:
            unit_of_work = UnitOfWorkImpl(session)
            async with unit_of_work:
                song_repo = unit_of_work.songs
                song = await song_repo.get_by_id(SongId(19))
                
                if not song:
                    print("❌ Song 19 not found")
                    return False
                
                print(f"📋 Current song status:")
                print(f"   Title: {song.title}")
                print(f"   Audio Status: {song.audio_status.value}")
                print(f"   Audio URL: {song.audio_url.url if song.audio_url else 'None'}")
                print(f"   Generation Status: {song.generation_status.value}")
                
                # Update song with completed audio generation
                if song.audio_status.value != "completed":
                    print(f"\n🔄 Fixing song 19 with completed audio generation...")
                    
                    # Use the song's domain method to properly update status
                    song.complete_audio_generation(
                        AudioUrl(audio_url),
                        Duration(duration_seconds)
                    )
                    
                    await song_repo.update(song)
                    await unit_of_work.commit()
                    
                    print(f"✅ Song 19 updated successfully!")
                    print(f"   Audio Status: {song.audio_status.value}")
                    print(f"   Audio URL: {song.audio_url.url}")
                    print(f"   Duration: {song.duration.duration}s")
                    print(f"   Generation Status: {song.generation_status.value}")
                    
                    # Broadcast completion to frontend
                    try:
                        await broadcaster.notify(19, {
                            "audio_status": song.audio_status.value,
                            "video_status": song.video_status.value,
                            "status": song.generation_status.value,
                            "audio_url": audio_url,
                            "duration": duration_seconds,
                            "title": song.title,
                            "message": "🎉 Your song is ready! You can now download it."
                        })
                        print(f"📡 Broadcasted completion status to frontend")
                    except Exception as e:
                        print(f"⚠️ Failed to broadcast: {e}")
                    
                    return True
                else:
                    print(f"\n✅ Song 19 is already marked as completed")
                    return True
        finally:
            session.close()
                    
    except Exception as e:
        print(f"❌ Error fixing song 19: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Fixing song 19 with backend fixes...")
    success = asyncio.run(fix_song_19())
    
    if success:
        print("\n🎉 SUCCESS! Song 19 has been fixed!")
        print("📱 Please refresh your browser page to see:")
        print("   • Song status: Completed ✅")
        print("   • Download buttons available")
        print("   • Audio ready to play")
        print("\n🎵 Your song 'моя девушка Сара Song' is now ready!")
    else:
        print("\n❌ Failed to fix song 19. Check the error above.") 