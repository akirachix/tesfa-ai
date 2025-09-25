#!/usr/bin/env python3
"""
API Test Script for Tesfa AI

This script helps test the Tesfa AI API endpoints and demonstrates
the correct format for making requests.

Usage:
    python test_api.py
"""

import requests
import json
import sys

def test_api_request(base_url="http://localhost:8080", query="What are the health risks in Yemen?"):
    """
    Test the API with both incorrect (form) and correct (JSON) request formats.
    """
    
    print("🧪 Testing Tesfa AI API")
    print("=" * 50)
    
    # Test 1: Incorrect format (form data) - should return helpful error
    print("\n1. Testing with INCORRECT format (form data):")
    print(f"   Sending: query={query}")
    
    try:
        form_response = requests.post(
            f"{base_url}/api/chat",  # Adjust endpoint as needed
            data={"query": query},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5
        )
        
        print(f"   Status: {form_response.status_code}")
        print(f"   Response: {json.dumps(form_response.json(), indent=2)}")
        
        if form_response.status_code == 400:
            print("   ✅ Correctly rejected form data with helpful error message")
        else:
            print("   ⚠️  Unexpected response for form data")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Could not connect to server. Is it running?")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Correct format (JSON) 
    print("\n2. Testing with CORRECT format (JSON):")
    print(f"   Sending: {json.dumps({'query': query})}")
    
    try:
        json_response = requests.post(
            f"{base_url}/api/chat",  # Adjust endpoint as needed
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"   Status: {json_response.status_code}")
        if json_response.status_code == 200:
            print("   ✅ Successfully processed JSON request")
            response_data = json_response.json()
            if isinstance(response_data, dict) and "title" in response_data:
                print(f"   📊 Response title: {response_data.get('title', 'N/A')}")
                print(f"   🏥 Health risks detected: {len(response_data.get('disease_risks', []))}")
        else:
            print(f"   Response: {json.dumps(json_response.json(), indent=2)}")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Could not connect to server. Is it running?")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def print_usage_examples():
    """Print examples of correct API usage"""
    
    print("\n" + "=" * 50)
    print("📖 USAGE EXAMPLES")
    print("=" * 50)
    
    print("\n✅ CORRECT - Using curl with JSON:")
    print("curl -X POST -H 'Content-Type: application/json' \\")
    print("  -d '{\"query\": \"What are the health risks in Syria?\"}' \\")
    print("  http://localhost:8080/api/chat")
    
    print("\n❌ INCORRECT - Using curl with form data:")
    print("curl -X POST -H 'Content-Type: application/x-www-form-urlencoded' \\")
    print("  -d 'query=What are the health risks in Syria?' \\")
    print("  http://localhost:8080/api/chat")
    
    print("\n✅ CORRECT - Using Python requests:")
    print("import requests")
    print("response = requests.post(")
    print("    'http://localhost:8080/api/chat',")
    print("    json={'query': 'What are the health risks in Syria?'}")
    print(")")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8080"
    
    if len(sys.argv) > 2:
        query = sys.argv[2]
    else:
        query = "What are the health risks in Yemen?"
    
    print(f"Testing API at: {base_url}")
    print(f"Query: {query}")
    
    test_api_request(base_url, query)
    print_usage_examples()
    
    print("\n" + "=" * 50)
    print("🚀 To start the server: python main.py")
    print("📚 Documentation: PYDANTIC_FIX_DOCUMENTATION.md")
    print("=" * 50)