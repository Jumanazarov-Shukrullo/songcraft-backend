#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.infrastructure.orm.song_model import SongORM
from app.domain.enums import GenerationStatus

async def check_and_fix_song_status():
    """Check and fix song status for song ID 19"""
    db = SessionLocal()
    
    try:
        # Get song 19
        song = db.query(SongORM).filter(SongORM.id == 19).first()
        
        if not song:
            print("❌ Song 19 not found")
            return
        
        print(f"📋 Current Song 19 Status:")
        print(f"   - Title: {song.title}")
        print(f"   - Overall Status: {song.status}")
        print(f"   - Lyrics Status: {song.lyrics_status}")
        print(f"   - Audio Status: {song.audio_status}")
        print(f"   - Video Status: {song.video_status}")
        print(f"   - Audio URL: {song.audio_url}")
        print(f"   - Video URL: {song.video_url}")
        print(f"   - Duration: {song.duration}")
        print(f"   - Message: {song.message}")
        
        # Check if we have audio URL but status is not completed
        if song.audio_url and song.audio_status != GenerationStatus.COMPLETED.value:
            print("\n🔧 FIXING: Song has audio URL but status is not completed")
            
            # Update to completed status
            song.audio_status = GenerationStatus.COMPLETED.value
            song.status = GenerationStatus.COMPLETED.value
            song.message = "🎉 Your song is ready! You can now download it."
            
            # If no duration, set a default
            if not song.duration:
                song.duration = 180  # 3 minutes default
            
            db.commit()
            print("✅ Song status updated to COMPLETED")
            
            print(f"\n📋 Updated Song 19 Status:")
            print(f"   - Overall Status: {song.status}")
            print(f"   - Audio Status: {song.audio_status}")
            print(f"   - Video Status: {song.video_status}")
            print(f"   - Message: {song.message}")
        
        elif song.audio_status == GenerationStatus.COMPLETED.value:
            print("\n✅ Song status is already COMPLETED")
        
        else:
            print(f"\n⚠️ Song status: {song.audio_status}, no audio URL yet")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(check_and_fix_song_status()) 