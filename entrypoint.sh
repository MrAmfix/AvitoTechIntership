#!/bin/sh

echo "Waiting for postgres..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

echo "Running database migrations..."
alembic upgrade head

echo "Starting API server..."
uvicorn app:app --host 0.0.0.0 --port ${API_PORT}