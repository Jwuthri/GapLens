#!/usr/bin/env python3
"""Manual API testing script."""

import requests
import json
import time
from uuid import UUID

# Base URL for the API
BASE_URL = "http://localhost:8000/api/v1"

def test_health_check():
    """Test the health check endpoint."""
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"Health check: {response.status_code} - {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_submit_app_analysis():
    """Test submitting an app analysis."""
    try:
        payload = {
            "app_url_or_id": "com.example.testapp"
        }
        
        response = requests.post(f"{BASE_URL}/analysis/", json=payload)
        print(f"Submit app analysis: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Analysis ID: {data['analysis_id']}")
            print(f"Status: {data['status']}")
            print(f"Message: {data['message']}")
            return data['analysis_id']
        else:
            print(f"Error: {response.json()}")
            return None
            
    except Exception as e:
        print(f"Submit app analysis failed: {e}")
        return None

def test_submit_website_analysis():
    """Test submitting a website analysis."""
    try:
        payload = {
            "website_url": "https://example.com"
        }
        
        response = requests.post(f"{BASE_URL}/analysis/", json=payload)
        print(f"Submit website analysis: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Analysis ID: {data['analysis_id']}")
            print(f"Status: {data['status']}")
            print(f"Message: {data['message']}")
            return data['analysis_id']
        else:
            print(f"Error: {response.json()}")
            return None
            
    except Exception as e:
        print(f"Submit website analysis failed: {e}")
        return None

def test_get_analysis_status(analysis_id):
    """Test getting analysis status."""
    try:
        response = requests.get(f"{BASE_URL}/analysis/{analysis_id}/status")
        print(f"Get analysis status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data['status']}")
            print(f"Progress: {data['progress']}%")
            print(f"Message: {data['message']}")
            return data['status']
        else:
            print(f"Error: {response.json()}")
            return None
            
    except Exception as e:
        print(f"Get analysis status failed: {e}")
        return None

def test_invalid_requests():
    """Test various invalid requests."""
    print("\n=== Testing Invalid Requests ===")
    
    # Test with no input
    response = requests.post(f"{BASE_URL}/analysis/", json={})
    print(f"No input: {response.status_code} - Expected 422")
    
    # Test with both inputs
    payload = {
        "app_url_or_id": "com.example.app",
        "website_url": "https://example.com"
    }
    response = requests.post(f"{BASE_URL}/analysis/", json=payload)
    print(f"Both inputs: {response.status_code} - Expected 422")
    
    # Test with invalid app URL
    payload = {
        "app_url_or_id": "invalid-url-format"
    }
    response = requests.post(f"{BASE_URL}/analysis/", json=payload)
    print(f"Invalid app URL: {response.status_code} - Expected 400")
    
    # Test getting non-existent analysis
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = requests.get(f"{BASE_URL}/analysis/{fake_id}")
    print(f"Non-existent analysis: {response.status_code} - Expected 404")

def main():
    """Run manual API tests."""
    print("=== Manual API Testing ===")
    
    # Test health check first
    if not test_health_check():
        print("Server not running. Start with: uvicorn app.main:app --reload")
        return
    
    print("\n=== Testing Valid Requests ===")
    
    # Test app analysis
    print("\n--- App Analysis ---")
    app_analysis_id = test_submit_app_analysis()
    
    if app_analysis_id:
        time.sleep(1)  # Brief delay
        test_get_analysis_status(app_analysis_id)
    
    # Test website analysis
    print("\n--- Website Analysis ---")
    website_analysis_id = test_submit_website_analysis()
    
    if website_analysis_id:
        time.sleep(1)  # Brief delay
        test_get_analysis_status(website_analysis_id)
    
    # Test invalid requests
    test_invalid_requests()
    
    print("\n=== Manual Testing Complete ===")
    print("Note: Background processing is mocked in tests.")
    print("For full testing, ensure all services are properly configured.")

if __name__ == "__main__":
    main()