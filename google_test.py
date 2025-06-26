#!/usr/bin/env python3
import requests
import json
import sys

# Get the backend URL from the frontend .env file
def get_backend_url() -> str:
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.strip().split('=')[1].strip('"\'')
    raise ValueError("Could not find REACT_APP_BACKEND_URL in frontend/.env")

BACKEND_URL = get_backend_url()
print(f"Using backend URL: {BACKEND_URL}")

def test_google_raw_response():
    """Test the Google suggestions API and print the raw response"""
    url = f"{BACKEND_URL}/api/suggestions/google"
    params = {"q": "python programming"}
    
    try:
        print(f"\nTesting {url} with query 'python programming'...")
        
        # Make a direct request to Google's API to compare
        google_url = "http://www.google.com/complete/search"
        google_params = {
            "client": "gws-wiz",
            "q": "python programming",
            "hl": "en"
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print("Making direct request to Google API...")
        direct_response = requests.get(google_url, params=google_params, headers=headers)
        print(f"Direct Google API Status: {direct_response.status_code}")
        print(f"Direct Google API Response (first 500 chars): {direct_response.text[:500]}")
        
        # Now test our backend API
        response = requests.get(url, params=params)
        print(f"Our API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Our API Response: {json.dumps(data, indent=2)}")
            print(f"Number of suggestions: {len(data['suggestions'])}")
        else:
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_google_raw_response()