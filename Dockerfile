FROM python:3.11-slim

# Install system dependencies and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create nonroot user
RUN useradd -m -u 1001 nonroot

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source and migrations
COPY aegis_backend/ aegis_backend/
COPY alembic/ alembic/
COPY alembic.ini .
COPY README.md .

# Setup permissions for nonroot user's directories
RUN mkdir -p /home/nonroot/.aegis_ai && chown -R nonroot:nonroot /home/nonroot /app

USER nonroot

EXPOSE 8000

ENV PORT=8000
ENV AEGIS_TEST_MODE=false

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["sh", "-c", "alembic upgrade head && python -m aegis_backend.main"]
