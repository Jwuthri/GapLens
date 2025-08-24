#!/bin/bash
"""Script to run Celery Beat scheduler for periodic tasks."""

# Set environment variables if not already set
export CELERY_BROKER_URL=${CELERY_BROKER_URL:-"redis://localhost:6379/0"}
export CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-"redis://localhost:6379/0"}

# Default values
LOG_LEVEL=${CELERY_LOG_LEVEL:-"info"}
SCHEDULE_FILE=${CELERY_SCHEDULE_FILE:-"celerybeat-schedule"}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --loglevel)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --schedule)
            SCHEDULE_FILE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --loglevel LEVEL       Log level (default: info)"
            echo "  --schedule FILE        Schedule database file (default: celerybeat-schedule)"
            echo "  --help                 Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  CELERY_BROKER_URL      Redis broker URL"
            echo "  CELERY_RESULT_BACKEND  Redis result backend URL"
            echo "  CELERY_LOG_LEVEL       Default log level"
            echo "  CELERY_SCHEDULE_FILE   Default schedule file"
            echo ""
            echo "Periodic tasks configured:"
            echo "  - cleanup-old-results: Runs every hour"
            echo "  - cleanup-failed-analyses: Runs daily"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Starting Celery Beat scheduler..."
echo "  Broker: $CELERY_BROKER_URL"
echo "  Result Backend: $CELERY_RESULT_BACKEND"
echo "  Log Level: $LOG_LEVEL"
echo "  Schedule File: $SCHEDULE_FILE"
echo ""

# Run Celery Beat
exec celery -A app.core.celery_app beat \
    --loglevel=$LOG_LEVEL \
    --schedule=$SCHEDULE_FILE \
    --pidfile=celerybeat.pid