#!/usr/bin/env python3
"""Test script for new review platforms integration."""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.website_review_aggregator import WebsiteReviewAggregator


async def test_new_platforms():
    """Test the new review platforms."""
    
    # Test business name
    test_business = "Slack"
    
    async with WebsiteReviewAggregator() as aggregator:
        print(f"Testing review aggregation for: {test_business}")
        print("=" * 50)
        
        # Test individual platforms
        platforms_to_test = [
            ("G2", aggregator.scrape_g2_reviews),
            ("Capterra", aggregator.scrape_capterra_reviews),
            ("TrustRadius", aggregator.scrape_trustradius_reviews),
            ("Software Advice", aggregator.scrape_software_advice_reviews),
            ("Product Hunt", aggregator.scrape_product_hunt_reviews),
            ("TripAdvisor", aggregator.scrape_tripadvisor_reviews),
            ("Zomato", aggregator.scrape_zomato_reviews),
        ]
        
        for platform_name, scraper_method in platforms_to_test:
            print(f"\nTesting {platform_name}...")
            try:
                reviews = await scraper_method(test_business)
                print(f"✓ {platform_name}: Found {len(reviews)} reviews")
                
                # Show first review if available
                if reviews:
                    first_review = reviews[0]
                    print(f"  Sample review: {first_review.text[:100]}...")
                    print(f"  Rating: {first_review.rating}")
                    print(f"  Author: {first_review.author}")
                
            except Exception as e:
                print(f"✗ {platform_name}: Error - {e}")
        
        print("\n" + "=" * 50)
        print("Testing complete aggregation...")
        
        # Test full aggregation (this will test website extraction too)
        try:
            all_reviews = await aggregator.aggregate_website_reviews("https://slack.com")
            print(f"✓ Full aggregation: Found {len(all_reviews)} total reviews")
            
            # Group by platform
            platform_counts = {}
            for review in all_reviews:
                platform_counts[review.source_platform] = platform_counts.get(review.source_platform, 0) + 1
            
            print("\nReviews by platform:")
            for platform, count in platform_counts.items():
                print(f"  {platform}: {count} reviews")
                
        except Exception as e:
            print(f"✗ Full aggregation: Error - {e}")


if __name__ == "__main__":
    asyncio.run(test_new_platforms())