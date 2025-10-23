FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    SECRET_KEY=change-me-in-unraid \
    SESSION_COOKIE_NAME=fmp_session \
    SESSION_COOKIE_SECURE=true \
    SESSION_COOKIE_SAMESITE=lax \
    DATABASE_URL=sqlite:////data/mealplanner.db

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Persistent DB directory
RUN mkdir -p /data && chown -R root:root /data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
