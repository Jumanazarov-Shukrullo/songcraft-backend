#!/usr/bin/env python3
"""
Test actual Dodo Payments API endpoints based on documentation
"""

import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API URLs to test based on documentation patterns
TEST_APIS = [
    # Based on the user's integration guide mentioning NEXT_PUBLIC_DODO_TEST_API
    "https://app.dodopayments.com/api/v1",
    "https://api.dodo.dev/v1",  # Common pattern for test environments
    "https://test-api.dodopayments.com/v1",
    "https://sandbox.dodopayments.com/api/v1", 
    "https://staging.dodopayments.com/api/v1",
    # From the docs examples pattern
    "https://checkout.dodopayments.com/api/v1",
]

def test_payments_endpoint(base_url: str, api_key: str):
    """Test the actual payments endpoint"""
    print(f"\n🧪 Testing: {base_url}/payments")
    
    # Test with minimal valid payload
    test_payload = {
        "payment_link": True,
        "billing": {
            "city": "Test City",
            "country": "US",
            "state": "CA",
            "street": "123 Test St",
            "zipcode": 12345
        },
        "customer": {
            "email": "test@example.com",
            "name": "Test Customer"
        },
        "product_cart": [
            {
                "product_id": "test_product",
                "quantity": 1
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{base_url}/payments",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json=test_payload,
            timeout=10.0
        )
        
        print(f"   📡 Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print(f"   ✅ SUCCESS! Valid endpoint found")
            try:
                data = response.json()
                print(f"   💰 Response: {data}")
            except:
                print(f"   📄 Response text: {response.text[:200]}...")
            return True
            
        elif response.status_code == 400:
            print(f"   ⚠️  Endpoint exists but request invalid (expected for test)")
            try:
                error = response.json()
                print(f"   📄 Error: {error}")
            except:
                print(f"   📄 Response: {response.text[:200]}...")
            return True
            
        elif response.status_code == 401:
            print(f"   🔐 Endpoint exists but authentication failed")
            return True
            
        elif response.status_code == 404:
            print(f"   ❌ Endpoint not found")
            return False
            
        else:
            print(f"   ❓ Other status: {response.text[:100]}...")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection failed")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("🎯 Testing Actual Dodo Payments API Endpoints")
    print("=" * 60)
    
    api_key = os.getenv("DODO_PAYMENTS_API_KEY")
    if not api_key:
        print("❌ DODO_PAYMENTS_API_KEY not found in environment variables")
        return
    
    print(f"🔑 Using API key: {api_key[:10]}...{api_key[-4:]}")
    
    working_endpoints = []
    
    for api_url in TEST_APIS:
        if test_payments_endpoint(api_url, api_key):
            working_endpoints.append(api_url)
    
    print("\n" + "=" * 60)
    if working_endpoints:
        print("✅ Working API endpoints found:")
        for endpoint in working_endpoints:
            print(f"   • {endpoint}")
        
        best_endpoint = working_endpoints[0]
        print(f"\n💡 Update your .env file:")
        print(f"DODO_PAYMENTS_API_URL={best_endpoint}")
        
    else:
        print("❌ No working endpoints found with current API key")
        print("💡 Next steps:")
        print("   1. Check your API key is correct")
        print("   2. Verify you're in the right environment (test vs production)")
        print("   3. Check your Dodo Payments dashboard for the correct API URL")
        print("   4. Contact Dodo Payments support for API documentation")

if __name__ == "__main__":
    main() 