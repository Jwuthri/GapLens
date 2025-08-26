# Monitoring and Observability Setup

## Overview
This document outlines the monitoring, logging, and observability setup for the Review Gap Analyzer production deployment.

## Health Check Endpoints

### Basic Health Check
- **Endpoint**: `GET /health`
- **Purpose**: Simple health check for load balancers
- **Response**: `{"status": "healthy", "timestamp": "...", "service": "backend"}`

### Detailed Health Check
- **Endpoint**: `GET /health/detailed`
- **Purpose**: Comprehensive health check including dependencies
- **Checks**: Database, Redis, system resources
- **Response**: Detailed status of all components

### Kubernetes Probes
- **Liveness**: `GET /live` - Checks if the application is running
- **Readiness**: `GET /ready` - Checks if the application is ready to serve traffic

### Metrics
- **Endpoint**: `GET /metrics`
- **Format**: Prometheus-compatible metrics
- **Metrics**: CPU usage, memory usage, disk usage

## Logging Configuration

### Log Levels
- **Production**: INFO level
- **Development**: DEBUG level
- **Error Tracking**: ERROR and CRITICAL levels sent to Sentry

### Log Format
```
%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(funcName)s - %(message)s
```

### Log Rotation
- **Max Size**: 10MB per file
- **Backup Count**: 5 files
- **Location**: `/app/logs/app.log`

## Monitoring Stack Options

### Option 1: Prometheus + Grafana
```yaml
# docker-compose.monitoring.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources

volumes:
  prometheus_data:
  grafana_data:
```

### Option 2: ELK Stack (Elasticsearch, Logstash, Kibana)
```yaml
# docker-compose.elk.yml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

### Option 3: Cloud-based Solutions

#### AWS CloudWatch
```python
# Add to requirements.txt
boto3==1.34.0
watchtower==3.0.1

# In main.py
import watchtower
import boto3

# Configure CloudWatch logging
cloudwatch_handler = watchtower.CloudWatchLogsHandler(
    log_group='review-gap-analyzer',
    stream_name='backend',
    boto3_client=boto3.client('logs', region_name='us-east-1')
)
logger.addHandler(cloudwatch_handler)
```

#### Datadog
```python
# Add to requirements.txt
datadog==0.47.0

# In main.py
from datadog import initialize, statsd

# Initialize Datadog
initialize(
    api_key=os.getenv('DATADOG_API_KEY'),
    app_key=os.getenv('DATADOG_APP_KEY')
)

# Custom metrics
@app.middleware("http")
async def datadog_metrics(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    statsd.histogram('request.duration', duration, tags=[
        f'method:{request.method}',
        f'status:{response.status_code}'
    ])
    
    return response
```

## Alerting Rules

### Critical Alerts
- Application down (health check fails)
- Database connection lost
- Redis connection lost
- High error rate (>5% in 5 minutes)
- High response time (>2s average in 5 minutes)

### Warning Alerts
- High CPU usage (>80% for 10 minutes)
- High memory usage (>85% for 10 minutes)
- High disk usage (>90%)
- Queue backlog growing

### Alert Channels
- Email notifications
- Slack integration
- PagerDuty for critical alerts

## Performance Monitoring

### Key Metrics to Track
- **Request Rate**: Requests per second
- **Response Time**: P50, P95, P99 percentiles
- **Error Rate**: Percentage of failed requests
- **Database Performance**: Query time, connection pool usage
- **Queue Performance**: Job processing time, queue length
- **System Resources**: CPU, memory, disk usage

### Custom Application Metrics
```python
# Add custom metrics to track business logic
from prometheus_client import Counter, Histogram, Gauge

# Request counters
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

# Business metrics
ANALYSIS_COUNT = Counter('analysis_requests_total', 'Total analysis requests', ['type'])
ANALYSIS_DURATION = Histogram('analysis_duration_seconds', 'Analysis processing time')
ACTIVE_ANALYSES = Gauge('active_analyses', 'Number of currently running analyses')
```

## Log Aggregation

### Structured Logging
```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Usage
logger = structlog.get_logger()
logger.info("Analysis started", analysis_id="123", app_id="com.example.app")
```

## Security Monitoring

### Security Events to Monitor
- Failed authentication attempts
- Unusual API usage patterns
- Rate limit violations
- Suspicious user agents
- Large file uploads
- Database query anomalies

### Security Alerts
- Multiple failed login attempts from same IP
- API abuse (high request rate from single source)
- Unusual geographic access patterns
- Potential SQL injection attempts