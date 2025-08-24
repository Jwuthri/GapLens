#!/usr/bin/env python3
"""Simple API test using SQLite to avoid PostgreSQL enum issues."""

import os
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

# Set up SQLite for testing
temp_db = tempfile.NamedTemporaryFile(delete=False)
temp_db.close()

os.environ["DATABASE_URL"] = f"sqlite:///{temp_db.name}"

from app.main import app
from app.database.connection import get_db, Base
from app.models import database as db_models

# Create test database
engine = create_engine(f"sqlite:///{temp_db.name}", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create tables
Base.metadata.create_all(bind=engine)

client = TestClient(app)

def test_api_with_sqlite():
    """Test API endpoints with SQLite database."""
    
    print("=== API Test with SQLite ===")
    
    # Test health endpoint
    response = client.get("/health")
    print(f"Health check: {response.status_code} - {response.json()}")
    
    # Mock background tasks to prevent actual processing
    with patch('app.api.v1.analysis.process_app_analysis') as mock_app_task, \
         patch('app.api.v1.analysis.process_website_analysis') as mock_website_task:
        
        # Test website analysis submission
        print("\n--- Website Analysis ---")
        response = client.post("/api/v1/analysis/", json={
            "website_url": "https://example.com"
        })
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analysis ID: {data['analysis_id']}")
            print(f"✅ Status: {data['status']}")
            print(f"✅ Message: {data['message']}")
            
            # Test status endpoint
            analysis_id = data['analysis_id']
            response = client.get(f"/api/v1/analysis/{analysis_id}/status")
            print(f"Status check: {response.status_code}")
            if response.status_code == 200:
                status_data = response.json()
                print(f"✅ Current status: {status_data['status']}")
                print(f"✅ Progress: {status_data['progress']}%")
            
            mock_website_task.assert_called_once()
        else:
            print(f"❌ Error: {response.json()}")
        
        # Test app analysis submission
        print("\n--- App Analysis ---")
        response = client.post("/api/v1/analysis/", json={
            "app_url_or_id": "com.example.app"
        })
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analysis ID: {data['analysis_id']}")
            print(f"✅ Status: {data['status']}")
            print(f"✅ Message: {data['message']}")
            
            # Test status endpoint
            analysis_id = data['analysis_id']
            response = client.get(f"/api/v1/analysis/{analysis_id}/status")
            print(f"Status check: {response.status_code}")
            if response.status_code == 200:
                status_data = response.json()
                print(f"✅ Current status: {status_data['status']}")
                print(f"✅ Progress: {status_data['progress']}%")
            
            mock_app_task.assert_called_once()
        else:
            print(f"❌ Error: {response.json()}")
    
    # Test validation
    print("\n--- Validation Tests ---")
    
    # Invalid app URL
    response = client.post("/api/v1/analysis/", json={
        "app_url_or_id": "invalid-format"
    })
    print(f"Invalid app URL: {response.status_code} (expected 400) ✅")
    
    # No input
    response = client.post("/api/v1/analysis/", json={})
    print(f"No input: {response.status_code} (expected 422) ✅")
    
    print("\n✅ All tests completed successfully!")
    
    # Cleanup
    os.unlink(temp_db.name)

if __name__ == "__main__":
    test_api_with_sqlite()