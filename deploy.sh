#!/bin/bash

# Production deployment script for Review Gap Analyzer
set -e

echo "🚀 Starting production deployment..."

# Check if required environment files exist
if [ ! -f ".env.production" ]; then
    echo "❌ Error: .env.production file not found"
    echo "Please copy .env.production.template and fill in the values"
    exit 1
fi

# Load environment variables
source .env.production

# Validate required environment variables
required_vars=(
    "SECRET_KEY"
    "DATABASE_URL"
    "REDIS_PASSWORD"
    "POSTGRES_DB"
    "POSTGRES_USER"
    "POSTGRES_PASSWORD"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: Required environment variable $var is not set"
        exit 1
    fi
done

echo "✅ Environment variables validated"

# Create necessary directories
mkdir -p logs/nginx
mkdir -p ssl
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/grafana/datasources

echo "✅ Directories created"

# Generate SSL certificates if they don't exist
if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
    echo "🔐 Generating SSL certificates..."
    openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    echo "✅ SSL certificates generated"
fi

# Build and start services
echo "🏗️  Building and starting services..."

# Pull latest images
docker-compose -f docker-compose.full-prod.yml pull

# Build custom images
docker-compose -f docker-compose.full-prod.yml build --no-cache

# Start core services first
echo "🗄️  Starting database services..."
docker-compose -f docker-compose.full-prod.yml up -d postgres redis

# Wait for databases to be ready
echo "⏳ Waiting for databases to be ready..."
sleep 30

# Run database migrations
echo "🔄 Running database migrations..."
docker-compose -f docker-compose.full-prod.yml exec -T backend alembic upgrade head

# Start application services
echo "🚀 Starting application services..."
docker-compose -f docker-compose.full-prod.yml up -d backend celery-worker celery-beat frontend nginx

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Health checks
echo "🏥 Running health checks..."

# Check backend health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend health check passed"
else
    echo "❌ Backend health check failed"
    docker-compose -f docker-compose.full-prod.yml logs backend
    exit 1
fi

# Check frontend health
if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "✅ Frontend health check passed"
else
    echo "❌ Frontend health check failed"
    docker-compose -f docker-compose.full-prod.yml logs frontend
    exit 1
fi

# Check database connectivity
if docker-compose -f docker-compose.full-prod.yml exec -T postgres pg_isready -U $POSTGRES_USER -d $POSTGRES_DB > /dev/null 2>&1; then
    echo "✅ Database connectivity check passed"
else
    echo "❌ Database connectivity check failed"
    exit 1
fi

# Check Redis connectivity
if docker-compose -f docker-compose.full-prod.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis connectivity check passed"
else
    echo "❌ Redis connectivity check failed"
    exit 1
fi

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📊 Service URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Documentation: http://localhost:8000/docs"
echo "   Health Check: http://localhost:8000/health"
echo ""
echo "🔧 Management Commands:"
echo "   View logs: docker-compose -f docker-compose.full-prod.yml logs -f [service]"
echo "   Stop services: docker-compose -f docker-compose.full-prod.yml down"
echo "   Restart service: docker-compose -f docker-compose.full-prod.yml restart [service]"
echo ""
echo "📈 Optional Monitoring:"
echo "   Start monitoring: docker-compose -f docker-compose.full-prod.yml --profile monitoring up -d"
echo "   Prometheus: http://localhost:9090"
echo "   Grafana: http://localhost:3001 (admin/admin)"
echo ""

# Show running services
echo "🏃 Running services:"
docker-compose -f docker-compose.full-prod.yml ps