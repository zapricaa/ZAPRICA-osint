# ZAPRICA Backend Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for build and networking
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e .

# Install Playwright browser binaries for web reconnaissance
RUN playwright install --with-deps chromium

# Copy application source
COPY . .

# Security: Non-root user execution
RUN useradd -u 10001 -m zaprica && \
    chown -R zaprica:zaprica /app

USER zaprica

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    ZAPRICA_SAFE_MODE=true \
    TERMINAL_EXECUTION_ENABLED=false \
    AUTO_INVESTIGATION_ENABLED=false

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
