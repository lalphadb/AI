# UDM-Pro MCP Server

Serveur MCP (Model Context Protocol) pour gérer votre UniFi Dream Machine Pro via SSH.

## 🚀 Fonctionnalités

### Outils Disponibles

1. **udm_connection_test** - Tester la connexion SSH
2. **udm_exec** - Exécuter des commandes sur le UDM-Pro
3. **udm_status** - Obtenir le statut système complet
4. **udm_network_info** - Informations réseau et clients
5. **udm_device_list** - Lister les appareils UniFi
6. **udm_logs** - Consulter les logs système
7. **udm_backup_config** - Sauvegarder la configuration
8. **udm_firewall_rules** - Afficher les règles de firewall

## 📦 Installation

### Prérequis

- Node.js v18+
- Accès SSH à votre UDM-Pro
- Clé SSH configurée

### Étape 1: Configuration de la clé SSH

```bash
# Si vous n'avez pas encore de clé SSH pour le UDM-Pro
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_udm -N ""

# Copier la clé publique sur le UDM-Pro
ssh-copy-id -i ~/.ssh/id_rsa_udm.pub root@10.10.10.1

# OU manuellement: copiez le contenu de la clé publique
cat ~/.ssh/id_rsa_udm.pub
# Puis sur le UDM-Pro, ajoutez-la dans /root/.ssh/authorized_keys
```

### Étape 2: Installation du serveur MCP

```bash
cd /home/lalpha/projets/udm-pro-mcp-server
npm install
npm run build
```

### Étape 3: Configuration Claude Desktop

Ajoutez dans `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "udm-pro": {
      "command": "node",
      "args": ["/home/lalpha/projets/udm-pro-mcp-server/dist/index.js"]
    }
  }
}
```

### Étape 4: Redémarrer Claude Desktop

Fermez complètement et relancez Claude Desktop.

## 🔧 Configuration

### Modifier l'adresse IP du UDM-Pro

Éditez `src/index.ts` et changez l'adresse:

```typescript
const SSH_CONFIG = {
  host: '10.10.10.1',  // Changez ici
  port: 22,
  username: 'root',
  privateKeyPath: path.join(homedir(), '.ssh', 'id_rsa_udm'),
};
```

Puis recompilez: `npm run build`

### Utiliser une clé SSH différente

Changez le chemin dans `SSH_CONFIG.privateKeyPath`.

## 🧪 Test de Connexion

Avant d'utiliser le serveur MCP, testez la connexion SSH:

```bash
# Test manuel
ssh -i ~/.ssh/id_rsa_udm root@10.10.10.1

# Devrait afficher le prompt du UDM-Pro
```

## 💡 Utilisation avec Claude

Une fois configuré, vous pouvez demander à Claude:

### Exemples de commandes

**Test de connexion:**
```
Teste la connexion à mon UDM-Pro
```

**Statut système:**
```
Quel est le statut de mon UDM-Pro?
```

**Exécuter une commande:**
```
Exécute la commande "uptime" sur mon UDM-Pro
```

**Informations réseau:**
```
Montre-moi les interfaces réseau de mon UDM-Pro et les clients connectés
```

**Consulter les logs:**
```
Affiche les 100 dernières lignes des logs du UDM-Pro filtrées sur "error"
```

**Backup:**
```
Crée un backup de la configuration du UDM-Pro
```

**Règles firewall:**
```
Liste toutes les règles de firewall actives sur le UDM-Pro
```

## 🔐 Sécurité

⚠️ **Important:**

- La clé SSH privée doit avoir les permissions 600: `chmod 600 ~/.ssh/id_rsa_udm`
- Ne partagez JAMAIS votre clé privée
- Utilisez une clé SSH dédiée pour ce serveur MCP
- Limitez l'accès SSH sur votre UDM-Pro si possible

## 🐛 Dépannage

### Le serveur ne démarre pas

Vérifiez:
```bash
# 1. Node.js installé
node --version

# 2. Dépendances installées
cd /home/lalpha/projets/udm-pro-mcp-server
npm install

# 3. Code compilé
npm run build
ls -l dist/index.js
```

### Erreur de connexion SSH

Testez manuellement:
```bash
# Vérifier que la clé existe
ls -l ~/.ssh/id_rsa_udm

# Tester la connexion
ssh -vvv -i ~/.ssh/id_rsa_udm root@10.10.10.1
```

### Claude ne voit pas le serveur

1. Vérifiez la configuration: `cat ~/.config/Claude/claude_desktop_config.json`
2. Vérifiez que le chemin vers `index.js` est correct
3. Redémarrez Claude Desktop **complètement**
4. Vérifiez les logs: `tail -f ~/.config/Claude/logs/*.log`

## 📊 Architecture

```
┌─────────────┐
│   Claude    │
│  Desktop    │
└──────┬──────┘
       │ MCP Protocol
       │
┌──────▼──────┐
│  UDM-Pro    │
│ MCP Server  │
└──────┬──────┘
       │ SSH
       │
┌──────▼──────┐
│  UDM-Pro    │
│ 10.10.10.1  │
└─────────────┘
```

## 🔄 Mise à jour

```bash
cd /home/lalpha/projets/udm-pro-mcp-server
git pull  # Si dans un repo git
npm install
npm run build
# Redémarrer Claude Desktop
```

## 📝 Développement

### Mode watch
```bash
npm run dev
```

### Ajouter un nouvel outil

1. Ajoutez la définition dans `TOOLS`
2. Ajoutez le case dans le switch du handler
3. Créez la fonction `handleVotreOutil()`
4. Recompilez: `npm run build`

## 📄 Licence

MIT

## 🤝 Support

Pour tout problème:
1. Vérifiez que la connexion SSH fonctionne manuellement
2. Consultez les logs de Claude Desktop
3. Testez le serveur isolément
4. Vérifiez la configuration

## ⚡ Commandes Utiles

```bash
# Rebuild complet
npm run build

# Tester SSH manuellement
ssh -i ~/.ssh/id_rsa_udm root@10.10.10.1

# Voir les logs Claude Desktop
tail -f ~/.config/Claude/logs/*.log

# Vérifier que le serveur compile
cd /home/lalpha/projets/udm-pro-mcp-server && npm run build

# Test rapide de la connexion
ssh -i ~/.ssh/id_rsa_udm root@10.10.10.1 'hostname && uptime'
```

## 🎯 Modèles de Configuration

### Configuration Complète avec Plusieurs Serveurs

```json
{
  "mcpServers": {
    "udm-pro": {
      "command": "node",
      "args": ["/home/lalpha/projets/udm-pro-mcp-server/dist/index.js"]
    },
    "ubuntu-server": {
      "command": "node",
      "args": ["/home/lalpha/projets/ubuntu-mcp-server/dist/index.js"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/lalpha"]
    }
  }
}
```
