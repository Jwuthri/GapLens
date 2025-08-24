# Backend Development Setup

## Quick Start

### Option 1: Using Docker (Recommended)

**Standard Docker (try this first):**
```bash
# From project root
docker-compose up -d --build
```

**If you get hdbscan compilation errors, use the conda version:**
```bash
# From project root  
docker-compose -f docker-compose.conda.yml up -d --build
```

The API will be available at http://localhost:8000

**Note:** The conda version uses conda-forge packages which have better pre-built binaries for ARM64/Apple Silicon.

### Option 2: Local Development

#### Prerequisites
- Python 3.8+
- PostgreSQL running locally
- Redis running locally

#### Setup Steps

1. **Create virtual environment:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On macOS/Linux
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your database credentials
```

4. **Run database migrations:**
```bash
alembic upgrade head
```

5. **Start the FastAPI server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

## API Documentation

- Interactive docs: http://localhost:8000/docs
- OpenAPI spec: http://localhost:8000/openapi.json

## Background Tasks

The application uses Celery for background tasks. To run the worker:

```bash
# In a separate terminal
./run_celery_worker.sh
```

## Testing

```bash
pytest
```