#!/usr/bin/env python3
"""
Direct SQL fix script for song 19 - manually update status after completed Mureka generation
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings

def fix_song_19():
    """Fix song 19 status with completed Mureka generation data"""
    
    # Data from successful Mureka generation (from logs)
    audio_url = "https://cdn.mureka.ai/cos-prod/open/song/20250709/76634189201409-NN2hMYwrwQqWoYudm3vA6D.mp3"
    duration_ms = 100771  # From Mureka response
    duration_seconds = duration_ms // 1000  # Convert to seconds
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    
    try:
        # First, check current status of song 19
        print("📋 Checking current status of song 19...")
        song_result = db.execute(
            text("SELECT id, title, audio_status, audio_url, duration FROM songs WHERE id = :song_id"),
            {"song_id": 19}
        ).fetchone()
        
        if not song_result:
            print("❌ Song 19 not found!")
            return False
        
        print(f"   Title: {song_result[1]}")
        print(f"   Audio Status: {song_result[2]}")
        print(f"   Audio URL: {song_result[3] or 'None'}")
        print(f"   Duration: {song_result[4] or 'None'}")
        
        # Update the song with completed audio generation
        if song_result[2] != "completed":
            print(f"\n🔄 Updating song 19 with completed audio generation...")
            
            # Update song with completed status and URLs
            update_result = db.execute(
                text("""
                    UPDATE songs 
                    SET audio_status = 'completed',
                        audio_url = :audio_url,
                        duration = :duration,
                        updated_at = NOW()
                    WHERE id = :song_id
                """),
                {
                    "song_id": 19,
                    "audio_url": audio_url,
                    "duration": duration_seconds
                }
            )
            
            if update_result.rowcount > 0:
                db.commit()
                print(f"✅ Song 19 updated successfully!")
                print(f"   Audio Status: completed")
                print(f"   Audio URL: {audio_url}")
                print(f"   Duration: {duration_seconds}s")
                
                # Verify the update
                verification = db.execute(
                    text("SELECT audio_status, audio_url, duration FROM songs WHERE id = :song_id"),
                    {"song_id": 19}
                ).fetchone()
                
                print(f"📋 Verification:")
                print(f"   Audio Status: {verification[0]}")
                print(f"   Audio URL: {verification[1]}")
                print(f"   Duration: {verification[2]}s")
                
                print(f"\n🎉 Song 19 is now marked as completed!")
                print(f"📱 Please refresh your browser to see the updated status.")
                
                return True
            else:
                print(f"❌ Failed to update song 19")
                return False
        else:
            print(f"\n✅ Song 19 is already marked as completed")
            return True
            
    except Exception as e:
        print(f"❌ Error fixing song 19: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 Fixing song 19 status with direct SQL update...")
    success = fix_song_19()
    if success:
        print("\n🎵 Song 19 has been fixed! You can now:")
        print("   • Refresh your browser")
        print("   • Download the completed song")
        print("   • Enjoy your personalized music!")
    else:
        print("\n❌ Failed to fix song 19. Please check the logs above.") 