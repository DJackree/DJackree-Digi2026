# Python 3.12 slim image: small footprint, enough tooling for pip installs.
FROM python:3.12-slim

WORKDIR /app

# Stream logs immediately; skip .pyc files in the image layer.
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# pg_isready lives in postgresql-client — entrypoint.sh waits for Postgres before migrate.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App source (same folder as Dockerfile): templates, manage.py, entrypoint.sh, etc.
COPY . .

EXPOSE 8000

# Default process: shell script runs migrations, seed, then runserver.
CMD ["sh", "./entrypoint.sh"]
