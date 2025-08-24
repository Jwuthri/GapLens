#!/usr/bin/env python3
"""Example usage of the enhanced Website Review Aggregator with all platforms."""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.website_review_aggregator import WebsiteReviewAggregator


async def demo_review_aggregation():
    """Demonstrate the review aggregation capabilities."""
    
    print("🚀 Website Review Aggregator - Enhanced Platform Support")
    print("=" * 60)
    
    # Example businesses for different platform types
    test_cases = [
        {
            "name": "Software Company",
            "website": "https://slack.com",
            "description": "Tests software review platforms (G2, Capterra, etc.)"
        },
        {
            "name": "Restaurant",
            "website": "https://mcdonalds.com",
            "description": "Tests restaurant platforms (Zomato, OpenTable)"
        },
        {
            "name": "Hotel",
            "website": "https://marriott.com",
            "description": "Tests travel platforms (TripAdvisor, Booking.com, etc.)"
        }
    ]
    
    async with WebsiteReviewAggregator() as aggregator:
        
        for test_case in test_cases:
            print(f"\n📊 Testing: {test_case['name']}")
            print(f"🌐 Website: {test_case['website']}")
            print(f"📝 {test_case['description']}")
            print("-" * 40)
            
            try:
                # Extract business info first
                business_info = await aggregator.extract_business_info(test_case['website'])
                
                if business_info:
                    print(f"✅ Business detected: {business_info.name}")
                    if business_info.address:
                        print(f"📍 Address: {business_info.address}")
                    if business_info.phone:
                        print(f"📞 Phone: {business_info.phone}")
                    
                    # Test a few specific platforms
                    platform_tests = [
                        ("G2 Reviews", aggregator.scrape_g2_reviews),
                        ("TripAdvisor Reviews", aggregator.scrape_tripadvisor_reviews),
                        ("Zomato Reviews", aggregator.scrape_zomato_reviews),
                    ]
                    
                    for platform_name, scraper_func in platform_tests:
                        try:
                            reviews = await scraper_func(business_info.name)
                            print(f"  {platform_name}: {len(reviews)} reviews found")
                        except Exception as e:
                            print(f"  {platform_name}: Error - {str(e)[:50]}...")
                
                else:
                    print("❌ Could not extract business information")
                    
            except Exception as e:
                print(f"❌ Error processing {test_case['name']}: {e}")
    
    print("\n" * 2)
    print("🎯 Platform Coverage Summary")
    print("=" * 60)
    
    platforms = [
        ("📱 App Stores", ["Google Play", "Apple App Store"]),
        ("💼 Software Reviews", ["G2", "Capterra", "TrustRadius", "Software Advice", "Product Hunt"]),
        ("✈️ Travel & Hotels", ["TripAdvisor", "Booking.com", "Expedia", "Hotels.com", "Airbnb", "Trivago", "HolidayCheck"]),
        ("🍽️ Restaurants", ["Zomato", "OpenTable"]),
        ("🌐 General Reviews", ["Google Reviews", "Yelp", "Facebook", "Twitter"])
    ]
    
    for category, platform_list in platforms:
        print(f"\n{category}")
        for platform in platform_list:
            print(f"  ✓ {platform}")
    
    print("\n🔧 Features:")
    print("  ✓ Anti-bot protection with Scrapling")
    print("  ✓ Automatic fallback to basic scraping")
    print("  ✓ Rate limiting and error handling")
    print("  ✓ Normalized review format across platforms")
    print("  ✓ Business information extraction")
    print("  ✓ Concurrent review collection")
    
    print("\n📚 For detailed usage, see: REVIEW_PLATFORMS_GUIDE.md")


if __name__ == "__main__":
    asyncio.run(demo_review_aggregation())