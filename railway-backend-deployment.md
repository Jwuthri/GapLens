# Railway Backend Deployment Guide

## Overview
Deploy the FastAPI backend to Railway - a modern platform with simple deployments and fair pricing.

## Why Railway?
- **Cost**: $5/month for 512MB RAM, $10/month for 1GB
- **Simple**: Git-based deployments
- **Features**: Built-in PostgreSQL, Redis, monitoring
- **Scaling**: Easy horizontal and vertical scaling

## Prerequisites
- Railway account (free trial)
- GitHub repository
- Railway CLI (optional)

## Quick Setup

### 1. Install Railway CLI
```bash
npm install -g @railway/cli
railway login
```

### 2. Prepare Backend for Railway

Create `railway.json` in backend directory:
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile.railway"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

Create `Dockerfile.railway` in backend directory:
```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Expose port (Railway will set PORT env var)
EXPOSE $PORT

# Run the application
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
```

### 3. Deploy to Railway

#### Option A: GitHub Integration (Recommended)
1. Go to [railway.app](https://railway.app)
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Select the backend directory
6. Railway will auto-detect and deploy

#### Option B: CLI Deployment
```bash
cd backend
railway login
railway init
railway up
```

### 4. Add Environment Variables
```bash
# Via CLI
railway variables set SECRET_KEY="your-secret-key"
railway variables set ENVIRONMENT="production"
railway variables set LOG_LEVEL="INFO"

# Via Dashboard
# Go to your project > Variables tab
```

### 5. Add PostgreSQL Database
```bash
# Add PostgreSQL plugin
railway add postgresql

# Railway will automatically set DATABASE_URL
# No additional configuration needed!
```

### 6. Add Redis (Optional)
```bash
# Add Redis plugin
railway add redis

# Railway will automatically set REDIS_URL
```

## Environment Variables Setup

Railway automatically provides:
- `DATABASE_URL` (when PostgreSQL is added)
- `REDIS_URL` (when Redis is added)
- `PORT` (automatically set)
- `RAILWAY_ENVIRONMENT` (production/staging)

Add these manually:
```bash
railway variables set SECRET_KEY="$(openssl rand -hex 32)"
railway variables set ENVIRONMENT="production"
railway variables set LOG_LEVEL="INFO"
railway variables set CORS_ORIGINS="https://your-vercel-app.vercel.app"
```

## Database Migrations

### Automatic Migrations on Deploy
Add to `railway.json`:
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile.railway"
  },
  "deploy": {
    "startCommand": "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health"
  }
}
```

### Manual Migrations
```bash
# Connect to your Railway project
railway shell

# Run migrations
alembic upgrade head
```

## Scaling & Performance

### Vertical Scaling
```bash
# Upgrade to higher memory/CPU
# Via Dashboard: Settings > Resources
# Plans: $5 (512MB), $10 (1GB), $20 (2GB)
```

### Horizontal Scaling
```bash
# Scale to multiple instances
railway scale --replicas 2
```

### Auto-scaling (Pro plan)
```json
{
  "deploy": {
    "autoScale": {
      "minReplicas": 1,
      "maxReplicas": 5,
      "targetCPU": 70,
      "targetMemory": 80
    }
  }
}
```

## Monitoring & Logs

### View Logs
```bash
# Via CLI
railway logs

# Via Dashboard
# Project > Deployments > View Logs
```

### Metrics
- CPU usage
- Memory usage
- Request count
- Response times
- Error rates

### Alerts
```bash
# Set up alerts via Dashboard
# Settings > Notifications
# Configure for high CPU, memory, or error rates
```

## Custom Domain

### Add Domain
```bash
# Via CLI
railway domain add yourdomain.com

# Via Dashboard
# Settings > Domains > Add Domain
```

### DNS Configuration
```bash
# Add CNAME record:
# api.yourdomain.com -> your-app.railway.app
```

## Cost Optimization

### Starter Plan ($5/month)
- 512MB RAM, 1 vCPU
- Good for low-traffic apps
- Includes PostgreSQL

### Developer Plan ($10/month)
- 1GB RAM, 1 vCPU
- Better for production apps
- Includes PostgreSQL + Redis

### Pro Plan ($20/month)
- 2GB RAM, 2 vCPU
- Auto-scaling
- Priority support

## Alternative: Render

If you prefer Render over Railway:

### Render Setup
```yaml
# render.yaml
services:
  - type: web
    name: review-gap-analyzer-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: LOG_LEVEL
        value: INFO
      - key: DATABASE_URL
        fromDatabase:
          name: review-gap-analyzer-db
          property: connectionString

databases:
  - name: review-gap-analyzer-db
    databaseName: review_gap_analyzer_prod
    user: app_user
```

### Render Pricing
- **Free**: 512MB RAM, sleeps after 15min inactivity
- **Starter**: $7/month, 512MB RAM, no sleep
- **Standard**: $25/month, 2GB RAM

## Alternative: DigitalOcean App Platform

### DigitalOcean Setup
```yaml
# .do/app.yaml
name: review-gap-analyzer
services:
- name: backend
  source_dir: backend
  github:
    repo: your-username/your-repo
    branch: main
  run_command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 8000
  health_check:
    http_path: /health
  envs:
  - key: ENVIRONMENT
    value: production
  - key: DATABASE_URL
    value: ${db.DATABASE_URL}

databases:
- name: db
  engine: PG
  version: "15"
  size_slug: db-s-dev-database
```

### DigitalOcean Pricing
- **Basic**: $5/month, 512MB RAM
- **Professional**: $12/month, 1GB RAM
- **Database**: $15/month for managed PostgreSQL

## Deployment Script

Create `deploy-railway.sh`:
```bash
#!/bin/bash
set -e

echo "🚀 Deploying to Railway..."

# Check if railway CLI is installed
command -v railway >/dev/null 2>&1 || { 
    echo "❌ Railway CLI not installed. Run: npm install -g @railway/cli"
    exit 1
}

# Login check
railway whoami >/dev/null 2>&1 || {
    echo "❌ Not logged in to Railway. Run: railway login"
    exit 1
}

cd backend

# Deploy
echo "📦 Deploying backend..."
railway up

# Run migrations
echo "🗄️ Running database migrations..."
railway run alembic upgrade head

# Check health
echo "🏥 Checking health..."
RAILWAY_URL=$(railway status --json | jq -r '.deployments[0].url')
if curl -f "$RAILWAY_URL/health" > /dev/null 2>&1; then
    echo "✅ Backend deployed successfully!"
    echo "🌐 URL: $RAILWAY_URL"
else
    echo "❌ Health check failed"
    exit 1
fi

echo "🎉 Deployment complete!"
echo "📊 Monitor: https://railway.app/dashboard"
```

## Benefits Summary

### Railway
✅ **Simple deployments**
✅ **Built-in PostgreSQL & Redis**
✅ **Fair pricing ($5-20/month)**
✅ **Auto-scaling**
✅ **Good monitoring**
✅ **No cold starts**

### Total Cost Comparison
- **Railway + Supabase**: $5-15/month
- **Render + Supabase**: $7-25/month  
- **DigitalOcean + Supabase**: $5-15/month
- **AWS ECS**: $85-95/month

Railway is perfect for your use case - simple, affordable, and reliable!