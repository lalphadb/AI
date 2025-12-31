# 📡 API Reference - AI Orchestrator v5.2

## Base URL

```
Production: https://ai.4lb.ca
Local:      http://localhost:8001
```

---

## Authentification

### Méthodes Supportées

| Méthode | Header | Usage |
|---------|--------|-------|
| JWT Bearer | `Authorization: Bearer <token>` | Sessions utilisateur |
| API Key | `X-API-Key: <key>` | Intégrations |
| Anonymous | - | Accès limité (si activé) |

### Obtenir un Token JWT

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "votre_password"
}
```

**Réponse** :
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

## Endpoints

### Health & Status

#### GET /health

Vérifier la santé de l'API.

```bash
curl https://ai.4lb.ca/health
```

**Réponse** :
```json
{
  "status": "healthy",
  "version": "5.2",
  "ollama": "connected",
  "chromadb": "connected",
  "tools_count": 57
}
```

#### GET /api/stats

Statistiques du système.

```bash
curl https://ai.4lb.ca/api/stats
```

**Réponse** :
```json
{
  "uptime": "2d 5h 32m",
  "conversations": 1247,
  "messages": 8934,
  "tools_count": 57,
  "memory_entries": 523,
  "models_available": 9
}
```

---

### Chat

#### POST /api/chat

Envoyer un message (synchrone).

```bash
curl -X POST https://ai.4lb.ca/api/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quel est le status Docker?",
    "model": "auto",
    "conversation_id": "conv-123"
  }'
```

**Paramètres** :

| Param | Type | Requis | Description |
|-------|------|--------|-------------|
| message | string | ✅ | Message utilisateur |
| model | string | ❌ | Modèle LLM (défaut: auto) |
| conversation_id | string | ❌ | ID conversation existante |
| stream | boolean | ❌ | Streaming SSE (défaut: false) |

**Réponse** :
```json
{
  "response": "Voici le status Docker...",
  "conversation_id": "conv-123",
  "model_used": "qwen2.5-coder:32b",
  "tools_used": ["docker_status"],
  "tokens": {
    "prompt": 245,
    "completion": 312
  }
}
```

#### WebSocket /ws/chat

Chat en temps réel avec streaming.

```javascript
const ws = new WebSocket('wss://ai.4lb.ca/ws/chat?token=<JWT>');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'think':
      console.log('💭 Réflexion:', data.content);
      break;
    case 'plan':
      console.log('📋 Plan:', data.content);
      break;
    case 'action':
      console.log('⚡ Action:', data.tool, data.params);
      break;
    case 'result':
      console.log('📊 Résultat:', data.content);
      break;
    case 'response':
      console.log('✅ Réponse finale:', data.content);
      break;
    case 'error':
      console.error('❌ Erreur:', data.content);
      break;
  }
};

// Envoyer un message
ws.send(JSON.stringify({
  message: "Liste les conteneurs Docker",
  model: "qwen-coder"
}));
```

**Types d'événements** :

| Type | Description |
|------|-------------|
| `think` | Réflexion de l'IA |
| `plan` | Planification des étapes |
| `action` | Exécution d'un outil |
| `result` | Résultat d'un outil |
| `response` | Réponse finale |
| `error` | Erreur |
| `ping` | Keep-alive |

---

### Tools

#### GET /tools

Liste tous les outils disponibles.

```bash
curl https://ai.4lb.ca/tools
```

**Réponse** :
```json
{
  "count": 57,
  "tools": [
    {
      "name": "execute_command",
      "description": "Exécuter une commande shell",
      "parameters": {
        "command": "string (required)"
      },
      "category": "system"
    },
    ...
  ]
}
```

#### GET /tools/{name}

Détails d'un outil spécifique.

```bash
curl https://ai.4lb.ca/tools/docker_status
```

---

### Models

#### GET /api/models

Liste les modèles LLM disponibles.

```bash
curl https://ai.4lb.ca/api/models
```

**Réponse** :
```json
{
  "models": [
    {
      "key": "auto",
      "name": "Sélection automatique",
      "type": "router"
    },
    {
      "key": "qwen-coder",
      "name": "qwen2.5-coder:32b-instruct-q4_K_M",
      "type": "local",
      "size": "19GB"
    },
    {
      "key": "kimi-k2",
      "name": "Kimi K2 1T",
      "type": "cloud",
      "provider": "Moonshot"
    }
  ]
}
```

---

### Conversations

#### GET /api/conversations

Liste les conversations.

```bash
curl https://ai.4lb.ca/api/conversations \
  -H "Authorization: Bearer <token>"
```

**Query params** :
- `limit` : Nombre max (défaut: 20)
- `offset` : Pagination
- `search` : Recherche texte

#### GET /api/conversations/{id}

Détails d'une conversation.

#### DELETE /api/conversations/{id}

Supprimer une conversation.

---

### Memory (ChromaDB)

#### POST /api/memory

Stocker une information en mémoire.

```bash
curl -X POST https://ai.4lb.ca/api/memory \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Le projet JSR utilise React et TailwindCSS",
    "metadata": {
      "project": "jsr",
      "type": "tech_stack"
    }
  }'
```

#### GET /api/memory/search

Recherche sémantique en mémoire.

```bash
curl "https://ai.4lb.ca/api/memory/search?q=projet%20JSR&limit=5"
```

---

### Authentication

#### POST /api/auth/login

Connexion (voir ci-dessus).

#### POST /api/auth/refresh

Rafraîchir le token.

```bash
curl -X POST https://ai.4lb.ca/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

#### GET /api/auth/me

Profil utilisateur courant.

```bash
curl https://ai.4lb.ca/api/auth/me \
  -H "Authorization: Bearer <token>"
```

#### POST /api/auth/logout

Déconnexion (invalide le refresh token).

---

### Upload

#### POST /api/upload

Upload de fichier pour analyse.

```bash
curl -X POST https://ai.4lb.ca/api/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.pdf" \
  -F "conversation_id=conv-123"
```

**Types supportés** :
- Images : jpg, png, gif, webp
- Documents : pdf, txt, md
- Code : py, js, ts, json, yaml

---

## Codes d'Erreur

| Code | Description |
|------|-------------|
| 200 | Succès |
| 201 | Créé |
| 400 | Requête invalide |
| 401 | Non authentifié |
| 403 | Non autorisé |
| 404 | Non trouvé |
| 429 | Rate limit dépassé |
| 500 | Erreur serveur |
| 503 | Service indisponible (Ollama down) |

**Format erreur** :
```json
{
  "detail": "Message d'erreur",
  "code": "ERROR_CODE",
  "timestamp": "2025-12-31T10:30:00Z"
}
```

---

## Rate Limiting

| Endpoint | Limite | Fenêtre |
|----------|--------|---------|
| /api/chat | 30 req | 1 min |
| /ws/chat | 60 msg | 1 min |
| /api/* | 100 req | 1 min |
| /api/auth/login | 5 req | 5 min |

Headers de réponse :
- `X-RateLimit-Limit` : Limite max
- `X-RateLimit-Remaining` : Requêtes restantes
- `X-RateLimit-Reset` : Timestamp reset

---

## Exemples

### Python

```python
import httpx

client = httpx.Client(base_url="https://ai.4lb.ca")

# Login
response = client.post("/api/auth/login", json={
    "username": "admin",
    "password": "password"
})
token = response.json()["access_token"]

# Chat
response = client.post("/api/chat", 
    headers={"Authorization": f"Bearer {token}"},
    json={"message": "Status du serveur?"}
)
print(response.json()["response"])
```

### JavaScript

```javascript
const API_BASE = 'https://ai.4lb.ca';

async function chat(message, token) {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message })
  });
  return response.json();
}
```

---

*API Reference - AI Orchestrator v5.2*
