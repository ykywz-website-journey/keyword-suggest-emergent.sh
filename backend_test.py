#!/usr/bin/env python3
import requests
import json
import sys
import os
from typing import Dict, List, Any, Tuple, Optional

# Get the backend URL from the frontend .env file
def get_backend_url() -> str:
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.strip().split('=')[1].strip('"\'')
    raise ValueError("Could not find REACT_APP_BACKEND_URL in frontend/.env")

BACKEND_URL = get_backend_url()
print(f"Using backend URL: {BACKEND_URL}")

def test_endpoint(endpoint: str, query: str, expected_source: str) -> Tuple[bool, str]:
    """
    Test a specific suggestion endpoint
    
    Args:
        endpoint: The API endpoint to test (e.g., 'google', 'amazon')
        query: The search query to use
        expected_source: The expected source value in the response
        
    Returns:
        Tuple of (success, message)
    """
    url = f"{BACKEND_URL}/api/suggestions/{endpoint}"
    params = {"q": query}
    
    try:
        print(f"\nTesting {url} with query '{query}'...")
        response = requests.get(url, params=params)
        
        # Check status code
        if response.status_code != 200:
            return False, f"Error: Status code {response.status_code}, Response: {response.text}"
        
        # Parse response
        try:
            data = response.json()
        except json.JSONDecodeError:
            return False, f"Error: Invalid JSON response: {response.text}"
        
        # Check response structure for single source endpoints
        if endpoint != 'all':
            if not isinstance(data, dict):
                return False, f"Error: Expected dictionary response, got {type(data)}"
            
            # Check required fields
            required_fields = ['query', 'source', 'suggestions']
            for field in required_fields:
                if field not in data:
                    return False, f"Error: Missing required field '{field}' in response"
            
            # Check query value
            if data['query'] != query:
                return False, f"Error: Expected query '{query}', got '{data['query']}'"
            
            # Check source value
            if data['source'] != expected_source:
                return False, f"Error: Expected source '{expected_source}', got '{data['source']}'"
            
            # Check suggestions is a list
            if not isinstance(data['suggestions'], list):
                return False, f"Error: Expected suggestions to be a list, got {type(data['suggestions'])}"
            
            # Check if suggestions were returned (might be empty for some queries)
            if len(data['suggestions']) == 0:
                print(f"Warning: No suggestions returned for query '{query}'")
            else:
                print(f"Success: Received {len(data['suggestions'])} suggestions")
                print(f"Sample suggestions: {data['suggestions'][:3]}")
            
            return True, f"Successfully tested {endpoint} endpoint with query '{query}'"
        
        # Check response structure for 'all' endpoint
        else:
            if not isinstance(data, list):
                return False, f"Error: Expected list response for 'all' endpoint, got {type(data)}"
            
            if len(data) == 0:
                return False, "Error: Empty response from 'all' endpoint"
            
            # Check each source in the response
            sources_found = []
            for item in data:
                if not isinstance(item, dict):
                    return False, f"Error: Expected dictionary items in 'all' response, got {type(item)}"
                
                # Check required fields
                required_fields = ['query', 'source', 'suggestions']
                for field in required_fields:
                    if field not in item:
                        return False, f"Error: Missing required field '{field}' in 'all' response item"
                
                # Check query value
                if item['query'] != query:
                    return False, f"Error: Expected query '{query}', got '{item['query']}'"
                
                # Add source to found sources
                sources_found.append(item['source'])
                
                # Check suggestions is a list
                if not isinstance(item['suggestions'], list):
                    return False, f"Error: Expected suggestions to be a list, got {type(item['suggestions'])}"
            
            # Check if we got responses from all expected sources
            expected_sources = ['google', 'amazon', 'youtube']
            missing_sources = [s for s in expected_sources if s not in sources_found]
            
            if missing_sources:
                print(f"Warning: Missing responses from sources: {missing_sources}")
            
            print(f"Success: Received responses from sources: {sources_found}")
            return True, f"Successfully tested 'all' endpoint with query '{query}'"
            
    except requests.RequestException as e:
        return False, f"Error: Request failed: {str(e)}"
    except Exception as e:
        return False, f"Error: Unexpected error: {str(e)}"

def test_error_handling(endpoint: str) -> Tuple[bool, str]:
    """Test error handling by making a request without a query parameter"""
    url = f"{BACKEND_URL}/api/suggestions/{endpoint}"
    
    try:
        print(f"\nTesting error handling for {url} (missing query parameter)...")
        response = requests.get(url)
        
        # We expect a 4xx status code for missing required parameter
        if 400 <= response.status_code < 500:
            print(f"Success: Received expected error status code {response.status_code}")
            return True, f"Successfully tested error handling for {endpoint} endpoint"
        else:
            return False, f"Error: Expected 4xx status code, got {response.status_code}"
            
    except requests.RequestException as e:
        return False, f"Error: Request failed: {str(e)}"
    except Exception as e:
        return False, f"Error: Unexpected error: {str(e)}"

def run_all_tests() -> Dict[str, List[Dict[str, Any]]]:
    """Run all tests and return results"""
    results = {
        "passed": [],
        "failed": []
    }
    
    # Test Google suggestions
    success, message = test_endpoint("google", "test", "google")
    if success:
        results["passed"].append({"test": "Google Suggestions", "message": message})
    else:
        results["failed"].append({"test": "Google Suggestions", "message": message})
    
    # Test Google error handling
    success, message = test_error_handling("google")
    if success:
        results["passed"].append({"test": "Google Error Handling", "message": message})
    else:
        results["failed"].append({"test": "Google Error Handling", "message": message})
    
    # Test Amazon suggestions
    success, message = test_endpoint("amazon", "camping", "amazon")
    if success:
        results["passed"].append({"test": "Amazon Suggestions", "message": message})
    else:
        results["failed"].append({"test": "Amazon Suggestions", "message": message})
    
    # Test Amazon error handling
    success, message = test_error_handling("amazon")
    if success:
        results["passed"].append({"test": "Amazon Error Handling", "message": message})
    else:
        results["failed"].append({"test": "Amazon Error Handling", "message": message})
    
    # Test YouTube suggestions
    success, message = test_endpoint("youtube", "tutorial", "youtube")
    if success:
        results["passed"].append({"test": "YouTube Suggestions", "message": message})
    else:
        results["failed"].append({"test": "YouTube Suggestions", "message": message})
    
    # Test YouTube error handling
    success, message = test_error_handling("youtube")
    if success:
        results["passed"].append({"test": "YouTube Error Handling", "message": message})
    else:
        results["failed"].append({"test": "YouTube Error Handling", "message": message})
    
    # Test All sources
    success, message = test_endpoint("all", "python", "all")
    if success:
        results["passed"].append({"test": "All Sources", "message": message})
    else:
        results["failed"].append({"test": "All Sources", "message": message})
    
    # Test All sources error handling
    success, message = test_error_handling("all")
    if success:
        results["passed"].append({"test": "All Sources Error Handling", "message": message})
    else:
        results["failed"].append({"test": "All Sources Error Handling", "message": message})
    
    return results

if __name__ == "__main__":
    print("Starting API endpoint tests...")
    results = run_all_tests()
    
    # Print summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    print(f"\nPASSED: {len(results['passed'])}")
    for test in results['passed']:
        print(f"✅ {test['test']}: {test['message']}")
    
    print(f"\nFAILED: {len(results['failed'])}")
    for test in results['failed']:
        print(f"❌ {test['test']}: {test['message']}")
    
    # Exit with appropriate status code
    if len(results['failed']) > 0:
        sys.exit(1)
    else:
        sys.exit(0)