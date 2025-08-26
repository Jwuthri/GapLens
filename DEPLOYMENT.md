# Production Deployment Guide

## Overview
This guide covers the production deployment of the Review Gap Analyzer application using Docker Compose with proper security, monitoring, and scalability configurations.

## Prerequisites

### System Requirements
- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 20GB+ disk space
- SSL certificates (Let's Encrypt recommended)

### Required Services
- PostgreSQL 15+
- Redis 7+
- Nginx (reverse proxy)

## Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd review-gap-analyzer
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.production.template .env.production

# Edit with your actual values
nano .env.production
```

### 3. Deploy
```bash
# Make deployment script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

## Manual Deployment Steps

### 1. Environment Configuration
Create `.env.production` with the following required variables:

```bash
# Generate secure secret key
SECRET_KEY=$(openssl rand -hex 32)

# Database credentials
POSTGRES_DB=review_gap_analyzer_prod
POSTGRES_USER=app_user
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Redis password
REDIS_PASSWORD=$(openssl rand -base64 24)

# Application URLs
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 2. SSL Certificates

#### Option A: Let's Encrypt (Recommended)
```bash
# Install certbot
sudo apt-get install certbot

# Generate certificates
sudo certbot certonly --standalone -d yourdomain.com -d api.yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
```

#### Option B: Self-signed (Development)
```bash
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes
```

### 3. Database Setup
```bash
# Start database services
docker-compose -f docker-compose.full-prod.yml up -d postgres redis

# Wait for services to be ready
sleep 30

# Run migrations
docker-compose -f docker-compose.full-prod.yml exec backend alembic upgrade head
```

### 4. Application Deployment
```bash
# Build and start all services
docker-compose -f docker-compose.full-prod.yml up -d

# Verify deployment
curl -f http://localhost:8000/health
curl -f http://localhost:3000/api/health
```

## Service Architecture

### Core Services
- **Backend**: FastAPI application server
- **Frontend**: Next.js web application
- **Celery Worker**: Background job processing
- **Celery Beat**: Scheduled task execution
- **PostgreSQL**: Primary database
- **Redis**: Cache and message broker
- **Nginx**: Reverse proxy and load balancer

### Optional Services
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards

## Configuration Files

### Docker Compose Files
- `docker-compose.full-prod.yml`: Complete production stack
- `backend/docker-compose.prod.yml`: Backend services only
- `frontend/docker-compose.prod.yml`: Frontend service only

### Application Configuration
- `backend/Dockerfile.prod`: Production backend container
- `frontend/Dockerfile.prod`: Production frontend container
- `backend/nginx.prod.conf`: Nginx reverse proxy configuration
- `backend/redis.prod.conf`: Redis production configuration

## Health Checks and Monitoring

### Health Check Endpoints
- **Backend**: `GET /health` (basic), `GET /health/detailed` (comprehensive)
- **Frontend**: `GET /api/health`
- **Metrics**: `GET /metrics` (Prometheus format)

### Kubernetes Probes
- **Liveness**: `GET /live`
- **Readiness**: `GET /ready`

### Monitoring Setup
```bash
# Start with monitoring stack
docker-compose -f docker-compose.full-prod.yml --profile monitoring up -d

# Access monitoring
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin/admin)
```

## Security Configuration

### Network Security
- All services run in isolated Docker network
- Nginx handles SSL termination
- Rate limiting configured for API endpoints
- CORS properly configured for frontend domains

### Application Security
- Non-root user in containers
- Security headers configured
- Input validation and sanitization
- Environment variable isolation

### Database Security
- Dedicated application user with limited privileges
- Connection pooling and timeout configuration
- Regular backup strategy recommended

## Performance Optimization

### Application Tuning
- **Uvicorn Workers**: 4 workers (adjust based on CPU cores)
- **Celery Concurrency**: 4 concurrent tasks
- **Database Connections**: Connection pooling enabled
- **Redis**: Configured for optimal memory usage

### Resource Limits
```yaml
# Add to docker-compose.yml services
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '0.5'
    reservations:
      memory: 512M
      cpus: '0.25'
```

## Backup and Recovery

### Database Backup
```bash
# Create backup
docker-compose -f docker-compose.full-prod.yml exec postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql

# Restore backup
docker-compose -f docker-compose.full-prod.yml exec -T postgres psql -U $POSTGRES_USER $POSTGRES_DB < backup.sql
```

### Redis Backup
```bash
# Redis automatically creates snapshots based on configuration
# Manual backup
docker-compose -f docker-compose.full-prod.yml exec redis redis-cli BGSAVE
```

## Scaling

### Horizontal Scaling
```bash
# Scale backend workers
docker-compose -f docker-compose.full-prod.yml up -d --scale backend=3

# Scale Celery workers
docker-compose -f docker-compose.full-prod.yml up -d --scale celery-worker=5
```

### Load Balancing
Nginx is configured to load balance between multiple backend instances automatically.

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
docker-compose -f docker-compose.full-prod.yml logs [service-name]

# Check service status
docker-compose -f docker-compose.full-prod.yml ps
```

#### Database Connection Issues
```bash
# Test database connectivity
docker-compose -f docker-compose.full-prod.yml exec postgres pg_isready -U $POSTGRES_USER

# Check database logs
docker-compose -f docker-compose.full-prod.yml logs postgres
```

#### High Memory Usage
```bash
# Check resource usage
docker stats

# Restart services if needed
docker-compose -f docker-compose.full-prod.yml restart [service-name]
```

### Log Locations
- **Application Logs**: `./logs/app.log`
- **Nginx Logs**: `./logs/nginx/`
- **Container Logs**: `docker-compose logs [service]`

## Maintenance

### Regular Tasks
- Monitor disk usage and clean up old logs
- Update Docker images regularly
- Rotate SSL certificates before expiration
- Review and update security configurations
- Monitor application performance metrics

### Updates
```bash
# Pull latest images
docker-compose -f docker-compose.full-prod.yml pull

# Rebuild and restart
docker-compose -f docker-compose.full-prod.yml up -d --build

# Run any new migrations
docker-compose -f docker-compose.full-prod.yml exec backend alembic upgrade head
```

## Support

### Monitoring Alerts
Configure alerts for:
- Service downtime
- High error rates
- Resource exhaustion
- Database connectivity issues
- Queue backlog growth

### Log Analysis
Use structured logging and log aggregation tools like ELK stack or cloud-based solutions for better observability.

### Performance Monitoring
Track key metrics:
- Request response times
- Database query performance
- Queue processing times
- System resource usage