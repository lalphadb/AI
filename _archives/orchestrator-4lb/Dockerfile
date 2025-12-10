# Orchestrateur 4LB - Dockerfile
FROM python:3.11-slim

LABEL maintainer="4lb.ca"
LABEL description="Orchestrateur IA Self-Improving pour infrastructure"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ORCHESTRATOR_HOST=0.0.0.0
ENV ORCHESTRATOR_PORT=8888

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Créer l'utilisateur non-root
RUN useradd -m -u 1000 orchestrator

# Répertoire de travail
WORKDIR /app

# Copier les requirements et installer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY --chown=orchestrator:orchestrator . .

# Créer les répertoires nécessaires
RUN mkdir -p logs backups && chown -R orchestrator:orchestrator logs backups

# Passer à l'utilisateur non-root
USER orchestrator

# Exposer le port
EXPOSE 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8888/health || exit 1

# Démarrer l'API
CMD ["python", "api.py"]
