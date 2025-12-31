# 🔒 Guide de Sécurité - AI Orchestrator v5.2

## Vue d'Ensemble

Ce document décrit les mesures de sécurité implémentées dans AI Orchestrator et les bonnes pratiques pour maintenir un environnement sécurisé.

---

## Architecture de Sécurité

### Defense in Depth

```
┌─────────────────────────────────────────────────────────────────┐
│                      COUCHE 1: RÉSEAU                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ UFW Firewall│  │  GeoBlock   │  │   CrowdSec IPS          │  │
│  │ Ports 80,443│  │ CA,US,FR... │  │   Community Blocklists  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                      COUCHE 2: TRANSPORT                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              TLS 1.3 (Let's Encrypt)                        ││
│  │              HSTS, Security Headers                          ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│                      COUCHE 3: APPLICATION                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ JWT Auth    │  │ Rate Limit  │  │   CORS Policy           │  │
│  │ 1h Expiry   │  │ 100/min/IP  │  │   Origins whitelist     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                      COUCHE 4: EXÉCUTION                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Blacklist   │  │ Path Valid  │  │   Symlink Protection    │  │
│  │ 30+ cmds    │  │ Traversal   │  │   Sandbox limits        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                      COUCHE 5: AUDIT                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Logging complet • Traçabilité actions          ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Authentification

### JWT (JSON Web Tokens)

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| Algorithme | HS256 | HMAC SHA-256 |
| Expiration | 1 heure | Access token |
| Refresh | 7 jours | Refresh token |
| Secret | Env var | JWT_SECRET_KEY |

**Configuration** :
```python
# backend/auth.py
ACCESS_TOKEN_EXPIRE_MINUTES = 60
ALGORITHM = "HS256"
```

### API Keys

Pour les intégrations programmatiques :
- Préfixe : `aio_`
- Longueur : 32 caractères
- Hachage : SHA-256 en base
- Scopes configurables

### Bonnes Pratiques

1. **Rotation des secrets** : Changer `JWT_SECRET_KEY` régulièrement
2. **Mots de passe forts** : 12+ caractères, mixte
3. **HTTPS obligatoire** : Jamais de tokens en HTTP
4. **Logout** : Invalider les refresh tokens

---

## Validation des Commandes

### Blacklist (Mode Autonome)

L'agent utilise une approche **blacklist** : tout est permis sauf les commandes explicitement interdites.

**Commandes Interdites** :
```python
FORBIDDEN_COMMANDS = {
    # Destructeurs système
    "mkfs", "fdisk", "dd", "shred",
    
    # Réseau dangereux
    "wget", "curl", "nc", "netcat", "ncat",
    
    # Gestion utilisateurs
    "useradd", "userdel", "usermod", "passwd", "chpasswd",
    
    # Cron/Tâches
    "crontab", "at", "batch",
    
    # Firewall/Réseau
    "iptables", "ip6tables", "nft", "ufw",
    
    # Montage/Disques
    "mount", "umount", "losetup",
    
    # Système
    "shutdown", "reboot", "poweroff", "init", "telinit",
    
    # SSH
    "ssh-keygen", "ssh-add",
    
    # Conteneurs (dangereux)
    "docker run", "docker exec",
}
```

### Patterns Dangereux

```python
FORBIDDEN_PATTERNS = [
    r"rm\s+-rf\s+/",           # rm -rf /
    r">\s*/dev/[hs]d",         # Écriture disque raw
    r"mkfs\.",                  # Format disque
    r":\(\)\{:\|:&\};:",       # Fork bomb
    r"/dev/tcp/",              # Reverse shell
    r"bash\s+-i",              # Interactive shell
    r"nc\s+-[el]",             # Netcat listen
    r"eval\s+.*base64",        # Obfuscation
]
```

### Validation des Chemins

```python
def validate_path(path: str) -> Tuple[bool, str]:
    """
    Valide un chemin contre:
    - Traversée de répertoire (../)
    - Symlinks malicieux
    - Chemins absolus non autorisés
    """
    ALLOWED_ROOTS = [
        "/home/lalpha/projets",
        "/tmp",
        "/var/log"
    ]
```

---

## Rate Limiting

### Configuration

| Endpoint | Limite | Fenêtre | Action |
|----------|--------|---------|--------|
| `/api/chat` | 30 | 1 min | 429 |
| `/ws/chat` | 60 msg | 1 min | Disconnect |
| `/api/*` | 100 | 1 min | 429 |
| `/api/auth/login` | 5 | 5 min | 429 + delay |

### Implémentation

```python
# backend/rate_limiter.py
class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.blocked_ips = set()
    
    async def check(self, ip: str, endpoint: str) -> bool:
        # Sliding window algorithm
        ...
```

### Headers de Réponse

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704020400
```

---

## Audit et Logging

### Événements Loggés

| Catégorie | Événements |
|-----------|------------|
| Auth | Login, logout, token refresh, échecs |
| Tools | Exécution, paramètres, résultats |
| Security | Commandes bloquées, rate limit, IP suspectes |
| System | Démarrage, erreurs, health checks |

### Format des Logs

```json
{
  "timestamp": "2025-12-31T10:30:00Z",
  "level": "WARNING",
  "category": "security",
  "event": "command_blocked",
  "details": {
    "command": "rm -rf /",
    "reason": "forbidden_pattern",
    "user": "admin",
    "ip": "10.10.10.5"
  }
}
```

### Emplacement

```
/data/audit.log      # Actions utilisateur
/data/security.log   # Événements sécurité
docker logs          # Logs application
```

---

## Configuration Sécurisée

### Variables d'Environnement

```bash
# .env (JAMAIS commiter)
JWT_SECRET_KEY=<openssl rand -base64 32>
ADMIN_PASSWORD=<mot de passe fort>

# Optionnel
DEBUG=false
AUTH_ENABLED=true
ALLOW_ANONYMOUS=false
ALLOWED_ORIGINS=https://ai.4lb.ca
```

### Checklist Déploiement

- [ ] Secrets générés aléatoirement
- [ ] DEBUG=false en production
- [ ] AUTH_ENABLED=true
- [ ] HTTPS configuré (Traefik)
- [ ] CrowdSec actif avec bouncer
- [ ] Firewall UFW activé
- [ ] Ports non essentiels fermés
- [ ] Logs rotatés

---

## Traefik & Middlewares

### Security Headers

```yaml
# middlewares.yml
security-headers:
  headers:
    frameDeny: true
    browserXssFilter: true
    contentTypeNosniff: true
    stsSeconds: 31536000
    stsIncludeSubdomains: true
    stsPreload: true
    contentSecurityPolicy: "default-src 'self'"
```

### GeoBlock

```yaml
geoblock:
  plugin:
    geoblock:
      allowedCountries:
        - CA  # Canada
        - US  # États-Unis
        - FR  # France
        - BE  # Belgique
        - CH  # Suisse
        - GB  # Royaume-Uni
```

### CrowdSec

```yaml
crowdsec:
  plugin:
    bouncer:
      crowdsecLapiKey: "${CROWDSEC_BOUNCER_KEY}"
      crowdsecLapiHost: "crowdsec:8080"
```

---

## Vulnérabilités Connues

### Statut Actuel

| ID | Vulnérabilité | Sévérité | Statut |
|----|---------------|----------|--------|
| P0-1 | Docker socket mount | CRITIQUE | ⚠️ À corriger |
| P0-2 | Volume /home RW | CRITIQUE | ⚠️ À corriger |
| P1-1 | Ports exposés 0.0.0.0 | HAUTE | ⚠️ À corriger |
| P2-1 | CrowdSec bouncer absent | MOYENNE | ⚠️ À configurer |

### Plan de Remédiation

1. **Docker Socket** : Migrer vers docker-socket-proxy
2. **Volume** : Restreindre à `/home/lalpha/projets:ro`
3. **Ports** : Bind sur 127.0.0.1
4. **CrowdSec** : `cscli bouncers add traefik-bouncer`

---

## Réponse aux Incidents

### Procédure

1. **Détection** : Alerte CrowdSec/logs
2. **Isolation** : Bloquer IP/token
3. **Analyse** : Examiner audit.log
4. **Correction** : Patcher vulnérabilité
5. **Documentation** : Post-mortem

### Contacts

- **Logs** : `/data/security.log`
- **Blocage IP** : `cscli decisions add -i <IP>`
- **Révocation token** : Redémarrer avec nouveau JWT_SECRET_KEY

---

## Checklist Sécurité

### Quotidien

- [ ] Vérifier les logs de sécurité
- [ ] Contrôler les alertes CrowdSec

### Hebdomadaire

- [ ] Revue des accès utilisateurs
- [ ] Mise à jour des dépendances (`pip-audit`, `npm audit`)

### Mensuel

- [ ] Rotation des secrets
- [ ] Audit de configuration
- [ ] Test de pénétration basique

---

*Guide de Sécurité - AI Orchestrator v5.2*
