#!/bin/bash

# Start Celery worker in the background
echo "Starting Celery worker..."
celery -A tasks.celery_app worker --loglevel=info --pool=solo &

# Start FastAPI server in the foreground
echo "Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
