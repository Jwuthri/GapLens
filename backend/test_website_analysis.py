#!/usr/bin/env python3
"""Test script for website analysis functionality."""

import asyncio
from app.services.website_review_aggregator import WebsiteReviewAggregator, WebsiteReview
from datetime import datetime

async def test_website_review_aggregator():
    """Test the WebsiteReviewAggregator with a sample website."""
    
    print("=== Testing Website Review Aggregator ===")
    
    # Test with a sample website URL
    test_url = "https://example.com"
    
    try:
        async with WebsiteReviewAggregator() as aggregator:
            print(f"Testing with URL: {test_url}")
            
            # Test business info extraction
            business_info = await aggregator.extract_business_info(test_url)
            if business_info:
                print(f"Business Name: {business_info.name}")
                print(f"Address: {business_info.address}")
                print(f"Phone: {business_info.phone}")
            else:
                print("Could not extract business information")
            
            # Test review aggregation (this will mostly return empty results without API keys)
            reviews = await aggregator.aggregate_website_reviews(test_url)
            print(f"Found {len(reviews)} reviews")
            
            for i, review in enumerate(reviews[:3]):  # Show first 3 reviews
                print(f"Review {i+1}:")
                print(f"  Platform: {review.platform}")
                print(f"  Source: {review.source_platform}")
                print(f"  Rating: {review.rating}")
                print(f"  Text: {review.text[:100]}...")
                print(f"  Author: {review.author}")
                print(f"  Date: {review.date}")
                print()
    
    except Exception as e:
        print(f"Error during testing: {e}")

def test_website_review_creation():
    """Test creating WebsiteReview objects."""
    
    print("=== Testing WebsiteReview Creation ===")
    
    # Create sample reviews
    sample_reviews = [
        WebsiteReview(
            id="test_1",
            platform="GOOGLE_REVIEWS",
            source_platform="Google Reviews",
            rating=4,
            text="Great service and friendly staff!",
            date=datetime.now(),
            author="John Doe",
            website_url="https://example.com"
        ),
        WebsiteReview(
            id="test_2",
            platform="YELP",
            source_platform="Yelp",
            rating=2,
            text="Poor customer service, waited too long.",
            date=datetime.now(),
            author="Jane Smith",
            website_url="https://example.com"
        )
    ]
    
    print(f"Created {len(sample_reviews)} sample reviews:")
    
    for review in sample_reviews:
        print(f"- {review.platform}: {review.rating}/5 - {review.text}")
    
    return sample_reviews

async def test_platform_conversion():
    """Test platform string to enum conversion."""
    
    print("=== Testing Platform Conversion ===")
    
    from app.models.database import Platform
    
    # Test the mapping logic used in the API
    platform_mapping = {
        "GOOGLE_REVIEWS": Platform.GOOGLE_REVIEWS,
        "YELP": Platform.YELP,
        "FACEBOOK": Platform.FACEBOOK,
        "TWITTER": Platform.TWITTER,
        "GOOGLE": Platform.GOOGLE_REVIEWS,
    }
    
    test_platforms = [
        "GOOGLE_REVIEWS",
        "YELP", 
        "FACEBOOK",
        "TWITTER",
        "GOOGLE",
        "INVALID_PLATFORM"
    ]
    
    for platform_str in test_platforms:
        platform_enum = platform_mapping.get(
            platform_str.upper(), 
            Platform.GOOGLE_REVIEWS  # Default fallback
        )
        print(f"✓ {platform_str} -> {platform_enum.value}")

async def main():
    """Run all tests."""
    
    print("Website Analysis Testing")
    print("=" * 50)
    
    # Test WebsiteReview creation
    sample_reviews = test_website_review_creation()
    print()
    
    # Test platform conversion
    await test_platform_conversion()
    print()
    
    # Test WebsiteReviewAggregator
    await test_website_review_aggregator()
    print()
    
    print("=" * 50)
    print("Testing Complete!")
    print()
    print("Notes:")
    print("- The WebsiteReviewAggregator will work but may return limited results")
    print("- For full functionality, configure API keys for:")
    print("  * Google Places API (google_places_api_key)")
    print("  * Yelp Fusion API (yelp_api_key)")
    print("  * Facebook Graph API (facebook_access_token)")
    print("  * Twitter API v2 (twitter_bearer_token)")
    print("- Without API keys, it falls back to web scraping (limited)")
    print("- The system will still work and can analyze any reviews found")

if __name__ == "__main__":
    asyncio.run(main())