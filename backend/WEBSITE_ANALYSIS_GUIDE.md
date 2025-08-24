# Website Analysis Guide

## Overview

Yes, the backend repository is designed to work with website URLs that don't have apps on any store. The system can fetch reviews from multiple websites and platforms for any business website.

## How Website Analysis Works

### 1. Business Information Extraction

When you submit a website URL (e.g., `https://mybusiness.com`), the system:

1. **Scrapes the website** to extract business information:
   - Business name (from meta tags, title, h1 tags, or domain)
   - Address (from structured data or contact sections)
   - Phone number (using regex patterns)

2. **Uses this information** to search for the business on review platforms

### 2. Multi-Platform Review Aggregation

The `WebsiteReviewAggregator` service searches for reviews across multiple platforms:

#### Supported Platforms:
- **Google Reviews** (via Google Places API or web scraping)
- **Yelp** (via Yelp Fusion API or web scraping)
- **Facebook** (via Facebook Graph API)
- **Twitter** (via Twitter API v2 for mentions)

#### How It Works:
1. Extract business name from website
2. Search each platform for the business
3. Collect reviews from all found sources
4. Normalize and standardize the review data
5. Store in database for analysis

### 3. API Configuration

The system supports both API-based and web scraping approaches:

#### With API Keys (Recommended):
```python
aggregator = WebsiteReviewAggregator()
aggregator.configure_apis(
    google_places_api_key="your_google_api_key",
    yelp_api_key="your_yelp_api_key",
    facebook_access_token="your_facebook_token",
    twitter_bearer_token="your_twitter_token"
)
```

#### Without API Keys (Fallback):
- Falls back to web scraping methods
- Limited functionality but still works
- May have rate limiting and reliability issues

## Example Usage

### Submit Website Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/analysis/" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://mybusiness.com"}'
```

### Response
```json
{
  "analysis_id": "12345678-1234-1234-1234-123456789012",
  "status": "pending",
  "message": "Analysis started successfully. Check status for progress updates."
}
```

## What Happens During Analysis

### Step 1: Website Scraping
```
https://mybusiness.com → Extract business info
├── Business Name: "My Business LLC"
├── Address: "123 Main St, City, State"
└── Phone: "(555) 123-4567"
```

### Step 2: Multi-Platform Search
```
"My Business LLC" → Search across platforms
├── Google Reviews: Find place_id → Get reviews
├── Yelp: Search business → Get reviews  
├── Facebook: Search pages → Get reviews
└── Twitter: Search mentions → Get tweets
```

### Step 3: Review Normalization
```
Raw Reviews → Standardized Format
├── Platform: "GOOGLE_REVIEWS" | "YELP" | "FACEBOOK" | "TWITTER"
├── Rating: 1-5 scale (normalized)
├── Text: Cleaned and validated
├── Date: Standardized datetime
└── Author: Extracted when available
```

### Step 4: Analysis Processing
```
Normalized Reviews → NLP Analysis
├── Filter negative reviews (≤2 stars or negative sentiment)
├── Clean and preprocess text
├── Cluster similar complaints
├── Generate insights and recommendations
└── Store results in database
```

## Review Data Structure

Each review is stored with:

```python
{
    "id": "unique_review_id",
    "website_url": "https://mybusiness.com",
    "platform": "google_reviews",  # Enum value
    "source_platform": "Google Reviews",  # Human readable
    "rating": 4,  # 1-5 scale
    "text": "Great service and friendly staff!",
    "review_date": "2024-01-15T10:30:00Z",
    "author": "John Doe",
    "locale": "en"
}
```

## Supported Website Types

The system works with any business website:

✅ **Restaurant websites** → Finds Google/Yelp reviews  
✅ **Service businesses** → Aggregates from multiple platforms  
✅ **E-commerce sites** → Collects customer feedback  
✅ **Local businesses** → Searches location-based reviews  
✅ **Professional services** → Finds testimonials and reviews  

## Configuration Requirements

### For Full Functionality:

1. **Google Places API Key**
   - Enable Places API in Google Cloud Console
   - Required for Google Reviews access

2. **Yelp Fusion API Key**
   - Register at Yelp Developers
   - Required for Yelp reviews access

3. **Facebook Graph API Token**
   - Create Facebook App
   - Required for Facebook reviews/mentions

4. **Twitter API v2 Bearer Token**
   - Apply for Twitter Developer access
   - Required for Twitter mentions

### Environment Variables:
```bash
GOOGLE_PLACES_API_KEY=your_key_here
YELP_API_KEY=your_key_here
FACEBOOK_ACCESS_TOKEN=your_token_here
TWITTER_BEARER_TOKEN=your_token_here
```

## Limitations and Considerations

### Current Limitations:
- Web scraping fallbacks have limited functionality
- Some platforms may require additional verification
- Rate limits apply to API calls
- Review availability depends on business presence on platforms

### Best Practices:
- Configure API keys for reliable results
- Handle cases where no reviews are found
- Monitor API usage and costs
- Respect platform terms of service

## Testing

Run the website analysis test:

```bash
cd backend
python test_website_analysis.py
```

This will test:
- Business information extraction
- Platform conversion
- Review aggregation workflow
- Error handling

## Error Handling

The system gracefully handles:
- Websites with no extractable business info
- Businesses not found on review platforms  
- API failures and rate limits
- Invalid or malformed review data
- Network connectivity issues

If no reviews are found, the analysis will complete with empty results rather than failing.

## Future Enhancements

Potential improvements:
- Additional review platforms (TripAdvisor, Amazon, etc.)
- Better business name matching algorithms
- Sentiment analysis for platforms without ratings
- Real-time review monitoring
- Review response suggestions