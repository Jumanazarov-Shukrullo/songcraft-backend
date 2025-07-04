#!/usr/bin/env python3
"""Test script for DeepSeek API integration"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.infrastructure.external_services.ai_service import AIService
from app.core.config import settings


async def test_deepseek_lyrics():
    """Test DeepSeek lyrics generation"""
    
    # Check if API key is configured
    if not hasattr(settings, 'DEEPSEEK_API_KEY') or not settings.DEEPSEEK_API_KEY:
        print("❌ DEEPSEEK_API_KEY not configured!")
        print("Please set DEEPSEEK_API_KEY in your .env file")
        return False
    
    print("🧪 Testing DeepSeek API integration...")
    print(f"📡 API Key configured: {settings.DEEPSEEK_API_KEY[:20]}...")
    
    # Initialize AI service
    ai_service = AIService()
    
    # Test data
    test_description = "A love song for my partner Sarah, celebrating our 5 years together"
    test_style = "pop"
    
    try:
        print(f"\n🔄 Generating lyrics...")
        print(f"Description: {test_description}")
        print(f"Style: {test_style}")
        
        lyrics = await ai_service.generate_lyrics(
            description=test_description,
            music_style=test_style
        )
        
        print("\n✅ Success! Generated lyrics:")
        print("=" * 50)
        print(lyrics)
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPossible issues:")
        print("1. Invalid DEEPSEEK_API_KEY")
        print("2. Network connectivity issues")
        print("3. DeepSeek API rate limits")
        return False


async def test_lyrics_improvement():
    """Test lyrics improvement functionality"""
    
    print("\n🧪 Testing lyrics improvement...")
    
    ai_service = AIService()
    
    original_lyrics = """[Verse 1]
Simple love song here
Nothing fancy dear
Just a melody

[Chorus]
Love is all we need
That's the only creed
You and me"""
    
    feedback = "Make it more romantic and add specific details about a couple's journey"
    
    try:
        improved_lyrics = await ai_service.improve_lyrics(original_lyrics, feedback)
        
        print("✅ Lyrics improvement successful!")
        print("\nOriginal:")
        print("-" * 30)
        print(original_lyrics)
        print("\nImproved:")
        print("-" * 30)
        print(improved_lyrics)
        
        return True
        
    except Exception as e:
        print(f"❌ Lyrics improvement failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("🚀 DeepSeek AI Service Test Suite")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 2
    
    # Test 1: Basic lyrics generation
    if await test_deepseek_lyrics():
        tests_passed += 1
    
    # Test 2: Lyrics improvement
    if await test_lyrics_improvement():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! DeepSeek integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the configuration.")
    
    return tests_passed == total_tests


if __name__ == "__main__":
    asyncio.run(main()) 