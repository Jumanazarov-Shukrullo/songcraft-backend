#!/usr/bin/env python3
"""Test proxy speed and alternative configurations"""

import asyncio
import time
import httpx
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

async def test_proxy_speed(proxy_url, description="Current proxy"):
    """Test how fast a proxy responds"""
    print(f"\n🔍 Testing {description}: {proxy_url}")
    start_time = time.time()
    
    try:
        # Test basic HTTP connection
        print("1️⃣ Testing basic HTTP connection...")
        async with httpx.AsyncClient(proxies=proxy_url, timeout=30.0) as client:
            response = await client.get("https://httpbin.org/ip")
            basic_time = time.time() - start_time
            print(f"✅ Basic HTTP: {basic_time:.2f}s - IP: {response.json().get('origin', 'unknown')}")
    
    except Exception as e:
        print(f"❌ Basic HTTP failed: {e}")
        return
    
    try:
        # Test OpenAI API connection (just to test endpoint, not full generation)
        print("2️⃣ Testing OpenAI API connection...")
        
        http_client = httpx.AsyncClient(
            proxies=proxy_url,
            timeout=httpx.Timeout(60.0, connect=15.0, read=45.0)
        )
        
        openai_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            http_client=http_client,
            timeout=60.0
        )
        
        # Test with a simple, fast request
        openai_start = time.time()
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",  # Faster than GPT-4
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10
        )
        openai_time = time.time() - openai_start
        
        total_time = time.time() - start_time
        print(f"✅ OpenAI API: {openai_time:.2f}s (Total: {total_time:.2f}s)")
        print(f"🚀 Response: {response.choices[0].message.content[:50]}...")
        
        await http_client.aclose()
        
        return {
            "proxy": proxy_url,
            "basic_time": basic_time,
            "openai_time": openai_time,
            "total_time": total_time,
            "success": True
        }
        
    except Exception as e:
        print(f"❌ OpenAI API failed: {e}")
        return {
            "proxy": proxy_url,
            "basic_time": basic_time,
            "success": False,
            "error": str(e)
        }

async def test_direct_connection():
    """Test direct connection (if available)"""
    print(f"\n🔍 Testing direct connection (no proxy)")
    start_time = time.time()
    
    try:
        openai_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=30.0
        )
        
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10
        )
        
        total_time = time.time() - start_time
        print(f"✅ Direct connection: {total_time:.2f}s")
        print(f"🚀 Response: {response.choices[0].message.content[:50]}...")
        
        return {"direct": True, "time": total_time, "success": True}
        
    except Exception as e:
        print(f"❌ Direct connection failed: {e}")
        return {"direct": True, "success": False, "error": str(e)}

async def main():
    print("🧪 Proxy Speed Test")
    print("=" * 50)
    
    # Get current proxy
    current_proxy = os.getenv("OPENAI_PROXY_URL")
    
    results = []
    
    if current_proxy:
        # Test current proxy
        result = await test_proxy_speed(current_proxy, "Current proxy")
        if result:
            results.append(result)
    else:
        print("⚠️ No proxy configured")
    
    # Test direct connection
    direct_result = await test_direct_connection()
    
    # Test some alternative proxy formats (you can add your own)
    alternative_proxies = [
        # Add alternative proxies here if you have them
        # "http://user:pass@alternative-proxy.com:8080",
        # "https://user:pass@premium-proxy.com:443",
    ]
    
    for proxy in alternative_proxies:
        result = await test_proxy_speed(proxy, "Alternative proxy")
        if result:
            results.append(result)
    
    # Summary
    print("\n📊 SPEED COMPARISON")
    print("=" * 50)
    
    if direct_result.get("success"):
        print(f"🏃‍♂️ Direct connection: {direct_result['time']:.2f}s")
    
    for result in results:
        if result["success"]:
            status = "🐌" if result["total_time"] > 60 else "🚀" if result["total_time"] < 10 else "🏃‍♂️"
            print(f"{status} {result['proxy'][:50]}...: {result['total_time']:.2f}s")
        else:
            print(f"❌ {result['proxy'][:50]}...: FAILED")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS")
    print("=" * 50)
    
    if current_proxy and results:
        current_result = results[0]
        if current_result["success"]:
            if current_result["total_time"] > 60:
                print("🐌 Your current proxy is VERY slow (>60s)")
                print("   Consider switching to a faster proxy service")
                print("   or using a reverse proxy instead")
            elif current_result["total_time"] > 30:
                print("⚠️ Your current proxy is slow (>30s)")
                print("   You might want to find a faster alternative")
            else:
                print("✅ Your proxy speed is acceptable")
    
    print("\n🛠️ SOLUTIONS:")
    print("1. Switch to a premium proxy service (usually faster)")
    print("2. Deploy your own reverse proxy on Vercel/Heroku (fastest)")
    print("3. Try SOCKS5 proxy instead of HTTP proxy")
    print("4. Use a VPN + direct connection")
    
    print("\nSee OPENAI_PROXY_SETUP.md for detailed setup instructions!")

if __name__ == "__main__":
    asyncio.run(main()) 