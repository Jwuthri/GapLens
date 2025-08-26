# Hybrid Deployment Guide: Vercel + Railway + Supabase

## Overview
Deploy your Review Gap Analyzer using the most cost-effective modern stack:
- **Frontend**: Vercel (Free)
- **Backend**: Railway ($5-10/month)
- **Database**: Supabase (Free → $25/month)

**Total Cost: $5-35/month** (vs $85+ for AWS ECS)

## Architecture Diagram
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Vercel      │    │     Railway     │    │    Supabase     │
│   (Frontend)    │───▶│   (Backend)     │───▶│   (Database)    │
│                 │    │                 │    │                 │
│ • Next.js       │    │ • FastAPI       │    │ • PostgreSQL    │
│ • Static Sites  │    │ • Python        │    │ • Auth          │
│ • CDN           │    │ • Auto-deploy   │    │ • Real-time     │
│ • Free SSL      │    │ • Monitoring    │    │ • Storage       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start Deployment

### 1. Setup Supabase Database
```bash
# 1. Create Supabase project at supabase.com
# 2. Copy connection details
# 3. Run the schema from supabase-database-setup.md
```

### 2. Deploy Backend to Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
cd backend
railway login
railway init
railway up

# Add environment variables
railway variables set DATABASE_URL="postgresql://postgres:password@db.project.supabase.co:5432/postgres?sslmode=require"
railway variables set SECRET_KEY="$(openssl rand -hex 32)"
railway variables set ENVIRONMENT="production"
railway variables set CORS_ORIGINS="https://your-app.vercel.app"
```

### 3. Deploy Frontend to Vercel
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd frontend
vercel

# Add environment variables
vercel env add NEXT_PUBLIC_API_URL production
# Enter: https://your-backend.railway.app
```

## Detailed Setup

### Step 1: Supabase Database Setup

1. **Create Project**
   - Go to [supabase.com](https://supabase.com)
   - Create new project: `review-gap-analyzer`
   - Choose region closest to your users
   - Generate strong database password

2. **Setup Schema**
   - Go to SQL Editor in Supabase dashboard
   - Run the schema from `supabase-database-setup.md`
   - Verify tables are created

3. **Get Connection Details**
   ```bash
   # From Settings > Database
   DATABASE_URL="postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres?sslmode=require"
   SUPABASE_URL="https://[project-ref].supabase.co"
   SUPABASE_ANON_KEY="your-anon-key"
   ```

### Step 2: Backend Deployment (Railway)

1. **Prepare Backend**
   ```bash
   cd backend
   
   # Create Railway-specific Dockerfile
   cat > Dockerfile.railway << 'EOF'
   FROM python:3.11-slim
   
   ENV PYTHONDONTWRITEBYTECODE=1 \
       PYTHONUNBUFFERED=1 \
       PYTHONPATH=/app
   
   WORKDIR /app
   
   RUN apt-get update && apt-get install -y \
       build-essential curl && \
       rm -rf /var/lib/apt/lists/*
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY . .
   
   RUN adduser --disabled-password appuser && \
       chown -R appuser:appuser /app
   USER appuser
   
   HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
       CMD curl -f http://localhost:$PORT/health || exit 1
   
   CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
   EOF
   ```

2. **Deploy to Railway**
   ```bash
   railway login
   railway init
   railway up
   ```

3. **Configure Environment Variables**
   ```bash
   railway variables set DATABASE_URL="your-supabase-database-url"
   railway variables set SECRET_KEY="$(openssl rand -hex 32)"
   railway variables set ENVIRONMENT="production"
   railway variables set LOG_LEVEL="INFO"
   railway variables set CORS_ORIGINS="https://your-app.vercel.app"
   ```

4. **Run Database Migrations**
   ```bash
   railway run alembic upgrade head
   ```

### Step 3: Frontend Deployment (Vercel)

1. **Configure Frontend**
   ```bash
   cd frontend
   
   # Create vercel.json
   cat > vercel.json << 'EOF'
   {
     "framework": "nextjs",
     "buildCommand": "npm run build",
     "outputDirectory": ".next",
     "rewrites": [
       {
         "source": "/api/:path*",
         "destination": "https://your-backend.railway.app/:path*"
       }
     ],
     "headers": [
       {
         "source": "/(.*)",
         "headers": [
           { "key": "X-Frame-Options", "value": "DENY" },
           { "key": "X-Content-Type-Options", "value": "nosniff" },
           { "key": "Referrer-Policy", "value": "origin-when-cross-origin" }
         ]
       }
     ]
   }
   EOF
   ```

2. **Deploy to Vercel**
   ```bash
   vercel login
   vercel
   
   # Follow prompts:
   # - Link to existing project? N
   # - Project name: review-gap-analyzer
   # - Directory: ./
   ```

3. **Configure Environment Variables**
   ```bash
   # Get your Railway backend URL first
   RAILWAY_URL=$(railway status --json | jq -r '.deployments[0].url')
   
   # Add to Vercel
   vercel env add NEXT_PUBLIC_API_URL production
   # Enter: $RAILWAY_URL
   
   vercel env add NEXT_PUBLIC_SUPABASE_URL production
   # Enter: your-supabase-url
   
   vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
   # Enter: your-supabase-anon-key
   ```

## Automated Deployment Script

Create `deploy-hybrid.sh`:
```bash
#!/bin/bash
set -e

echo "🚀 Hybrid Deployment: Vercel + Railway + Supabase"

# Check prerequisites
command -v railway >/dev/null 2>&1 || { echo "❌ Railway CLI required"; exit 1; }
command -v vercel >/dev/null 2>&1 || { echo "❌ Vercel CLI required"; exit 1; }

# Configuration
read -p "Enter your Supabase Database URL: " DATABASE_URL
read -p "Enter your Supabase Project URL: " SUPABASE_URL
read -p "Enter your Supabase Anon Key: " SUPABASE_ANON_KEY

echo "📦 Deploying backend to Railway..."
cd backend

# Deploy backend
railway up

# Configure environment variables
railway variables set DATABASE_URL="$DATABASE_URL"
railway variables set SECRET_KEY="$(openssl rand -hex 32)"
railway variables set ENVIRONMENT="production"
railway variables set LOG_LEVEL="INFO"

# Run migrations
echo "🗄️ Running database migrations..."
railway run alembic upgrade head

# Get Railway URL
RAILWAY_URL=$(railway status --json | jq -r '.deployments[0].url')
echo "✅ Backend deployed: $RAILWAY_URL"

# Update CORS origins
railway variables set CORS_ORIGINS="https://your-app.vercel.app"

cd ../frontend

echo "🌐 Deploying frontend to Vercel..."

# Deploy frontend
vercel --prod

# Configure environment variables
vercel env add NEXT_PUBLIC_API_URL production --value="$RAILWAY_URL"
vercel env add NEXT_PUBLIC_SUPABASE_URL production --value="$SUPABASE_URL"
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production --value="$SUPABASE_ANON_KEY"

# Redeploy with environment variables
vercel --prod

VERCEL_URL=$(vercel ls | grep production | awk '{print $2}')
echo "✅ Frontend deployed: $VERCEL_URL"

# Update CORS origins with actual Vercel URL
cd ../backend
railway variables set CORS_ORIGINS="$VERCEL_URL"

echo ""
echo "🎉 Deployment Complete!"
echo "📊 URLs:"
echo "   Frontend: $VERCEL_URL"
echo "   Backend: $RAILWAY_URL"
echo "   Database: Supabase Dashboard"
echo ""
echo "💰 Monthly Cost Estimate:"
echo "   Vercel: $0 (Free tier)"
echo "   Railway: $5-10 (Starter/Developer)"
echo "   Supabase: $0-25 (Free → Pro)"
echo "   Total: $5-35/month"
```

## Cost Comparison

### Hybrid Stack (Vercel + Railway + Supabase)
| Service | Free Tier | Paid Tier | Monthly Cost |
|---------|-----------|-----------|--------------|
| **Vercel** | 100GB bandwidth | 1TB bandwidth | $0 → $20 |
| **Railway** | $5 trial credit | 512MB-2GB RAM | $5 → $20 |
| **Supabase** | 500MB DB | 8GB DB | $0 → $25 |
| **Total** | **$5/month** | **$65/month** | **Average: $15-25** |

### vs. Traditional Hosting
| Platform | Monthly Cost | Complexity | Features |
|----------|--------------|------------|----------|
| **Hybrid Stack** | $5-35 | Low | Modern, scalable |
| **AWS ECS** | $85-150 | High | Full control |
| **Heroku** | $50-100 | Low | Simple but expensive |
| **DigitalOcean** | $20-60 | Medium | Good value |
| **VPS** | $10-30 | High | Manual everything |

## Monitoring & Maintenance

### Railway Monitoring
```bash
# View logs
railway logs

# Check status
railway status

# Scale up
railway variables set RAILWAY_REPLICA_COUNT=2
```

### Vercel Monitoring
```bash
# View deployments
vercel ls

# Check logs
vercel logs

# View analytics
# Dashboard: vercel.com/dashboard
```

### Supabase Monitoring
- **Dashboard**: Monitor database usage, queries
- **Logs**: View real-time database logs
- **Metrics**: Track API usage, storage

## Scaling Strategy

### Traffic Growth Plan
1. **0-1K users**: Free tiers (cost: $5/month)
2. **1K-10K users**: Upgrade Railway to Developer ($10/month)
3. **10K-50K users**: Upgrade Supabase to Pro ($25/month)
4. **50K+ users**: Scale Railway replicas, consider Vercel Pro

### Performance Optimization
```bash
# Enable Railway auto-scaling
railway variables set RAILWAY_AUTOSCALE_MIN=1
railway variables set RAILWAY_AUTOSCALE_MAX=5

# Vercel Edge Functions for caching
# Supabase Edge Functions for complex queries
```

## Backup & Recovery

### Database Backups (Supabase)
- **Automatic**: Daily backups on Pro plan
- **Manual**: Export via dashboard or CLI
- **Point-in-time**: Recovery available on Pro

### Code Backups
- **Git**: All code in version control
- **Vercel**: Automatic deployment history
- **Railway**: Deployment rollback available

## Security Checklist

### Environment Variables
- ✅ Never commit secrets to git
- ✅ Use different keys for dev/prod
- ✅ Rotate secrets regularly

### Database Security
- ✅ Enable Row Level Security (RLS)
- ✅ Use connection pooling
- ✅ Monitor for unusual queries

### API Security
- ✅ CORS properly configured
- ✅ Rate limiting enabled
- ✅ Input validation on all endpoints

## Troubleshooting

### Common Issues

#### CORS Errors
```bash
# Update Railway CORS settings
railway variables set CORS_ORIGINS="https://your-actual-vercel-url.vercel.app"
```

#### Database Connection Issues
```bash
# Check Supabase connection
railway run python -c "import psycopg2; psycopg2.connect('$DATABASE_URL')"
```

#### Build Failures
```bash
# Check Railway logs
railway logs

# Check Vercel logs
vercel logs
```

## Benefits Summary

### Why This Stack Rocks
✅ **Cost-effective**: $5-35/month vs $85+ for AWS
✅ **Simple deployment**: Git-based, no complex configs
✅ **Auto-scaling**: Handles traffic spikes automatically
✅ **Modern features**: Real-time, edge functions, CDN
✅ **Great DX**: Excellent developer experience
✅ **Production-ready**: Used by thousands of companies

This hybrid approach gives you the best of all worlds: Vercel's excellent frontend hosting, Railway's simple backend deployment, and Supabase's powerful database features - all at a fraction of the cost of traditional cloud providers!

Ready to deploy? Run the deployment script and you'll be live in minutes! 🚀