FROM python:3.12-slim

WORKDIR /app

# Installer les dépendances système incluant Docker CLI
RUN apt-get update && apt-get install -y \
    curl \
    openssh-client \
    procps \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier l'application
COPY main.py .

# Créer le dossier data
RUN mkdir -p /data

# Exposer le port
EXPOSE 8001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Démarrer
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
