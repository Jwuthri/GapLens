#!/usr/bin/env python3
"""
FIXED G2 Scraper - Correctly extracts real reviews from article elements
"""

import sys
import os
import re
from datetime import datetime
from typing import List

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from botasaurus.browser import browser
    BOTASAURUS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


class WebsiteReview:
    """Review data structure"""
    def __init__(self, id: str, platform: str, source_platform: str, 
                 rating: int = None, text: str = "", date: datetime = None,
                 author: str = None, website_url: str = ""):
        self.id = id
        self.platform = platform
        self.source_platform = source_platform
        self.rating = rating
        self.text = text
        self.date = date or datetime.now()
        self.author = author
        self.website_url = website_url


@browser
def scrape_g2_reviews_properly(driver, data):
    """
    Properly scrape G2 reviews from article elements
    """
    business_name = data['business_name']
    base_url = f"https://www.g2.com/products/{business_name}/reviews"
    
    print(f"🤖 Navigating to: {base_url}")
    driver.get(base_url)
    driver.sleep(5)  # Let page fully load
    
    print(f"✅ Page loaded: {driver.title}")
    
    all_reviews = []
    page_number = 1
    max_pages = 5  # Get more pages for better coverage
    
    while page_number <= max_pages:
        print(f"\n📄 Scraping G2 page {page_number}")
        
        # Get all article elements (these contain the actual reviews)
        article_elements = driver.select_all('article')
        
        if not article_elements:
            print(f"❌ No article elements found on page {page_number}")
            break
            
        print(f"📦 Found {len(article_elements)} article elements")
        
        page_reviews = 0
        
        for i, article in enumerate(article_elements):
            try:
                # Get all text from the article
                full_text = article.text
                
                if not full_text or len(full_text) < 50:
                    continue
                
                # Extract review components
                lines = full_text.split('\n')
                lines = [line.strip() for line in lines if line.strip()]
                
                # Look for author (usually first line with a name pattern)
                author = None
                for line in lines[:5]:
                    # Names typically have capital letters and periods
                    if re.match(r'^[A-Z][a-z]+ [A-Z]\.?', line):
                        author = line
                        break
                
                # Look for rating (pattern like "5/5" or "4 out of 5")
                rating = None
                rating_line = None
                for line in lines:
                    if re.search(r'\d+/5', line):
                        rating_match = re.search(r'(\d+)/5', line)
                        if rating_match:
                            rating = int(rating_match.group(1))
                            rating_line = line
                            break
                    elif 'out of 5' in line:
                        rating_match = re.search(r'(\d+(?:\.\d+)?)\s*out of 5', line)
                        if rating_match:
                            rating = int(float(rating_match.group(1)))
                            rating_line = line
                            break
                
                # Extract the main review text
                review_text = ""
                
                # Look for the review content (usually after "What do you like best" or similar)
                collecting_review = False
                for line in lines:
                    if any(phrase in line.lower() for phrase in [
                        'what do you like best',
                        'what do you dislike',
                        'review collected',
                        'pros and cons'
                    ]):
                        collecting_review = True
                        continue
                    
                    if collecting_review:
                        # Skip metadata lines
                        if any(skip in line.lower() for skip in [
                            'verified review', 'review collected', 'small-business',
                            'mid-market', 'enterprise', 'emp.', '/20'
                        ]):
                            continue
                        
                        # Stop at pagination or navigation
                        if any(stop in line.lower() for stop in [
                            'next', 'previous', 'page', 'show more'
                        ]):
                            break
                            
                        review_text += line + " "
                        
                        if len(review_text) > 300:  # Reasonable review length
                            break
                
                # If no structured review found, take meaningful chunks
                if not review_text and len(full_text) > 100:
                    # Look for quoted text (review titles)
                    quoted_text = re.findall(r'"([^"]{20,200})"', full_text)
                    if quoted_text:
                        review_text = quoted_text[0]
                    else:
                        # Take first substantial paragraph
                        paragraphs = [p for p in lines if len(p) > 30 and not any(skip in p.lower() for skip in [
                            'emp.', 'verified', 'collected', 'small-business'
                        ])]
                        if paragraphs:
                            review_text = paragraphs[0][:300]
                
                # Skip if we couldn't extract meaningful content
                if not review_text or len(review_text.strip()) < 20:
                    continue
                
                # Skip obvious UI elements
                if any(ui_text in review_text.lower() for ui_text in [
                    'edit review', 'show more', 'load more', 'filter', 'sort by'
                ]):
                    continue
                
                # Create review object
                review_data = {
                    'text': review_text.strip()[:500],  # Limit length
                    'rating': rating,
                    'author': author,
                    'page': page_number,
                    'index': i
                }
                
                all_reviews.append(review_data)
                page_reviews += 1
                
                print(f"  ✅ Review {page_reviews}: {author} - {rating}/5 - \"{review_text[:50]}...\"")
                
                # Limit reviews per page
                if page_reviews >= 10:
                    break
                
            except Exception as e:
                print(f"  ❌ Error processing article {i}: {e}")
                continue
        
        print(f"✅ Extracted {page_reviews} real reviews from page {page_number}")
        
        # Try to go to next page
        if page_number < max_pages and page_reviews > 0:
            try:
                # Look for pagination
                next_selectors = [
                    'a[aria-label*="Next"]',
                    'a[aria-label*="next"]', 
                    '.pagination-next',
                    '[class*="next"]'
                ]
                
                clicked_next = False
                for selector in next_selectors:
                    try:
                        next_btn = driver.select(selector)
                        if next_btn:
                            print(f"🔄 Clicking next page button...")
                            next_btn.click()
                            driver.sleep(4)  # Wait for page load
                            clicked_next = True
                            break
                    except Exception:
                        continue
                
                if not clicked_next:
                    print("⏹️ No next button found, ending pagination")
                    break
                    
            except Exception as e:
                print(f"❌ Error navigating to next page: {e}")
                break
        else:
            break
        
        page_number += 1
    
    print(f"\n🎯 TOTAL REVIEWS EXTRACTED: {len(all_reviews)}")
    return all_reviews


def test_fixed_g2_scraper():
    """Test the fixed G2 scraper"""
    
    businesses = ['gorgias']  # Focus on one for detailed testing
    
    for business in businesses:
        print(f"\n{'='*60}")
        print(f"TESTING FIXED G2 SCRAPER: {business}")
        print('='*60)
        
        try:
            # Execute scraper
            raw_reviews = scrape_g2_reviews_properly({'business_name': business})
            
            # Convert to WebsiteReview objects
            website_reviews = []
            for review_data in raw_reviews:
                review = WebsiteReview(
                    id=f"g2_fixed_{business}_{review_data['page']}_{review_data['index']}",
                    platform="G2",
                    source_platform="G2 (Fixed)",
                    rating=review_data['rating'],
                    text=review_data['text'],
                    date=datetime.now(),
                    author=review_data['author'],
                    website_url=f"https://www.g2.com/products/{business}/reviews"
                )
                website_reviews.append(review)
            
            # Display results
            if website_reviews:
                print(f"\n🎉 SUCCESS: Extracted {len(website_reviews)} REAL reviews!")
                print(f"📊 G2 shows 528 total reviews - we got {len(website_reviews)}")
                
                # Show first 3 reviews
                for i, review in enumerate(website_reviews[:3]):
                    print(f"\n📝 REAL Review {i+1}:")
                    print(f"   👤 Author: {review.author}")
                    print(f"   ⭐ Rating: {review.rating}/5")
                    print(f"   💬 Text: {review.text[:100]}...")
                    
            else:
                print("❌ No reviews extracted")
                
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_fixed_g2_scraper()
