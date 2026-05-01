#!/bin/sh
set -e

echo "Waiting for PostgreSQL (${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432})..."
until pg_isready -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -q; do
  sleep 1
done

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Seeding if empty..."
python manage.py seed_data --if-empty

echo "Starting development server..."
exec python manage.py runserver 0.0.0.0:8000
