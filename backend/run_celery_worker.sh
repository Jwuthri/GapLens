#!/bin/bash
"""Script to run Celery worker for background task processing."""

# Set environment variables if not already set
export CELERY_BROKER_URL=${CELERY_BROKER_URL:-"redis://localhost:6379/0"}
export CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-"redis://localhost:6379/0"}

# Default values
QUEUES=${CELERY_QUEUES:-"analysis,maintenance"}
CONCURRENCY=${CELERY_CONCURRENCY:-2}
LOG_LEVEL=${CELERY_LOG_LEVEL:-"info"}
WORKER_NAME=${CELERY_WORKER_NAME:-"worker"}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --queues)
            QUEUES="$2"
            shift 2
            ;;
        --concurrency)
            CONCURRENCY="$2"
            shift 2
            ;;
        --loglevel)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --name)
            WORKER_NAME="$2"
            shift 2
            ;;
        --analysis-only)
            QUEUES="analysis"
            shift
            ;;
        --maintenance-only)
            QUEUES="maintenance"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --queues QUEUES        Comma-separated list of queues (default: analysis,maintenance)"
            echo "  --concurrency N        Number of concurrent processes (default: 2)"
            echo "  --loglevel LEVEL       Log level (default: info)"
            echo "  --name NAME            Worker name (default: worker)"
            echo "  --analysis-only        Only process analysis queue"
            echo "  --maintenance-only     Only process maintenance queue"
            echo "  --help                 Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  CELERY_BROKER_URL      Redis broker URL"
            echo "  CELERY_RESULT_BACKEND  Redis result backend URL"
            echo "  CELERY_QUEUES          Default queues to process"
            echo "  CELERY_CONCURRENCY     Default concurrency level"
            echo "  CELERY_LOG_LEVEL       Default log level"
            echo "  CELERY_WORKER_NAME     Default worker name"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Starting Celery worker..."
echo "  Broker: $CELERY_BROKER_URL"
echo "  Result Backend: $CELERY_RESULT_BACKEND"
echo "  Queues: $QUEUES"
echo "  Concurrency: $CONCURRENCY"
echo "  Log Level: $LOG_LEVEL"
echo "  Worker Name: $WORKER_NAME"
echo ""

# Run Celery worker
exec celery -A app.core.celery_app worker \
    --loglevel=$LOG_LEVEL \
    --queues=$QUEUES \
    --concurrency=$CONCURRENCY \
    --hostname=$WORKER_NAME@%h \
    --time-limit=2400 \
    --soft-time-limit=1800