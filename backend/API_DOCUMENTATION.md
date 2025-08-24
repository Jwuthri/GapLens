# Review Gap Analyzer API Documentation

## Overview

The Review Gap Analyzer API provides endpoints for analyzing app store reviews and website feedback to identify user pain points and product opportunities.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, no authentication is required for API access.

## Endpoints

### 1. Submit Analysis

**POST** `/analysis/`

Submit an app or website for analysis.

#### Request Body

```json
{
  "app_url_or_id": "string (optional)",
  "website_url": "string (optional)"
}
```

**Note:** Exactly one of `app_url_or_id` or `website_url` must be provided.

#### App URL/ID Examples

- Google Play URL: `https://play.google.com/store/apps/details?id=com.example.app`
- App Store URL: `https://apps.apple.com/us/app/app-name/id123456789`
- Google Play ID: `com.example.app`
- App Store ID: `123456789`

#### Website URL Examples

- `https://example.com`
- `https://www.mybusiness.com`

#### Response

```json
{
  "analysis_id": "uuid",
  "status": "pending",
  "message": "Analysis started successfully. Check status for progress updates."
}
```

#### Status Codes

- `200`: Analysis submitted successfully
- `400`: Invalid app URL/ID format
- `422`: Validation error (missing or invalid input)
- `500`: Internal server error

### 2. Get Analysis Results

**GET** `/analysis/{analysis_id}`

Retrieve complete analysis results including clusters and summary statistics.

#### Path Parameters

- `analysis_id` (UUID): The analysis ID returned from the submit endpoint

#### Response

```json
{
  "analysis": {
    "id": "uuid",
    "app_id": "string",
    "website_url": "string",
    "analysis_type": "APP|WEBSITE",
    "platform": "google_play|app_store|google_reviews|yelp|facebook|twitter",
    "status": "completed",
    "total_reviews": 100,
    "negative_reviews": 25,
    "created_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:35:00Z",
    "clusters": [...]
  },
  "summary": {
    "total_reviews": 100,
    "negative_reviews": 25,
    "negative_percentage": 25.0,
    "analysis_date": "2024-01-15T10:35:00Z",
    "app_id": "com.example.app",
    "website_url": null,
    "analysis_type": "APP",
    "platform": "google_play"
  },
  "clusters": [
    {
      "id": "uuid",
      "analysis_id": "uuid",
      "name": "App Crashes",
      "description": "Issues related to app crashes and instability",
      "review_count": 10,
      "percentage": 40.0,
      "recency_score": 75.0,
      "sample_reviews": [
        "App crashes constantly on Android 14",
        "Keeps crashing when I try to login"
      ],
      "keywords": ["crash", "bug", "android"]
    }
  ]
}
```

#### Status Codes

- `200`: Results retrieved successfully
- `400`: Analysis not completed yet
- `404`: Analysis not found
- `500`: Internal server error

### 3. Get Analysis Status

**GET** `/analysis/{analysis_id}/status`

Check the current status and progress of an analysis.

#### Path Parameters

- `analysis_id` (UUID): The analysis ID

#### Response

```json
{
  "analysis_id": "uuid",
  "status": "processing",
  "progress": 50.0,
  "message": "Analysis is in progress"
}
```

#### Status Values

- `pending`: Analysis is queued for processing
- `processing`: Analysis is currently running
- `completed`: Analysis finished successfully
- `failed`: Analysis failed due to an error

#### Status Codes

- `200`: Status retrieved successfully
- `404`: Analysis not found
- `500`: Internal server error

### 4. Export Analysis Results

**GET** `/analysis/{analysis_id}/export`

Export analysis results in CSV or JSON format.

#### Path Parameters

- `analysis_id` (UUID): The analysis ID

#### Query Parameters

- `format` (optional): Export format (`json` or `csv`, default: `json`)

#### Response

Returns a file download with the analysis results.

**JSON Export:**
- Content-Type: `application/json`
- Contains complete analysis data in structured format

**CSV Export:**
- Content-Type: `text/csv`
- Contains flattened analysis data suitable for spreadsheet applications

#### Status Codes

- `200`: Export successful (file download)
- `400`: Analysis not completed or invalid format
- `404`: Analysis not found
- `500`: Internal server error

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

## Rate Limiting

Currently, no rate limiting is implemented, but it may be added in future versions.

## Examples

### Submit App Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/analysis/" \
  -H "Content-Type: application/json" \
  -d '{"app_url_or_id": "com.example.app"}'
```

### Submit Website Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/analysis/" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://example.com"}'
```

### Check Analysis Status

```bash
curl "http://localhost:8000/api/v1/analysis/12345678-1234-1234-1234-123456789012/status"
```

### Get Analysis Results

```bash
curl "http://localhost:8000/api/v1/analysis/12345678-1234-1234-1234-123456789012"
```

### Export as CSV

```bash
curl "http://localhost:8000/api/v1/analysis/12345678-1234-1234-1234-123456789012/export?format=csv" \
  -o analysis_results.csv
```

## Interactive API Documentation

When the server is running, you can access interactive API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Background Processing

Analysis requests are processed asynchronously in the background. The typical workflow is:

1. Submit analysis request → Receive analysis ID
2. Poll status endpoint → Monitor progress
3. When status is "completed" → Fetch results
4. Optionally export results in desired format

Processing time varies based on:
- Number of reviews to analyze
- Complexity of NLP processing
- Current system load

For apps with many reviews, processing may take several minutes.