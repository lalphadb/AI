# Documentation API - AI Orchestrator v3.0

## Table des matières

1. [Introduction](#introduction)
2. [Authentification](#authentification)
3. [Endpoints](#endpoints)
4. [WebSocket](#websocket)
5. [Codes d'erreur](#codes-derreur)
6. [Exemples](#exemples)

---

## Introduction

### Base URL

```
Production: https://ai.4lb.ca
Développement: http://localhost:8001
```

### Format des requêtes

- Content-Type: `application/json`
- Encoding: UTF-8

### Format des réponses

Toutes les réponses sont en JSON.

---

## Authentification

### POST /api/auth/login

Obtenir un token d'accès.

**Request:**
```bash
curl -X POST https://ai.4lb.ca/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=yourpassword"
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "refresh_token_here",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Response (401):**
```json
{
  "detail": "Invalid credentials"
}
```

---

### POST /api/auth/refresh

Renouveler un token d'accès.

**Request:**
```bash
curl -X POST https://ai.4lb.ca/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your_refresh_token"}'
```

**Response (200):**
```json
{
  "access_token": "new_access_token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### POST /api/auth/logout

Révoquer un refresh token.

**Request:**
```bash
curl -X POST https://ai.4lb.ca/api/auth/logout \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your_refresh_token"}'
```

---

### API Keys

#### POST /api/auth/apikeys (Admin)

Créer une nouvelle API key.

**Request:**
```bash
curl -X POST https://ai.4lb.ca/api/auth/apikeys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CI/CD Pipeline",
    "scopes": ["read", "execute"],
    "expires_days": 90
  }'
```

**Response (200):**
```json
{
  "key": "ak_abc123...",
  "name": "CI/CD Pipeline",
  "scopes": ["read", "execute"],
  "created_at": "2024-12-14T18:30:00Z",
  "expires_at": "2025-03-14T18:30:00Z"
}
```

---

## Endpoints

### GET /health

Vérifier l'état du service.

**Response (200):**
```json
{
  "status": "healthy",
  "version": "3.0.0",
  "tools_count": 34,
  "models_count": 9,
  "ollama_url": "http://10.10.10.46:11434",
  "auth_enabled": true,
  "rate_limit_enabled": true
}
```

---

### GET /api/models

Liste des modèles disponibles.

**Response (200):**
```json
{
  "models": [
    {
      "id": "auto",
      "name": "AUTO (Sélection automatique)",
      "description": "L'agent choisit le meilleur modèle selon la tâche"
    },
    {
      "id": "qwen-coder",
      "name": "Qwen 2.5 Coder 32B",
      "description": "Code, scripts, debug, analyse technique"
    }
  ],
  "default": "auto"
}
```

---

### GET /tools

Liste des outils disponibles.

**Response (200):**
```json
{
  "tools": [
    {
      "name": "execute_command",
      "description": "Exécuter une commande bash sur le serveur",
      "example": "execute_command(command=\"ls -la\")"
    }
  ],
  "count": 34
}
```

---

### GET /api/stats

Statistiques système en temps réel.

**Response (200):**
```json
{
  "cpu": {
    "percent": 15.2,
    "cores": 24
  },
  "memory": {
    "used_gb": 12.5,
    "total_gb": 64.0,
    "percent": 19.5
  },
  "gpu": {
    "name": "NVIDIA GeForce RTX 5070 Ti",
    "memory_used": 1024,
    "memory_total": 16384,
    "percent": 6
  },
  "docker": {
    "running": 14,
    "total": 14
  }
}
```

---

### POST /api/chat

Envoyer un message et recevoir une réponse.

**Headers:**
```
Authorization: Bearer $TOKEN
Content-Type: application/json
```

**Request:**
```json
{
  "message": "Liste les containers Docker",
  "model": "auto",
  "conversation_id": "optional_id",
  "file_ids": ["optional_file_id"]
}
```

**Response (200):**
```json
{
  "response": "Voici les containers Docker en cours d'exécution:\n- traefik: Up 5 days\n- ai-orchestrator-backend: Up 4 hours\n...",
  "conversation_id": "abc123def456",
  "model_used": "qwen2.5-coder:32b"
}
```

---

### POST /api/upload

Uploader un fichier.

**Request:**
```bash
curl -X POST https://ai.4lb.ca/api/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@screenshot.png" \
  -F "conversation_id=optional_id"
```

**Response (200):**
```json
{
  "success": true,
  "file": {
    "id": "abc123",
    "filename": "screenshot.png",
    "filetype": "image",
    "size": 102400
  }
}
```

---

### GET /api/conversations

Liste des conversations récentes.

**Query params:**
- `limit` (int, default=20): Nombre maximum de conversations

**Response (200):**
```json
{
  "conversations": [
    {
      "id": "abc123",
      "title": "Docker status check",
      "created_at": "2024-12-14T10:00:00",
      "updated_at": "2024-12-14T10:05:00",
      "first_message": "Montre moi les containers Docker"
    }
  ]
}
```

---

### GET /api/conversations/{id}

Détails d'une conversation.

**Response (200):**
```json
{
  "conversation_id": "abc123",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "Bonjour",
      "created_at": "2024-12-14T10:00:00"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "Bonjour! Comment puis-je vous aider?",
      "model_used": "qwen2.5-coder:32b",
      "created_at": "2024-12-14T10:00:05"
    }
  ]
}
```

---

### PUT /api/conversations/{id}

Mettre à jour le titre d'une conversation.

**Request:**
```json
{
  "title": "Nouveau titre"
}
```

**Response (200):**
```json
{
  "success": true
}
```

---

### DELETE /api/conversations/{id}

Supprimer une conversation.

**Response (200):**
```json
{
  "success": true
}
```

---

## WebSocket

### /ws/chat

Connexion WebSocket pour le chat en temps réel.

#### Connexion

```javascript
const ws = new WebSocket('wss://ai.4lb.ca/ws/chat');
// Ou avec token
const ws = new WebSocket('wss://ai.4lb.ca/ws/chat?token=YOUR_TOKEN');
```

#### Messages envoyés (Client → Serveur)

```json
{
  "message": "Votre question ici",
  "model": "auto",
  "conversation_id": "optional",
  "file_ids": []
}
```

#### Messages reçus (Serveur → Client)

**Conversation créée:**
```json
{
  "type": "conversation_created",
  "conversation_id": "abc123"
}
```

**Modèle sélectionné:**
```json
{
  "type": "model_selected",
  "model": "qwen2.5-coder:32b",
  "reason": "analyse automatique"
}
```

**Réflexion en cours:**
```json
{
  "type": "thinking",
  "iteration": 1,
  "message": "Itération 1/12..."
}
```

**Étape de raisonnement:**
```json
{
  "type": "step",
  "iteration": 1,
  "content": "THINK: Je vais d'abord vérifier...\nACTION: docker_status()"
}
```

**Outil exécuté:**
```json
{
  "type": "tool",
  "tool": "docker_status",
  "params": {}
}
```

**Résultat d'outil:**
```json
{
  "type": "result",
  "tool": "docker_status",
  "result": "Conteneurs Docker:\ntraefik  Up 5 days..."
}
```

**Auto-apprentissage:**
```json
{
  "type": "activity",
  "action": "Auto-apprentissage: 2 fait(s) mémorisé(s)",
  "details": "[user_fact] développeur, [project] ai-orchestrator"
}
```

**Réponse finale:**
```json
{
  "type": "complete",
  "answer": "Voici les containers Docker...",
  "iterations": 3,
  "model": "qwen2.5-coder:32b"
}
```

**Erreur:**
```json
{
  "type": "error",
  "message": "Description de l'erreur"
}
```

---

## Codes d'erreur

| Code | Description |
|------|-------------|
| 200 | Succès |
| 400 | Requête invalide |
| 401 | Non authentifié |
| 403 | Non autorisé (scope manquant) |
| 404 | Ressource non trouvée |
| 429 | Trop de requêtes (rate limit) |
| 500 | Erreur serveur |

### Format des erreurs

```json
{
  "detail": "Description de l'erreur"
}
```

### Rate Limit (429)

```json
{
  "detail": "Too many requests",
  "retry_after": 30
}
```

Headers:
```
Retry-After: 30
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1734200000
```

---

## Exemples

### Python

```python
import httpx

BASE_URL = "https://ai.4lb.ca"

# Authentification
async def login(username: str, password: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/auth/login",
            data={"username": username, "password": password}
        )
        return response.json()["access_token"]

# Chat
async def chat(token: str, message: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": message, "model": "auto"}
        )
        return response.json()["response"]

# Exemple d'utilisation
import asyncio

async def main():
    token = await login("admin", "password")
    response = await chat(token, "Quel est l'uptime du serveur?")
    print(response)

asyncio.run(main())
```

### JavaScript

```javascript
const BASE_URL = 'https://ai.4lb.ca';

// Authentification
async function login(username, password) {
    const response = await fetch(`${BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `username=${username}&password=${password}`
    });
    const data = await response.json();
    return data.access_token;
}

// WebSocket Chat
function connectChat(token, onMessage) {
    const ws = new WebSocket(`wss://ai.4lb.ca/ws/chat?token=${token}`);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        onMessage(data);
    };

    ws.sendMessage = (message, model = 'auto') => {
        ws.send(JSON.stringify({ message, model }));
    };

    return ws;
}

// Exemple
async function main() {
    const token = await login('admin', 'password');
    const ws = connectChat(token, (data) => {
        if (data.type === 'complete') {
            console.log('Réponse:', data.answer);
        }
    });

    ws.onopen = () => {
        ws.sendMessage('Liste les containers Docker');
    };
}

main();
```

### cURL

```bash
# Variables
BASE_URL="https://ai.4lb.ca"

# Login
TOKEN=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -d "username=admin&password=password" | jq -r '.access_token')

# Chat
curl -X POST "$BASE_URL/api/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "uptime", "model": "auto"}' | jq '.response'

# Upload
curl -X POST "$BASE_URL/api/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@image.png"

# Avec API Key
curl "$BASE_URL/api/stats" \
  -H "X-API-Key: ak_your_api_key_here"
```
