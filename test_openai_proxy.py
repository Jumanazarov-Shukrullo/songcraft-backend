#!/usr/bin/env python3
"""
Test script for OpenAI API with proxy configuration
"""

import asyncio
import os
from app.infrastructure.external_services.ai_service import AIService
from app.core.config import settings

async def test_openai_connection():
    """Test OpenAI API connection with proxy configuration"""
    
    print("🔧 Testing OpenAI API Configuration")
    print("=" * 50)
    
    # Check configuration
    print(f"OpenAI API Key: {'✅ Set' if settings.OPENAI_API_KEY else '❌ Missing'}")
    print(f"Proxy URL: {settings.OPENAI_PROXY_URL or 'Not configured'}")
    print(f"Base URL: {settings.OPENAI_BASE_URL or 'Default (api.openai.com)'}")
    print("-" * 50)
    
    if not settings.OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY is required. Please set it in your .env file.")
        return False
    
    # Test AI service
    try:
        print("🚀 Testing lyrics generation...")
        ai_service = AIService()
        print('here')
        result = await ai_service.generate_lyrics(
            description="A happy birthday song for my best friend",
            music_style="pop"
        )
        print('here2')
        print("✅ OpenAI API connection successful!")
        print(f"Generated lyrics preview: {result[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API connection failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("1. Check your OPENAI_API_KEY is valid")
        print("2. If in Russia, configure OPENAI_PROXY_URL in .env")
        print("3. Ensure proxy server is accessible")
        print("4. Check firewall/network settings")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_openai_connection())
    exit(0 if success else 1) 