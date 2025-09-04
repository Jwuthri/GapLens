import os
import time
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import psutil
import redis
from sqlalchemy import text

from app.api import router as api_router
from app.database.connection import get_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Review Gap Analyzer API",
    description="API for analyzing app store reviews to identify user pain points",
    version="1.0.0"
)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.4f}s")
    
    return response

# Include API routes
app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Review Gap Analyzer API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "backend"
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including dependencies"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "backend",
        "version": "1.0.0",
        "checks": {}
    }
    
    # Check database connection
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Check Redis connection
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        r.ping()
        health_status["checks"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # System metrics
    try:
        health_status["checks"]["system"] = {
            "status": "healthy",
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    except Exception as e:
        health_status["checks"]["system"] = {"status": "unhealthy", "error": str(e)}
    
    # Return appropriate status code
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)

@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint"""
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        metrics_text = f"""# HELP cpu_usage_percent CPU usage percentage
# TYPE cpu_usage_percent gauge
cpu_usage_percent {cpu_percent}

# HELP memory_usage_percent Memory usage percentage
# TYPE memory_usage_percent gauge
memory_usage_percent {memory.percent}

# HELP memory_usage_bytes Memory usage in bytes
# TYPE memory_usage_bytes gauge
memory_usage_bytes {memory.used}

# HELP disk_usage_percent Disk usage percentage
# TYPE disk_usage_percent gauge
disk_usage_percent {disk.percent / disk.total * 100}

# HELP disk_usage_bytes Disk usage in bytes
# TYPE disk_usage_bytes gauge
disk_usage_bytes {disk.used}
"""
        
        return JSONResponse(
            content=metrics_text,
            media_type="text/plain"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to collect metrics: {str(e)}")

@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint"""
    try:
        # Check if application is ready to serve requests
        db = next(get_db())
        db.execute(text("SELECT 1"))
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        r.ping()
        
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")

@app.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}