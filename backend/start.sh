#!/bin/bash

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start Celery worker in the background
echo "Starting Celery worker..."
celery -A tasks.celery_app worker --loglevel=info --pool=solo &

# Start FastAPI server in the foreground
echo "Starting FastAPI server on port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"



