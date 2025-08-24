#!/usr/bin/env python3
"""Integration test for the complete API."""

from fastapi.testclient import TestClient
from unittest.mock import patch
import json

from app.main import app

client = TestClient(app)

def test_api_integration():
    """Test the complete API integration."""
    
    print("=== API Integration Test ===")
    
    # Test health endpoint
    response = client.get("/health")
    print(f"Health check: {response.status_code} - {response.json()}")
    assert response.status_code == 200
    
    # Test root endpoint
    response = client.get("/")
    print(f"Root endpoint: {response.status_code} - {response.json()}")
    assert response.status_code == 200
    
    # Test API docs
    response = client.get("/docs")
    print(f"API docs: {response.status_code} (HTML response)")
    assert response.status_code == 200
    
    # Mock background tasks to prevent actual processing
    with patch('app.api.v1.analysis.process_app_analysis') as mock_app_task, \
         patch('app.api.v1.analysis.process_website_analysis') as mock_website_task:
        
        # Test website analysis submission
        response = client.post("/api/v1/analysis/", json={
            "website_url": "https://example.com"
        })
        print(f"Website analysis submission: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Analysis ID: {data['analysis_id']}")
            print(f"  Status: {data['status']}")
            mock_website_task.assert_called_once()
        else:
            print(f"  Error: {response.json()}")
        
        # Test app analysis submission
        response = client.post("/api/v1/analysis/", json={
            "app_url_or_id": "com.example.app"
        })
        print(f"App analysis submission: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Analysis ID: {data['analysis_id']}")
            print(f"  Status: {data['status']}")
            mock_app_task.assert_called_once()
        else:
            print(f"  Error: {response.json()}")
    
    # Test validation errors
    print("\n--- Testing Validation ---")
    
    # No input
    response = client.post("/api/v1/analysis/", json={})
    print(f"No input: {response.status_code} (expected 422)")
    
    # Both inputs
    response = client.post("/api/v1/analysis/", json={
        "app_url_or_id": "com.example.app",
        "website_url": "https://example.com"
    })
    print(f"Both inputs: {response.status_code} (expected 422)")
    
    # Invalid app URL
    response = client.post("/api/v1/analysis/", json={
        "app_url_or_id": "invalid-format"
    })
    print(f"Invalid app URL: {response.status_code} (expected 400)")
    
    print("\n✅ Integration test completed successfully!")

if __name__ == "__main__":
    test_api_integration()