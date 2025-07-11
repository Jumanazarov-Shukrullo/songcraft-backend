#!/usr/bin/env python3
"""Test script to verify complete Mureka generation and status flow"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.external_services.ai_service import AIService

# Load environment variables
load_dotenv()

async def test_mureka_flow():
    """Test the complete Mureka generation and status checking flow"""
    
    if not os.getenv("MUREKA_API_KEY"):
        print("❌ MUREKA_API_KEY not found")
        return
    
    print("=== Testing Complete Mureka Flow ===")
    print()
    
    ai_service = AIService()
    
    # Test lyrics and style
    lyrics = """[Verse]
Testing the new endpoint
Everything should work now
No more 404 errors
Music generation success"""
    
    style = "pop, happy, energetic"
    
    print(f"🎵 Testing music generation...")
    print(f"Lyrics: {lyrics[:50]}...")
    print(f"Style: {style}")
    print()
    
    try:
        # Test the complete audio generation flow
        result = await ai_service.generate_audio(lyrics, style)
        
        print(f"🎯 Generation result: {result}")
        
        if result.get("status") == "processing":
            print("✅ Generation started successfully!")
            generation_id = result.get("generation_id")
            if generation_id:
                print(f"📋 Generation ID: {generation_id}")
                
                # Test status checking manually
                print("\n🔍 Testing status checking...")
                status = await ai_service._get_mureka_status(generation_id)
                print(f"📊 Status result: {status}")
                
                if status.get("status") != "error":
                    print("✅ Status checking works!")
                else:
                    print("❌ Status checking failed")
                    
        elif result.get("status") == "completed":
            print("✅ Generation completed immediately!")
            
        elif result.get("status") == "failed":
            print(f"❌ Generation failed: {result.get('error')}")
            
        else:
            print(f"🤔 Unexpected result: {result}")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mureka_flow()) 