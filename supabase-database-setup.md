# Supabase Database Setup Guide

## Overview
Use Supabase as your PostgreSQL database with built-in auth, real-time features, and Redis-like caching.

## Why Supabase?
- **Free tier**: 500MB database, 2GB bandwidth
- **PostgreSQL**: Full-featured database with extensions
- **Built-in features**: Auth, real-time, storage, edge functions
- **Redis alternative**: Built-in caching and real-time subscriptions
- **Cost**: Free tier → $25/month for production

## Quick Setup

### 1. Create Supabase Project
1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project"
3. Create new organization (if needed)
4. Create new project:
   - **Name**: review-gap-analyzer
   - **Database Password**: Generate strong password
   - **Region**: Choose closest to your users

### 2. Get Connection Details
```bash
# From Supabase Dashboard > Settings > Database
DATABASE_URL="postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres"
SUPABASE_URL="https://[project-ref].supabase.co"
SUPABASE_ANON_KEY="your-anon-key"
SUPABASE_SERVICE_KEY="your-service-role-key"
```

### 3. Configure Backend for Supabase

Update `backend/app/database/connection.py`:
```python
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from supabase import create_client, Client

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Configure SSL for Supabase
if "supabase.co" in DATABASE_URL:
    DATABASE_URL += "?sslmode=require"

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=os.getenv("ENVIRONMENT") == "development"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Supabase client for additional features
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = None
if supabase_url and supabase_key:
    supabase = create_client(supabase_url, supabase_key)

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_supabase_client():
    return supabase
```

### 4. Add Supabase Dependencies
Add to `backend/requirements.txt`:
```txt
supabase==2.3.0
postgrest==0.13.0
```

### 5. Database Schema Setup

Create `backend/supabase_schema.sql`:
```sql
-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create custom types
CREATE TYPE analysis_status AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE review_sentiment AS ENUM ('positive', 'negative', 'neutral');

-- Apps table
CREATE TABLE apps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    package_id VARCHAR(255) UNIQUE NOT NULL,
    platform VARCHAR(50) NOT NULL CHECK (platform IN ('ios', 'android')),
    category VARCHAR(100),
    description TEXT,
    icon_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Reviews table
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id UUID REFERENCES apps(id) ON DELETE CASCADE,
    review_id VARCHAR(255) NOT NULL,
    author VARCHAR(255),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(500),
    content TEXT NOT NULL,
    date TIMESTAMP WITH TIME ZONE,
    sentiment review_sentiment,
    sentiment_score DECIMAL(3,2),
    language VARCHAR(10),
    helpful_count INTEGER DEFAULT 0,
    platform VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(app_id, review_id, platform)
);

-- Analysis results table
CREATE TABLE analysis_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id UUID REFERENCES apps(id) ON DELETE CASCADE,
    status analysis_status DEFAULT 'pending',
    total_reviews INTEGER DEFAULT 0,
    processed_reviews INTEGER DEFAULT 0,
    sentiment_distribution JSONB,
    pain_points JSONB,
    feature_requests JSONB,
    clusters JSONB,
    insights JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Pain points table
CREATE TABLE pain_points (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID REFERENCES analysis_results(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    severity_score DECIMAL(3,2),
    frequency INTEGER DEFAULT 1,
    example_reviews TEXT[],
    suggested_solutions TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Feature requests table
CREATE TABLE feature_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID REFERENCES analysis_results(id) ON DELETE CASCADE,
    feature VARCHAR(255) NOT NULL,
    description TEXT,
    priority_score DECIMAL(3,2),
    request_count INTEGER DEFAULT 1,
    example_reviews TEXT[],
    implementation_complexity VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_reviews_app_id ON reviews(app_id);
CREATE INDEX idx_reviews_sentiment ON reviews(sentiment);
CREATE INDEX idx_reviews_rating ON reviews(rating);
CREATE INDEX idx_reviews_date ON reviews(date);
CREATE INDEX idx_reviews_content_gin ON reviews USING gin(to_tsvector('english', content));
CREATE INDEX idx_apps_package_id ON apps(package_id);
CREATE INDEX idx_analysis_results_app_id ON analysis_results(app_id);
CREATE INDEX idx_analysis_results_status ON analysis_results(status);
CREATE INDEX idx_pain_points_analysis_id ON pain_points(analysis_id);
CREATE INDEX idx_feature_requests_analysis_id ON feature_requests(analysis_id);

-- Row Level Security (RLS) policies
ALTER TABLE apps ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE pain_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE feature_requests ENABLE ROW LEVEL SECURITY;

-- Public access policies (adjust based on your auth requirements)
CREATE POLICY "Public apps access" ON apps FOR ALL USING (true);
CREATE POLICY "Public reviews access" ON reviews FOR ALL USING (true);
CREATE POLICY "Public analysis access" ON analysis_results FOR ALL USING (true);
CREATE POLICY "Public pain points access" ON pain_points FOR ALL USING (true);
CREATE POLICY "Public feature requests access" ON feature_requests FOR ALL USING (true);

-- Functions for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_apps_updated_at BEFORE UPDATE ON apps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analysis_results_updated_at BEFORE UPDATE ON analysis_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate sentiment distribution
CREATE OR REPLACE FUNCTION calculate_sentiment_distribution(app_uuid UUID)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'positive', COUNT(*) FILTER (WHERE sentiment = 'positive'),
        'negative', COUNT(*) FILTER (WHERE sentiment = 'negative'),
        'neutral', COUNT(*) FILTER (WHERE sentiment = 'neutral'),
        'total', COUNT(*)
    ) INTO result
    FROM reviews
    WHERE app_id = app_uuid;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to get top pain points
CREATE OR REPLACE FUNCTION get_top_pain_points(app_uuid UUID, limit_count INTEGER DEFAULT 10)
RETURNS TABLE(category VARCHAR, description TEXT, frequency INTEGER, severity DECIMAL) AS $$
BEGIN
    RETURN QUERY
    SELECT pp.category, pp.description, pp.frequency, pp.severity_score
    FROM pain_points pp
    JOIN analysis_results ar ON pp.analysis_id = ar.id
    WHERE ar.app_id = app_uuid
    ORDER BY pp.severity_score DESC, pp.frequency DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;
```

### 6. Run Schema Setup
```bash
# Via Supabase Dashboard
# Go to SQL Editor > New Query
# Paste the schema and run

# Or via CLI
npx supabase db reset
```

### 7. Caching Strategy (Redis Alternative)

Since Supabase doesn't include Redis, use these alternatives:

#### Option A: Supabase Edge Functions for Caching
```typescript
// supabase/functions/cache-service/index.ts
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const cache = new Map<string, { data: any, expires: number }>()

serve(async (req) => {
  const { method } = req
  const url = new URL(req.url)
  const key = url.searchParams.get('key')

  if (method === 'GET' && key) {
    const cached = cache.get(key)
    if (cached && cached.expires > Date.now()) {
      return new Response(JSON.stringify(cached.data), {
        headers: { 'Content-Type': 'application/json' }
      })
    }
    return new Response(null, { status: 404 })
  }

  if (method === 'POST' && key) {
    const data = await req.json()
    const ttl = parseInt(url.searchParams.get('ttl') || '3600') * 1000
    cache.set(key, { data, expires: Date.now() + ttl })
    return new Response('OK')
  }

  return new Response('Method not allowed', { status: 405 })
})
```

#### Option B: In-Memory Caching in Backend
```python
# backend/app/services/cache_service.py
import json
import time
from typing import Any, Optional
from datetime import datetime, timedelta

class InMemoryCache:
    def __init__(self):
        self._cache = {}
        self._expires = {}
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            if key not in self._expires or self._expires[key] > time.time():
                return self._cache[key]
            else:
                # Expired
                del self._cache[key]
                del self._expires[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        self._cache[key] = value
        self._expires[key] = time.time() + ttl
    
    def delete(self, key: str):
        self._cache.pop(key, None)
        self._expires.pop(key, None)
    
    def clear(self):
        self._cache.clear()
        self._expires.clear()

# Global cache instance
cache = InMemoryCache()
```

#### Option C: Add Upstash Redis (Free Tier)
```bash
# Add to Railway/Render environment variables
REDIS_URL="redis://default:password@redis-12345.upstash.io:12345"

# Upstash offers 10,000 requests/day free
# Perfect for caching analysis results
```

### 8. Real-time Features (Bonus)

Enable real-time updates for analysis progress:
```python
# backend/app/services/realtime_service.py
from app.database.connection import get_supabase_client

async def notify_analysis_progress(analysis_id: str, progress: dict):
    supabase = get_supabase_client()
    if supabase:
        # Update analysis result
        supabase.table('analysis_results').update({
            'processed_reviews': progress['processed'],
            'total_reviews': progress['total'],
            'updated_at': 'now()'
        }).eq('id', analysis_id).execute()
        
        # Send real-time notification
        supabase.realtime.send('analysis_progress', {
            'analysis_id': analysis_id,
            'progress': progress
        })
```

Frontend real-time subscription:
```typescript
// frontend/hooks/useAnalysisProgress.ts
import { useEffect, useState } from 'react'
import { createClient } from '@supabase/supabase-js'

export function useAnalysisProgress(analysisId: string) {
  const [progress, setProgress] = useState({ processed: 0, total: 0 })
  
  useEffect(() => {
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )
    
    const subscription = supabase
      .channel('analysis_progress')
      .on('broadcast', { event: 'analysis_progress' }, (payload) => {
        if (payload.analysis_id === analysisId) {
          setProgress(payload.progress)
        }
      })
      .subscribe()
    
    return () => {
      subscription.unsubscribe()
    }
  }, [analysisId])
  
  return progress
}
```

## Cost Breakdown

### Free Tier
- **Database**: 500MB storage
- **Bandwidth**: 2GB/month
- **Auth users**: 50,000 monthly active users
- **Edge Functions**: 500,000 invocations
- **Storage**: 1GB

### Pro Tier ($25/month)
- **Database**: 8GB storage
- **Bandwidth**: 250GB/month
- **Auth users**: 100,000 monthly active users
- **Edge Functions**: 2M invocations
- **Storage**: 100GB
- **Daily backups**

### Usage Estimates
- **Small app** (< 1000 reviews): Free tier sufficient
- **Medium app** (< 50k reviews): Free tier or Pro
- **Large app** (> 100k reviews): Pro tier recommended

## Migration from Other Databases

### From PostgreSQL
```bash
# Export existing data
pg_dump $OLD_DATABASE_URL > backup.sql

# Import to Supabase
psql $SUPABASE_DATABASE_URL < backup.sql
```

### From SQLite
```python
# Use SQLAlchemy to migrate
from sqlalchemy import create_engine
import pandas as pd

# Read from SQLite
sqlite_engine = create_engine('sqlite:///old_database.db')
df = pd.read_sql('SELECT * FROM reviews', sqlite_engine)

# Write to Supabase
supabase_engine = create_engine(SUPABASE_DATABASE_URL)
df.to_sql('reviews', supabase_engine, if_exists='append', index=False)
```

## Environment Variables Summary

Add these to your backend deployment:
```bash
# Database
DATABASE_URL="postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres?sslmode=require"

# Supabase (optional, for additional features)
SUPABASE_URL="https://[project-ref].supabase.co"
SUPABASE_ANON_KEY="your-anon-key"
SUPABASE_SERVICE_KEY="your-service-role-key"

# Cache (if using Upstash Redis)
REDIS_URL="redis://default:password@redis-12345.upstash.io:12345"
```

## Benefits Summary

✅ **Free tier for development**
✅ **Full PostgreSQL with extensions**
✅ **Built-in auth & real-time**
✅ **Automatic backups**
✅ **Dashboard for data management**
✅ **Edge functions for serverless logic**
✅ **Global CDN**
✅ **Row-level security**

Supabase gives you a production-ready database with tons of features for free, scaling to $25/month when you need more resources!