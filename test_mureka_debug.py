#!/usr/bin/env python3
"""Debug script to test Mureka API configuration"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_mureka_api():
    """Test Mureka API configuration and connectivity"""
    
    # Get environment variables
    api_key = os.getenv("MUREKA_API_KEY")
    api_url = os.getenv("MUREKA_API_URL", "https://api.mureka.ai")
    
    print("=== Mureka API Debug Test ===")
    print(f"API URL: {api_url}")
    print(f"API Key: {api_key[:20]}..." if api_key else "API Key: None")
    print()
    
    if not api_key:
        print("❌ MUREKA_API_KEY not found in environment variables")
        return
    
    # Test payload (same as your working curl)
    test_lyrics = """[Verse]
In the stormy night, I wander alone
Lost in the rain, feeling like I have been thrown
Memories of you, they flash before my eyes
Hoping for a moment, just to find some bliss"""
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "lyrics": test_lyrics,
        "model": "auto",
        "prompt": "r&b, slow, passionate, male vocal"
    }
    
    # Test the endpoint
    url = f"{api_url}/v1/song/generate"
    
    print(f"Testing endpoint: {url}")
    print(f"Payload: {payload}")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("🎤 Sending request to Mureka API...")
            response = await client.post(url, headers=headers, json=payload)
            
            print(f"Response Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print()
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Success! Response data:")
                print(data)
            else:
                print(f"❌ Error {response.status_code}:")
                print(response.text)
                
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_mureka_api()) 