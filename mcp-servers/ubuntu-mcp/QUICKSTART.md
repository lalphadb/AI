# Guide de Démarrage Rapide

## Installation en 3 étapes

### 1. Installation
```bash
cd /home/lalpha/projets/ubuntu-mcp-server
./install.sh
```

Le script d'installation va:
- Vérifier Node.js (v18+)
- Installer les dépendances npm
- Compiler le code TypeScript
- Créer le dossier de backups
- Proposer de configurer automatiquement Claude Desktop

### 2. Configuration manuelle (si nécessaire)

Si vous n'avez pas utilisé la configuration automatique, éditez:
```bash
nano ~/.config/Claude/claude_desktop_config.json
```

Ajoutez:
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

### 3. Redémarrer Claude Desktop

Fermez complètement Claude Desktop et relancez-le.

## Vérification

Pour vérifier que tout fonctionne:
```bash
cd /home/lalpha/projets/ubuntu-mcp-server
./test.sh
```

## Premiers pas

Une fois configuré, ouvrez Claude Desktop et essayez:

**Exemple 1: Informations système**
```
Donne-moi un aperçu complet de mon système Ubuntu
```

**Exemple 2: Processus actifs**
```
Affiche les 15 processus qui consomment le plus de mémoire
```

**Exemple 3: Vérifier un service**
```
Vérifie si nginx est actif
```

**Exemple 4: Analyse de logs**
```
Analyse les dernières erreurs dans le syslog
```

**Exemple 5: Sécurité**
```
Fais un check de sécurité complet
```

## Résolution de problèmes

### Le serveur n'apparaît pas dans Claude
1. Vérifiez le chemin dans claude_desktop_config.json
2. Assurez-vous que dist/index.js existe (lancez `npm run build`)
3. Redémarrez Claude Desktop complètement
4. Vérifiez les logs: `tail -f ~/claude-desktop-launcher.log`

### Erreurs de permissions
Certaines commandes nécessitent sudo. Pour éviter les prompts:
```bash
sudo visudo
```
Ajoutez:
```
lalpha ALL=(ALL) NOPASSWD: /bin/systemctl, /usr/sbin/ufw
```

### Node.js trop ancien
```bash
# Installer Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

## Commandes utiles

```bash
# Rebuild après modification
npm run build

# Développement avec auto-rebuild
npm run dev

# Vérifier que tout fonctionne
./test.sh

# Voir les logs en temps réel
journalctl -f
```

## Personnalisation

Pour ajouter vos propres outils, éditez `src/index.ts`:

1. Ajoutez votre outil dans le tableau `TOOLS`
2. Créez la fonction handler `handleVotreOutil()`
3. Ajoutez le case dans le switch
4. Rebuild: `npm run build`
5. Redémarrez Claude Desktop

## Support

Pour plus d'informations, consultez le [README.md](README.md) complet.

## Exemples avancés

### Surveillance système
```
Surveille le système et dis-moi s'il y a des problèmes: 
- Charge CPU > 80%
- Mémoire > 90%
- Espace disque > 85%
```

### Gestion Docker
```
Liste tous mes conteneurs Docker et redémarre ceux qui sont en erreur
```

### Backup automatique
```
Crée un backup de mes projets dans /home/lalpha/projets vers /home/lalpha/backups
```

### Analyse de performance
```
Analyse les performances du système et recommande des optimisations
```
