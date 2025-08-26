#!/bin/bash
set -e

echo "🚀 Hybrid Deployment: Vercel + Railway + Supabase"

# Check prerequisites
command -v railway >/dev/null 2>&1 || { echo "❌ Railway CLI required: npm install -g @railway/cli"; exit 1; }
command -v vercel >/dev/null 2>&1 || { echo "❌ Vercel CLI required: npm install -g vercel"; exit 1; }

# Configuration
echo "📋 Please provide your Supabase details:"
read -p "Enter your Supabase Database URL: " DATABASE_URL
read -p "Enter your Supabase Project URL: " SUPABASE_URL
read -p "Enter your Supabase Anon Key: " SUPABASE_ANON_KEY

echo ""
echo "📦 Deploying backend to Railway..."
cd backend

# Deploy backend
railway up

# Configure environment variables
echo "🔧 Configuring environment variables..."
railway variables set DATABASE_URL="$DATABASE_URL"
railway variables set SECRET_KEY="$(openssl rand -hex 32)"
railway variables set ENVIRONMENT="production"
railway variables set LOG_LEVEL="INFO"

# Run migrations
echo "🗄️ Running database migrations..."
railway run alembic upgrade head

# Get Railway URL
RAILWAY_URL=$(railway status --json | jq -r '.deployments[0].url' 2>/dev/null || echo "https://your-backend.railway.app")
echo "✅ Backend deployed: $RAILWAY_URL"

cd ../frontend

echo "🌐 Deploying frontend to Vercel..."

# Deploy frontend
vercel --prod

# Configure environment variables
echo "🔧 Configuring Vercel environment variables..."
vercel env add NEXT_PUBLIC_API_URL production --value="$RAILWAY_URL" --force
vercel env add NEXT_PUBLIC_SUPABASE_URL production --value="$SUPABASE_URL" --force
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production --value="$SUPABASE_ANON_KEY" --force

# Redeploy with environment variables
echo "🔄 Redeploying with environment variables..."
vercel --prod

# Get Vercel URL
VERCEL_URL=$(vercel ls 2>/dev/null | grep production | awk '{print $2}' | head -1 || echo "https://your-app.vercel.app")
echo "✅ Frontend deployed: $VERCEL_URL"

# Update CORS origins with actual Vercel URL
echo "🔧 Updating CORS configuration..."
cd ../backend
railway variables set CORS_ORIGINS="$VERCEL_URL"

echo ""
echo "🎉 Deployment Complete!"
echo ""
echo "📊 Your Application URLs:"
echo "   🌐 Frontend: $VERCEL_URL"
echo "   🔧 Backend API: $RAILWAY_URL"
echo "   📚 API Docs: $RAILWAY_URL/docs"
echo "   🏥 Health Check: $RAILWAY_URL/health"
echo "   🗄️ Database: Supabase Dashboard"
echo ""
echo "💰 Monthly Cost Estimate:"
echo "   📱 Vercel: $0 (Free tier - 100GB bandwidth)"
echo "   🚂 Railway: $5-10 (Starter/Developer plan)"
echo "   🗄️ Supabase: $0-25 (Free tier → Pro)"
echo "   💵 Total: $5-35/month"
echo ""
echo "🔧 Management Commands:"
echo "   Railway logs: railway logs"
echo "   Vercel logs: vercel logs"
echo "   Scale Railway: railway variables set RAILWAY_REPLICA_COUNT=2"
echo ""
echo "🔒 Next Steps:"
echo "   1. Test your application: $VERCEL_URL"
echo "   2. Set up custom domain in Vercel dashboard"
echo "   3. Configure monitoring and alerts"
echo "   4. Set up automated backups"
echo ""
echo "🎯 Your modern, cost-effective stack is ready!"