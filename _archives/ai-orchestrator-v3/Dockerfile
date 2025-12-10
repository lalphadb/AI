FROM python:3.11-slim

WORKDIR /app

# Dépendances système
RUN apt-get update && apt-get install -y \
    curl \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier l'application
COPY main.py .
COPY frontend/ frontend/

# Créer les dossiers
RUN mkdir -p /data/uploads

# Port
EXPOSE 8000

# Démarrer
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
