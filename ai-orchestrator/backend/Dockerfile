FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (combining all apt operations in single layer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    openssh-client \
    procps \
    docker.io \
    git \
    tree \
    iputils-ping \
    dnsutils \
    net-tools \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user with specific UID/GID for better security
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Configure Git to accept all directories (required for mounted volumes)
RUN git config --global --add safe.directory '*'

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python application files in optimized layers
# Core application files
COPY main.py auth.py security.py config.py engine.py rate_limiter.py prompts.py auto_learn.py dynamic_context.py ./

# Application modules (tools, utils, services)
COPY tools/ ./tools/
COPY utils/ ./utils/
COPY services/ ./services/

# Create data directory with proper ownership
RUN mkdir -p /data && chown -R appuser:appgroup /data

# Set ownership of application files
RUN chown -R appuser:appgroup /app

# Expose port
EXPOSE 8001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Switch to non-root user
USER appuser

# Start application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
