#!/usr/bin/env python3
"""
Test Dodo Payments SDK integration
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_dodo_sdk():
    """Test the Dodo Payments SDK implementation"""
    print("🎯 Testing Dodo Payments SDK Integration")
    print("=" * 50)
    
    # Import our payment service
    try:
        from app.infrastructure.external_services.payment_service import PaymentService
        print("✅ PaymentService imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import PaymentService: {e}")
        return
    
    # Check environment variables
    api_key = os.getenv("DODO_PAYMENTS_API_KEY")
    audio_product_id = os.getenv("DODO_AUDIO_PRODUCT_ID")
    video_product_id = os.getenv("DODO_VIDEO_PRODUCT_ID")
    
    if not api_key:
        print("❌ DODO_PAYMENTS_API_KEY not found in environment")
        return
    
    if not audio_product_id:
        print("❌ DODO_AUDIO_PRODUCT_ID not found in environment")
        return
        
    if not video_product_id:
        print("❌ DODO_VIDEO_PRODUCT_ID not found in environment")
        return
    
    print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"🎵 Audio Product ID: {audio_product_id}")
    print(f"🎬 Video Product ID: {video_product_id}")
    
    # Initialize payment service
    try:
        payment_service = PaymentService()
        print("✅ PaymentService initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize PaymentService: {e}")
        return
    
    # Test creating a checkout session
    try:
        print("\n🧪 Testing checkout session creation...")
        
        result = await payment_service.create_checkout_session(
            customer_email="test@example.com",
            product_type="audio_only",
            custom_data={
                "user_id": "test_user_123",
                "customer_name": "Test Customer"
            }
        )
        
        print("✅ Checkout session created successfully!")
        print(f"🆔 Payment ID: {result.get('payment_id')}")
        print(f"🔗 Checkout URL: {result.get('checkout_url')}")
        print(f"💰 Currency: {result.get('currency')}")
        
    except Exception as e:
        print(f"❌ Failed to create checkout session: {e}")
        print("💡 This might be expected if you don't have valid product IDs yet")

if __name__ == "__main__":
    asyncio.run(test_dodo_sdk()) 