# Argus API — production image
#
# Build: docker build -t argus-api .
# Run:   docker run -p 8000:8000 -v $(pwd)/data:/app/data -v $(pwd)/config:/app/config argus-api
#
# For local development, use docker-compose.yml instead.

FROM python:3.11-slim

WORKDIR /app

# System dependencies (shapely/scipy need libgeos; curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Copy dependency manifests first (layer cache)
COPY pyproject.toml uv.lock ./

# Install production dependencies (no dev extras)
RUN uv pip install --system -e "."

# Copy application source
COPY argus/ ./argus/
COPY config/ ./config/

# Create data directories
RUN mkdir -p /app/data/artifacts

# Non-root user for security
RUN useradd -m -u 1000 argus && chown -R argus:argus /app
USER argus

EXPOSE 8000

CMD ["argus", "serve", "--host", "0.0.0.0", "--port", "8000", "--db-path", "/app/data/argus.db"]
