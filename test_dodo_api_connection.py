#!/usr/bin/env python3
"""
Test script to verify Dodo Payments API connection
Run this to check if the API URL and credentials are correct
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Potential API URLs to test
API_URLS_TO_TEST = [
    "https://app.dodopayments.com/api/v1",
    "https://app.dodopayments.com/api",
    "https://api.dodopayments.com/v1", 
    "https://api.dodopayments.com",
    "https://checkout.dodopayments.com/api/v1",
    "https://checkout.dodopayments.com/api"
]

async def test_api_connection(api_url: str, api_key: str):
    """Test connection to a specific API URL"""
    print(f"\n🔍 Testing: {api_url}")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test with a simple GET request first
            response = await client.get(
                f"{api_url}/health",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json"
                },
                timeout=10.0
            )
            print(f"   ✅ Health check: {response.status_code}")
            return True
            
    except httpx.ConnectError as e:
        print(f"   ❌ Connection error: {str(e)}")
        return False
    except httpx.TimeoutException:
        print(f"   ⏰ Timeout")
        return False
    except Exception as e:
        print(f"   ⚠️  Other error: {str(e)}")
        return False

async def test_payments_endpoint(api_url: str, api_key: str):
    """Test the payments endpoint specifically"""
    print(f"\n💳 Testing payments endpoint: {api_url}/payments")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test POST to payments endpoint (should fail with missing data, but connection should work)
            response = await client.post(
                f"{api_url}/payments",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={},  # Empty payload to test connection
                timeout=10.0
            )
            print(f"   ✅ Payments endpoint reachable: {response.status_code}")
            if response.status_code != 404:
                return True
                
    except httpx.ConnectError as e:
        print(f"   ❌ Connection error: {str(e)}")
        return False
    except Exception as e:
        print(f"   ⚠️  Error: {str(e)}")
        return False

async def main():
    print("🚀 Dodo Payments API Connection Test")
    print("=" * 50)
    
    api_key = os.getenv("DODO_PAYMENTS_API_KEY")
    if not api_key:
        print("❌ DODO_PAYMENTS_API_KEY not found in environment variables")
        print("Make sure you have set up your .env file correctly")
        return
    
    print(f"🔑 Using API key: {api_key[:10]}...{api_key[-4:]}")
    
    # Test different API URLs
    working_urls = []
    for api_url in API_URLS_TO_TEST:
        if await test_api_connection(api_url, api_key):
            working_urls.append(api_url)
            await test_payments_endpoint(api_url, api_key)
    
    print("\n" + "=" * 50)
    if working_urls:
        print("✅ Working API URLs found:")
        for url in working_urls:
            print(f"   • {url}")
        print(f"\n💡 Update your DODO_PAYMENTS_API_URL to: {working_urls[0]}")
    else:
        print("❌ No working API URLs found")
        print("💡 Possible solutions:")
        print("   1. Check your API key is correct")
        print("   2. Verify your account has API access enabled")
        print("   3. Contact Dodo Payments support for the correct API URL")
        print("   4. Check if you're in test mode vs production mode")

if __name__ == "__main__":
    asyncio.run(main()) 