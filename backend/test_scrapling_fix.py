#!/usr/bin/env python3
"""Test script to verify scrapling fix."""

import asyncio
from app.services.website_review_aggregator import WebsiteReviewAggregator

async def test_scrapling():
    """Test that scrapling works correctly."""
    aggregator = WebsiteReviewAggregator()
    
    # Test the scraping method
    try:
        soup = await aggregator._scrape_with_scrapling("https://httpbin.org/html")
        if soup:
            print("✓ Scrapling fix works - successfully scraped test page")
            print(f"  Page title: {soup.title.string if soup.title else 'No title'}")
        else:
            print("✗ Scrapling returned None")
    except Exception as e:
        print(f"✗ Scrapling error: {e}")
    
    # Close the session if it exists
    if hasattr(aggregator, 'session') and aggregator.session:
        await aggregator.session.close()

if __name__ == "__main__":
    asyncio.run(test_scrapling())