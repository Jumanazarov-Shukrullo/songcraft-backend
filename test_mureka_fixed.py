#!/usr/bin/env python3
"""Test script to verify the fixed Mureka API integration"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.external_services.ai_service import AIService

# Load environment variables
load_dotenv()

async def test_mureka_integration():
    """Test complete Mureka integration with multiple endpoint attempts"""
    
    if not os.getenv("MUREKA_API_KEY"):
        print("❌ MUREKA_API_KEY not found in environment")
        return
    
    print("=== Testing MAXIMUM COST-OPTIMIZED Mureka Integration ===")
    print("💰 Expected API calls: 3 maximum total per song")
    print("⏱️ Polling intervals: 30s, 2min, 3min")
    print("📊 Total cost reduction: 95%+ compared to original approach (3 vs 60+ calls)")
    print("🎯 Target: Most songs complete within 2-3 minutes, caught by first 2 polls")
    print()
    
    ai_service = AIService()
    
    # Test lyrics and style
    lyrics = """[Verse]
Testing the new endpoints
Hoping this will work now
Multiple API paths to try
Until we find the right one

[Chorus]
Download my song when it's ready
Audio and video files
User experience should be smooth
No more 404 errors"""
    
    style = "pop"
    
    print(f"📝 Test lyrics: {lyrics[:50]}...")
    print(f"🎵 Style: {style}")
    print()
    
    try:
        # Test the generation
        print("🎤 Starting music generation...")
        result = await ai_service._generate_audio_mureka(lyrics, style)
        
        print(f"🎤 Generation result: {result}")
        
        if result.get("status") == "processing":
            generation_id = result.get("generation_id")
            print(f"✅ Generation started! ID: {generation_id}")
            
            if generation_id:
                print()
                print("🔍 Testing correct status endpoint /v1/song/query/{id}...")
                
                # Test status checking directly with correct endpoint
                status_result = await ai_service._get_mureka_status(generation_id)
                print(f"🔍 Status check result: {status_result}")
                
                # Only proceed with polling if initial status check works
                if status_result.get("status") != "error":
                    print()
                    print("⏱️ Testing MAXIMUM COST-OPTIMIZED polling (max 3 calls total per song)...")
                    poll_result = await ai_service._poll_mureka_completion(generation_id)
                    print(f"⏱️ Final poll result: {poll_result}")
                    
                    # If successful, show download URLs and test download
                    if poll_result.get("status") == "completed":
                        print()
                        print("🎉 SUCCESS! Song generation completed!")
                        print(f"🎧 Audio URL: {poll_result.get('audio_url')}")
                        if poll_result.get("all_urls"):
                            print(f"📁 All URLs: {poll_result.get('all_urls')}")
                        
                        # Test download functionality
                        audio_url = poll_result.get("audio_url")
                        if audio_url:
                            print()
                            print("📥 Testing audio download...")
                            try:
                                audio_bytes = await ai_service.download_audio_file(audio_url)
                                print(f"✅ Download successful! File size: {len(audio_bytes)} bytes")
                            except Exception as download_error:
                                print(f"❌ Download failed: {download_error}")
                        
                        # Test download info helper
                        print()
                        print("📋 Testing download info helper...")
                        download_info = await ai_service.get_song_download_info(generation_id)
                        print(f"📋 Download info: {download_info}")
                        
                else:
                    print("❌ Status endpoint still not working - check API key and endpoint")
                
        else:
            print(f"❌ Generation failed: {result}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mureka_integration()) 