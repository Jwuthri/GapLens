#!/bin/bash

# AWS ECS Deployment Script for Review Gap Analyzer
set -e

echo "🚀 Starting AWS ECS deployment..."

# Check prerequisites
command -v aws >/dev/null 2>&1 || { echo "❌ AWS CLI is required but not installed. Aborting." >&2; exit 1; }
command -v terraform >/dev/null 2>&1 || { echo "❌ Terraform is required but not installed. Aborting." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Aborting." >&2; exit 1; }

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
APP_NAME="review-gap-analyzer"
ENVIRONMENT="production"

echo "📋 Configuration:"
echo "   AWS Region: $AWS_REGION"
echo "   App Name: $APP_NAME"
echo "   Environment: $ENVIRONMENT"

# Check AWS credentials
echo "🔐 Checking AWS credentials..."
aws sts get-caller-identity > /dev/null || {
    echo "❌ AWS credentials not configured. Run 'aws configure' first."
    exit 1
}

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✅ AWS Account ID: $AWS_ACCOUNT_ID"

# Initialize Terraform
echo "🏗️  Initializing Terraform..."
terraform init

# Plan infrastructure
echo "📋 Planning infrastructure changes..."
terraform plan \
    -var="aws_region=$AWS_REGION" \
    -var="app_name=$APP_NAME" \
    -var="environment=$ENVIRONMENT" \
    -out=tfplan

echo ""
echo "💰 Estimated monthly cost: $85-95"
echo "   - ECS Fargate: ~$53"
echo "   - RDS PostgreSQL: ~$14"
echo "   - ElastiCache Redis: ~$12"
echo "   - Load Balancer: ~$16"
echo "   - Other services: ~$10"
echo ""

read -p "🤔 Do you want to proceed with infrastructure creation? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled."
    exit 1
fi

# Apply infrastructure
echo "🏗️  Creating AWS infrastructure..."
terraform apply tfplan

# Get outputs
ECR_BACKEND_URI=$(terraform output -raw ecr_backend_repository_url)
ECR_FRONTEND_URI=$(terraform output -raw ecr_frontend_repository_url)
ALB_DNS=$(terraform output -raw load_balancer_dns)

echo "✅ Infrastructure created successfully!"
echo "   Backend ECR: $ECR_BACKEND_URI"
echo "   Frontend ECR: $ECR_FRONTEND_URI"
echo "   Load Balancer: $ALB_DNS"

# Build and push Docker images
echo "🐳 Building and pushing Docker images..."

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push backend
echo "🔨 Building backend image..."
docker build -f backend/Dockerfile.prod -t $ECR_BACKEND_URI:latest ./backend
docker push $ECR_BACKEND_URI:latest

# Build and push frontend
echo "🔨 Building frontend image..."
docker build -f frontend/Dockerfile.prod -t $ECR_FRONTEND_URI:latest ./frontend
docker push $ECR_FRONTEND_URI:latest

echo "✅ Docker images pushed successfully!"

# Create ECS task definitions
echo "📝 Creating ECS task definitions..."

# Backend task definition
cat > backend-task-definition.json << EOF
{
  "family": "$APP_NAME-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/$APP_NAME-ecs-task-execution-role",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "$ECR_BACKEND_URI:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:$APP_NAME/secrets:SECRET_KEY::"
        },
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:$APP_NAME/secrets:DATABASE_URL::"
        },
        {
          "name": "REDIS_URL",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:$APP_NAME/secrets:REDIS_URL::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$APP_NAME-backend",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8000/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Frontend task definition
cat > frontend-task-definition.json << EOF
{
  "family": "$APP_NAME-frontend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/$APP_NAME-ecs-task-execution-role",
  "containerDefinitions": [
    {
      "name": "frontend",
      "image": "$ECR_FRONTEND_URI:latest",
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "NODE_ENV",
          "value": "production"
        },
        {
          "name": "NEXT_PUBLIC_API_URL",
          "value": "https://$ALB_DNS"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$APP_NAME-frontend",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:3000/api/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
EOF

# Register task definitions
echo "📋 Registering ECS task definitions..."
aws ecs register-task-definition --cli-input-json file://backend-task-definition.json --region $AWS_REGION
aws ecs register-task-definition --cli-input-json file://frontend-task-definition.json --region $AWS_REGION

# Get cluster and target group ARNs
CLUSTER_NAME="$APP_NAME-cluster"
BACKEND_TG_ARN=$(aws elbv2 describe-target-groups --names "$APP_NAME-backend-tg" --query 'TargetGroups[0].TargetGroupArn' --output text --region $AWS_REGION)
FRONTEND_TG_ARN=$(aws elbv2 describe-target-groups --names "$APP_NAME-frontend-tg" --query 'TargetGroups[0].TargetGroupArn' --output text --region $AWS_REGION)

# Get subnet and security group IDs
PRIVATE_SUBNETS=$(aws ec2 describe-subnets --filters "Name=tag:Name,Values=$APP_NAME-private-*" --query 'Subnets[].SubnetId' --output text --region $AWS_REGION | tr '\t' ',')
ECS_SG=$(aws ec2 describe-security-groups --filters "Name=tag:Name,Values=$APP_NAME-ecs-tasks-sg" --query 'SecurityGroups[0].GroupId' --output text --region $AWS_REGION)

# Create ECS services
echo "🚀 Creating ECS services..."

# Backend service
aws ecs create-service \
    --cluster $CLUSTER_NAME \
    --service-name "$APP_NAME-backend-service" \
    --task-definition "$APP_NAME-backend" \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNETS],securityGroups=[$ECS_SG],assignPublicIp=DISABLED}" \
    --load-balancers "targetGroupArn=$BACKEND_TG_ARN,containerName=backend,containerPort=8000" \
    --deployment-configuration "maximumPercent=200,minimumHealthyPercent=50,deploymentCircuitBreaker={enable=true,rollback=true}" \
    --region $AWS_REGION

# Frontend service
aws ecs create-service \
    --cluster $CLUSTER_NAME \
    --service-name "$APP_NAME-frontend-service" \
    --task-definition "$APP_NAME-frontend" \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNETS],securityGroups=[$ECS_SG],assignPublicIp=DISABLED}" \
    --load-balancers "targetGroupArn=$FRONTEND_TG_ARN,containerName=frontend,containerPort=3000" \
    --deployment-configuration "maximumPercent=200,minimumHealthyPercent=50,deploymentCircuitBreaker={enable=true,rollback=true}" \
    --region $AWS_REGION

echo "⏳ Waiting for services to stabilize..."
aws ecs wait services-stable --cluster $CLUSTER_NAME --services "$APP_NAME-backend-service" --region $AWS_REGION
aws ecs wait services-stable --cluster $CLUSTER_NAME --services "$APP_NAME-frontend-service" --region $AWS_REGION

# Run database migrations
echo "🗄️  Running database migrations..."
aws ecs run-task \
    --cluster $CLUSTER_NAME \
    --task-definition "$APP_NAME-backend" \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNETS],securityGroups=[$ECS_SG],assignPublicIp=DISABLED}" \
    --overrides '{
        "containerOverrides": [
            {
                "name": "backend",
                "command": ["alembic", "upgrade", "head"]
            }
        ]
    }' \
    --region $AWS_REGION

echo "⏳ Waiting for migration task to complete..."
sleep 60

# Health checks
echo "🏥 Running health checks..."

# Wait for ALB to be ready
echo "⏳ Waiting for load balancer to be ready..."
sleep 120

# Check backend health
if curl -f "http://$ALB_DNS/health" > /dev/null 2>&1; then
    echo "✅ Backend health check passed"
else
    echo "⚠️  Backend health check failed - may need more time to start"
fi

# Check frontend health
if curl -f "http://$ALB_DNS/" > /dev/null 2>&1; then
    echo "✅ Frontend health check passed"
else
    echo "⚠️  Frontend health check failed - may need more time to start"
fi

# Cleanup temporary files
rm -f backend-task-definition.json frontend-task-definition.json tfplan

echo ""
echo "🎉 AWS ECS deployment completed!"
echo ""
echo "📊 Service URLs:"
echo "   Application: http://$ALB_DNS"
echo "   API: http://$ALB_DNS/api"
echo "   Health Check: http://$ALB_DNS/health"
echo "   API Docs: http://$ALB_DNS/docs"
echo ""
echo "🔧 Management Commands:"
echo "   View services: aws ecs describe-services --cluster $CLUSTER_NAME --region $AWS_REGION"
echo "   View logs: aws logs tail /ecs/$APP_NAME-backend --follow --region $AWS_REGION"
echo "   Scale service: aws ecs update-service --cluster $CLUSTER_NAME --service $APP_NAME-backend-service --desired-count 4 --region $AWS_REGION"
echo ""
echo "💰 Estimated monthly cost: \$85-95"
echo "   Monitor costs: https://console.aws.amazon.com/billing/"
echo ""
echo "🔒 Security:"
echo "   - SSL certificate needs to be configured for HTTPS"
echo "   - Update DNS to point to: $ALB_DNS"
echo "   - Configure domain in Route 53 for production use"
echo ""

# Show running services
echo "🏃 ECS Services Status:"
aws ecs describe-services --cluster $CLUSTER_NAME --services "$APP_NAME-backend-service" "$APP_NAME-frontend-service" --query 'services[].{Name:serviceName,Status:status,Running:runningCount,Desired:desiredCount}' --output table --region $AWS_REGION