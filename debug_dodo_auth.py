#!/usr/bin/env python3
"""
Debug Dodo Payments authentication issues
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def debug_dodo_auth():
    """Debug Dodo Payments authentication"""
    print("🔍 Debugging Dodo Payments Authentication")
    print("=" * 50)
    
    try:
        from dodopayments import DodoPayments
        print("✅ Dodo Payments SDK imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Dodo Payments SDK: {e}")
        return
    
    api_key = os.getenv("DODO_PAYMENTS_API_KEY")
    if not api_key:
        print("❌ No API key found")
        return
    
    print(f"🔑 API Key: {api_key[:15]}...{api_key[-8:]}")
    print(f"📏 Length: {len(api_key)}")
    
    # Test 1: Initialize client
    try:
        client = DodoPayments(bearer_token=api_key)
        print("✅ DodoPayments client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return
    
    # Test 2: Try a simple payment creation with minimal data
    try:
        print("\n🧪 Testing payment creation...")
        
        # Use a simple test product ID pattern
        test_product_id = "test_product_123"  # This will likely fail but should give us better error info
        
        payment = client.payments.create(
            payment_link=True,
            billing={
                "city": "Test City",
                "country": "US",
                "state": "CA",
                "street": "123 Test St",
                "zipcode": 12345
            },
            customer={
                "email": "test@example.com",
                "name": "Test Customer"
            },
            product_cart=[{
                "product_id": test_product_id,
                "quantity": 1
            }]
        )
        
        print("✅ Payment creation successful!")
        print(f"Payment ID: {payment.payment_id}")
        print(f"Payment Link: {payment.payment_link}")
        
    except Exception as e:
        print(f"❌ Payment creation failed: {e}")
        
        # Try to get more detailed error information
        error_str = str(e)
        
        if "401" in error_str:
            print("\n🔍 401 Unauthorized Error Analysis:")
            print("   This usually means:")
            print("   1. API key is for wrong environment (test vs production)")
            print("   2. API key doesn't have required permissions/modules")
            print("   3. API key is invalid or expired")
            
        elif "400" in error_str:
            print("\n🔍 400 Bad Request Error Analysis:")
            print("   This usually means:")
            print("   1. Invalid product ID")
            print("   2. Missing required fields")
            print("   3. API key is valid but request format is wrong")
            
        elif "product" in error_str.lower():
            print("\n🔍 Product Error Analysis:")
            print("   This usually means:")
            print("   1. Product ID doesn't exist")
            print("   2. Product ID is for wrong account")
            
        print(f"\n📝 Full error details: {error_str}")
    
    # Test 3: Try with your actual product ID
    audio_product_id = os.getenv("DODO_AUDIO_PRODUCT_ID")
    if audio_product_id:
        print(f"\n🧪 Testing with your actual audio product ID: {audio_product_id}")
        try:
            payment = client.payments.create(
                payment_link=True,
                billing={
                    "city": "Test City",
                    "country": "US",
                    "state": "CA", 
                    "street": "123 Test St",
                    "zipcode": 12345
                },
                customer={
                    "email": "test@example.com",
                    "name": "Test Customer"
                },
                product_cart=[{
                    "product_id": audio_product_id,
                    "quantity": 1
                }]
            )
            
            print("✅ Payment with real product ID successful!")
            print(f"Payment ID: {payment.payment_id}")
            
        except Exception as e:
            print(f"❌ Payment with real product ID failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_dodo_auth()) 