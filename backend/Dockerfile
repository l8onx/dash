FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for layer caching
# Build context must be the project root (set in docker-compose.yml)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/app/ ./app/

# Copy legacy frontend assets (replaced by React/Vite in next phase)
COPY public/ ./public/

ENV PORT=3000 \
    DATA_DIR=/data \
    DASH_URL=http://localhost:3000 \
    DASH_PSK=""

EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
