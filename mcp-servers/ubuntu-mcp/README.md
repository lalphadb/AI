# Ubuntu MCP Server

Serveur MCP (Model Context Protocol) intelligent pour gérer et analyser votre serveur Ubuntu.

## 🚀 Fonctionnalités

### Informations Système
- **system_info**: Récupère des informations détaillées sur le système (CPU, mémoire, disque, OS, réseau)
- **list_processes**: Liste les processus en cours avec tri par CPU/mémoire/nom
- **disk_usage**: Analyse l'utilisation du disque par répertoire
- **network_info**: Informations réseau complètes (interfaces, connexions, ports)

### Gestion des Services
- **service_status**: Vérifie le statut d'un service systemd
- **service_control**: Contrôle les services (start, stop, restart, enable, disable)

### Exécution de Commandes
- **execute_command**: Exécute n'importe quelle commande shell avec timeout configurable

### Analyse et Monitoring
- **log_analyzer**: Analyse les logs système avec filtrage
- **docker_status**: Gère et surveille les conteneurs Docker
- **file_search**: Recherche de fichiers avancée

### Sécurité
- **security_check**: Vérifications de sécurité (updates, ports, users, firewall)

### Backups
- **backup_manager**: Gestion complète des sauvegardes (créer, lister, info)

## 📦 Installation

```bash
cd /home/lalpha/projets/ubuntu-mcp-server
npm install
npm run build
```

## ⚙️ Configuration dans Claude Desktop

Ajoutez cette configuration dans votre fichier `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ubuntu-server": {
      "command": "node",
      "args": ["/home/lalpha/projets/ubuntu-mcp-server/dist/index.js"]
    }
  }
}
```

Sur Linux, le fichier se trouve généralement à:
```
~/.config/Claude/claude_desktop_config.json
```

## 🔧 Utilisation

Une fois configuré dans Claude Desktop, vous pouvez utiliser les outils directement:

### Exemples de commandes

**Vérifier les informations système:**
```
Utilise system_info pour me donner un aperçu complet du système
```

**Lister les processus gourmands:**
```
Affiche-moi les 10 processus qui consomment le plus de CPU
```

**Vérifier un service:**
```
Vérifie le statut du service nginx
```

**Analyser les logs:**
```
Analyse les 200 dernières lignes du syslog et filtre les erreurs
```

**Gestion Docker:**
```
Montre-moi tous les conteneurs Docker, même ceux arrêtés
```

**Recherche de fichiers:**
```
Trouve tous les fichiers .log dans /var/log
```

**Vérification de sécurité:**
```
Fais un check de sécurité complet du système
```

**Créer un backup:**
```
Crée un backup du dossier /home/lalpha/projets vers /home/lalpha/backups
```

## 🔐 Permissions

Certaines commandes nécessitent des privilèges sudo (gestion de services, firewall, etc.). Assurez-vous que:

1. L'utilisateur a les permissions sudo nécessaires
2. Pour les opérations automatisées, configurez sudoers pour éviter les prompts de mot de passe:

```bash
sudo visudo
```

Ajoutez:
```
lalpha ALL=(ALL) NOPASSWD: /bin/systemctl
```

## 📝 Outils Disponibles

| Outil | Description | Arguments |
|-------|-------------|-----------|
| system_info | Info système | category: all\|cpu\|memory\|disk\|os\|network |
| list_processes | Liste processus | sortBy: cpu\|memory\|name, limit: number |
| execute_command | Exécute commande | command: string, timeout: number |
| service_status | Statut service | service: string |
| service_control | Contrôle service | service: string, action: start\|stop\|restart\|enable\|disable |
| disk_usage | Usage disque | path: string, depth: number |
| network_info | Info réseau | detailed: boolean |
| log_analyzer | Analyse logs | logFile: string, lines: number, filter: string |
| docker_status | Statut Docker | all: boolean |
| file_search | Recherche fichiers | directory: string, pattern: string, maxDepth: number |
| security_check | Check sécurité | checkType: updates\|ports\|users\|firewall\|all |
| backup_manager | Gestion backups | action: create\|list\|info, source: string, destination: string |

## 🛠️ Développement

### Structure du projet
```
ubuntu-mcp-server/
├── src/
│   └── index.ts          # Code source principal
├── dist/                 # Code compilé
├── package.json
├── tsconfig.json
└── README.md
```

### Développement en mode watch
```bash
npm run dev
```

### Build
```bash
npm run build
```

## 🐛 Dépannage

### Le serveur ne démarre pas
- Vérifiez que Node.js v18+ est installé
- Vérifiez que les dépendances sont installées: `npm install`
- Vérifiez que le build est à jour: `npm run build`

### Permissions refusées
- Certaines commandes nécessitent sudo
- Configurez sudoers pour les opérations automatisées

### Claude Desktop ne voit pas le serveur
- Vérifiez le chemin dans claude_desktop_config.json
- Redémarrez Claude Desktop
- Vérifiez les logs: `tail -f ~/claude-desktop-launcher.log`

## 📄 Licence

MIT

## 🤝 Contribution

Ce serveur est un point de départ. N'hésitez pas à ajouter vos propres outils selon vos besoins!

### Ajouter un nouvel outil

1. Ajoutez la définition dans `TOOLS`
2. Ajoutez le case dans le switch du handler
3. Créez la fonction de traitement `handleVotreOutil()`
4. Rebuild: `npm run build`

## 🔥 Astuces

- Utilisez `execute_command` pour des opérations personnalisées
- Combinez plusieurs outils pour des analyses complexes
- Créez des scripts shell et exécutez-les via `execute_command`
- Utilisez `log_analyzer` avec des filtres grep pour trouver rapidement des problèmes
- Configurez des backups réguliers avec `backup_manager`

## ⚠️ Avertissements

- Soyez prudent avec `execute_command` - il exécute n'importe quelle commande
- Les opérations sudo peuvent modifier votre système
- Testez les commandes critiques manuellement avant automatisation
- Les backups ne sont pas chiffrés par défaut
