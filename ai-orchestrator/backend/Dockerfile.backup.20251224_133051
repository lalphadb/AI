FROM python:3.12-slim

WORKDIR /app

# Installer les dépendances système incluant Docker CLI et Git
RUN apt-get update && apt-get install -y \
    curl \
    openssh-client \
    procps \
    docker.io \
    git \
    && rm -rf /var/lib/apt/lists/*

# Configurer Git pour accepter tous les répertoires (requis pour volumes montés)
RUN git config --global --add safe.directory '*'

# Copier les requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier l'application et tous les modules v3.0
COPY main.py .
COPY auto_learn.py .
COPY security.py .
COPY auth.py .
COPY rate_limiter.py .
COPY config.py .
COPY prompts.py .

# Créer le dossier data
RUN mkdir -p /data

# Exposer le port
EXPOSE 8001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Démarrer
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
