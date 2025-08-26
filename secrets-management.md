# Secrets Management Guide

## Overview
This document outlines the secrets management strategy for the Review Gap Analyzer production deployment.

## Environment Variables

### Required Secrets
- `SECRET_KEY`: Application secret key for JWT tokens and encryption
- `DATABASE_URL`: PostgreSQL connection string with credentials
- `REDIS_PASSWORD`: Redis authentication password
- `GOOGLE_PLAY_API_KEY`: Google Play Store API access
- `APP_STORE_API_KEY`: Apple App Store API access
- `YELP_API_KEY`: Yelp Fusion API access
- `GOOGLE_PLACES_API_KEY`: Google Places API for business lookup

### Optional Secrets
- `SENTRY_DSN`: Error tracking and monitoring
- `NEW_RELIC_LICENSE_KEY`: Application performance monitoring

## Deployment Options

### Docker Compose with .env files
1. Copy `.env.production` templates to `.env.production.local`
2. Fill in actual secret values
3. Use `docker-compose --env-file .env.production.local up`

### Kubernetes Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: review-gap-analyzer-secrets
type: Opaque
stringData:
  SECRET_KEY: "your-secret-key"
  DATABASE_URL: "postgresql://user:pass@host:5432/db"
  REDIS_PASSWORD: "your-redis-password"
  # Add other secrets...
```

### AWS Secrets Manager
```bash
# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name "review-gap-analyzer/prod" \
  --description "Production secrets for Review Gap Analyzer" \
  --secret-string file://secrets.json
```

### HashiCorp Vault
```bash
# Store secrets in Vault
vault kv put secret/review-gap-analyzer/prod \
  SECRET_KEY="your-secret-key" \
  DATABASE_URL="postgresql://user:pass@host:5432/db"
```

## Security Best Practices

1. **Rotation**: Rotate secrets regularly (every 90 days minimum)
2. **Access Control**: Limit access to secrets to necessary personnel only
3. **Encryption**: Ensure secrets are encrypted at rest and in transit
4. **Auditing**: Log all access to secrets for security monitoring
5. **Separation**: Use different secrets for different environments

## Secret Generation

### Generate Strong Passwords
```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate database password
openssl rand -base64 32

# Generate Redis password
openssl rand -base64 24
```

### SSL Certificates
```bash
# Generate self-signed certificate for development
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# For production, use Let's Encrypt or purchase from CA
certbot certonly --standalone -d yourdomain.com
```