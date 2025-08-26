# Vercel Frontend Deployment Guide

## Overview
Deploy the Next.js frontend to Vercel for free with automatic deployments, CDN, and serverless functions.

## Prerequisites
- Vercel account (free)
- GitHub repository
- Domain (optional)

## Quick Setup

### 1. Install Vercel CLI
```bash
npm i -g vercel
vercel login
```

### 2. Configure Frontend for Vercel
Already configured in `next.config.js` with:
- Standalone output for optimal performance
- Environment variable support
- Security headers

### 3. Environment Variables
Create `.env.local` in frontend directory:
```bash
# Frontend Environment Variables
NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
NEXT_PUBLIC_GA_ID=your-google-analytics-id
NEXT_PUBLIC_ENABLE_ANALYTICS=true
```

### 4. Deploy to Vercel

#### Option A: GitHub Integration (Recommended)
1. Push your code to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Click "New Project"
4. Import your GitHub repository
5. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`

#### Option B: CLI Deployment
```bash
cd frontend
vercel

# Follow prompts:
# ? Set up and deploy "frontend"? Y
# ? Which scope? Your username
# ? Link to existing project? N
# ? What's your project's name? review-gap-analyzer
# ? In which directory is your code located? ./
```

### 5. Configure Environment Variables in Vercel
```bash
# Add environment variables via CLI
vercel env add NEXT_PUBLIC_API_URL production
# Enter: https://your-backend-url.railway.app

# Or via Vercel Dashboard:
# Project Settings > Environment Variables
```

### 6. Custom Domain (Optional)
```bash
# Add custom domain
vercel domains add yourdomain.com
vercel domains add www.yourdomain.com

# Configure DNS:
# A record: @ -> 76.76.19.61
# CNAME: www -> cname.vercel-dns.com
```

## Vercel Configuration File

Create `vercel.json` in frontend root:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "functions": {
    "app/api/**/*.ts": {
      "maxDuration": 30
    }
  },
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "Referrer-Policy",
          "value": "origin-when-cross-origin"
        }
      ]
    }
  ],
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-backend-url.railway.app/:path*"
    }
  ]
}
```

## Automatic Deployments

### GitHub Integration
- **Production**: Deploys from `main` branch
- **Preview**: Deploys from feature branches
- **Instant**: Deploys on every push

### Environment-specific Deployments
```bash
# Production deployment
git push origin main

# Preview deployment
git push origin feature-branch
```

## Performance Optimizations

### Image Optimization
```jsx
// Already configured in next.config.js
import Image from 'next/image'

<Image
  src="/hero-image.jpg"
  alt="Description"
  width={800}
  height={600}
  priority
/>
```

### Static Generation
```jsx
// For static pages
export async function getStaticProps() {
  return {
    props: {},
    revalidate: 3600 // Revalidate every hour
  }
}
```

## Monitoring & Analytics

### Vercel Analytics
```bash
# Install Vercel Analytics
npm install @vercel/analytics

# Add to _app.tsx
import { Analytics } from '@vercel/analytics/react'

export default function App({ Component, pageProps }) {
  return (
    <>
      <Component {...pageProps} />
      <Analytics />
    </>
  )
}
```

### Web Vitals
```jsx
// pages/_app.tsx
export function reportWebVitals(metric) {
  console.log(metric)
  // Send to analytics service
}
```

## Cost & Limits

### Free Tier (Hobby)
- **Bandwidth**: 100GB/month
- **Builds**: 6,000 minutes/month
- **Serverless Functions**: 100GB-hours/month
- **Custom Domains**: Unlimited
- **Team Members**: 1

### Pro Tier ($20/month)
- **Bandwidth**: 1TB/month
- **Builds**: 24,000 minutes/month
- **Serverless Functions**: 1,000GB-hours/month
- **Team Members**: Unlimited
- **Advanced Analytics**

## Troubleshooting

### Build Errors
```bash
# Check build logs
vercel logs

# Local build test
npm run build
npm start
```

### Environment Variables
```bash
# List environment variables
vercel env ls

# Pull environment variables locally
vercel env pull .env.local
```

### CORS Issues
```javascript
// next.config.js - already configured
async headers() {
  return [
    {
      source: '/api/:path*',
      headers: [
        { key: 'Access-Control-Allow-Origin', value: '*' },
        { key: 'Access-Control-Allow-Methods', value: 'GET,POST,PUT,DELETE,OPTIONS' },
        { key: 'Access-Control-Allow-Headers', value: 'Content-Type, Authorization' },
      ],
    },
  ]
}
```

## Security Best Practices

### Environment Variables
- Never commit `.env.local` to git
- Use `NEXT_PUBLIC_` prefix only for client-side variables
- Store sensitive data in Vercel environment variables

### Content Security Policy
```javascript
// next.config.js
async headers() {
  return [
    {
      source: '/(.*)',
      headers: [
        {
          key: 'Content-Security-Policy',
          value: "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
        }
      ]
    }
  ]
}
```

## Deployment Commands

```bash
# Deploy to production
vercel --prod

# Deploy preview
vercel

# Deploy with specific environment
vercel --env NEXT_PUBLIC_API_URL=https://staging-api.com

# Promote preview to production
vercel promote https://preview-url.vercel.app
```

## Integration with Backend

### API Proxy Configuration
```javascript
// next.config.js - already configured
async rewrites() {
  const apiUrl = process.env.NODE_ENV === 'production' 
    ? process.env.NEXT_PUBLIC_API_URL || 'https://your-backend.railway.app'
    : 'http://localhost:8000';
    
  return [
    {
      source: '/api/:path*',
      destination: `${apiUrl}/:path*`,
    },
  ]
}
```

### Environment-specific API URLs
```bash
# Production
NEXT_PUBLIC_API_URL=https://your-backend.railway.app

# Staging
NEXT_PUBLIC_API_URL=https://staging-backend.railway.app

# Development
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Benefits of Vercel

✅ **Free for most use cases**
✅ **Automatic HTTPS & CDN**
✅ **Zero-config deployments**
✅ **Instant rollbacks**
✅ **Preview deployments**
✅ **Built-in analytics**
✅ **Edge functions**
✅ **Excellent Next.js integration**

Your frontend will be blazing fast and cost $0 for most traffic levels!