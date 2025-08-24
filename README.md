# Review Gap Analyzer

A web application for analyzing app store reviews to identify user pain points and feature gaps.

## Project Structure

```
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # API routes
│   │   ├── core/     # Core configuration
│   │   ├── database/ # Database models and connection
│   │   ├── models/   # Pydantic models
│   │   └── services/ # Business logic
│   └── requirements.txt
├── frontend/         # Next.js frontend
│   ├── src/
│   │   └── app/      # App router pages
│   └── package.json
└── docker-compose.yml
```

## Development Setup

1. Clone the repository
2. Copy environment variables:
   ```bash
   cp backend/.env.example backend/.env
   ```
3. Start the development environment:
   ```bash
   docker-compose up -d
   ```

## Services

- **Frontend**: http://localhost:3000 (Next.js)
- **Backend API**: http://localhost:8000 (FastAPI)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation.