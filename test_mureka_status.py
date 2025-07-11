#!/usr/bin/env python3
"""Test script to find correct Mureka status endpoint"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_mureka_status_endpoints():
    """Test different Mureka status endpoints"""
    
    api_key = os.getenv("MUREKA_API_KEY")
    api_url = os.getenv("MUREKA_API_URL", "https://api.mureka.ai")
    
    if not api_key:
        print("❌ MUREKA_API_KEY not found")
        return
    
    # Use the generation ID from your logs
    generation_id = "82647791566849"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # Test the correct status endpoint from official documentation
    correct_endpoint = f"{api_url}/v1/music/{generation_id}"
    
    print(f"=== Testing Mureka Status Endpoint ===")
    print(f"Generation ID: {generation_id}")
    print(f"Based on official documentation: {correct_endpoint}")
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print(f"🔍 Testing: {correct_endpoint}")
            response = await client.get(correct_endpoint, headers=headers)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS! Response: {response.json()}")
                return correct_endpoint
            elif response.status_code == 404:
                print(f"   ❌ 404 Not Found - Generation may not exist or is still processing")
                print(f"   💡 This could mean the generation ID is wrong or the song is still being created")
            else:
                print(f"   ⚠️  Error {response.status_code}: {response.text[:200]}")
            print()
            
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
            print()
    
    print("✅ Test completed - using correct endpoint from documentation")

if __name__ == "__main__":
    asyncio.run(test_mureka_status_endpoints()) 