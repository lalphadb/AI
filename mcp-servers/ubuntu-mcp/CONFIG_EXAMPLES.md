# Exemples de Configuration Claude Desktop

## Configuration de base

**Emplacement**: `~/.config/Claude/claude_desktop_config.json`

### Serveur MCP Ubuntu uniquement
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

## Configurations avancées

### Avec plusieurs serveurs MCP
```json
{
  "mcpServers": {
    "ubuntu-server": {
      "command": "node",
      "args": ["/home/lalpha/projets/ubuntu-mcp-server/dist/index.js"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/lalpha"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "votre_token_github"
      }
    }
  }
}
```

### Avec variables d'environnement
```json
{
  "mcpServers": {
    "ubuntu-server": {
      "command": "node",
      "args": ["/home/lalpha/projets/ubuntu-mcp-server/dist/index.js"],
      "env": {
        "LOG_LEVEL": "debug",
        "BACKUP_DIR": "/home/lalpha/backups",
        "MAX_TIMEOUT": "60000"
      }
    }
  }
}
```

### Avec logging personnalisé
```json
{
  "mcpServers": {
    "ubuntu-server": {
      "command": "node",
      "args": ["/home/lalpha/projets/ubuntu-mcp-server/dist/index.js"],
      "env": {
        "NODE_ENV": "production",
        "DEBUG": "mcp:*"
      }
    }
  },
  "globalShortcut": "CommandOrControl+Shift+.",
  "logging": {
    "level": "info"
  }
}
```

## Configuration par environnement

### Développement
```json
{
  "mcpServers": {
    "ubuntu-server-dev": {
      "command": "node",
      "args": [
        "--inspect",
        "/home/lalpha/projets/ubuntu-mcp-server/dist/index.js"
      ],
      "env": {
        "NODE_ENV": "development",
        "DEBUG": "*"
      }
    }
  }
}
```

### Production
```json
{
  "mcpServers": {
    "ubuntu-server": {
      "command": "node",
      "args": ["/home/lalpha/projets/ubuntu-mcp-server/dist/index.js"],
      "env": {
        "NODE_ENV": "production"
      }
    }
  }
}
```

## Dépannage de la configuration

### Vérifier que la config est valide
```bash
# Vérifier la syntaxe JSON
cat ~/.config/Claude/claude_desktop_config.json | jq .
```

### Vérifier les chemins
```bash
# S'assurer que le fichier existe
ls -l /home/lalpha/projets/ubuntu-mcp-server/dist/index.js
```

### Voir les logs de Claude Desktop
```bash
# Logs en temps réel
tail -f ~/claude-desktop-launcher.log

# Rechercher des erreurs
grep -i error ~/claude-desktop-launcher.log
```

## Bonnes pratiques

1. **Toujours valider le JSON** avant de redémarrer Claude
2. **Faire une sauvegarde** avant de modifier la config
3. **Utiliser des chemins absolus** pour éviter les problèmes
4. **Tester après chaque modification**

## Sauvegarde de configuration
```bash
# Créer une sauvegarde
cp ~/.config/Claude/claude_desktop_config.json ~/.config/Claude/claude_desktop_config.json.backup

# Restaurer depuis une sauvegarde
cp ~/.config/Claude/claude_desktop_config.json.backup ~/.config/Claude/claude_desktop_config.json
```

## Configuration recommandée complète
```json
{
  "mcpServers": {
    "ubuntu-server": {
      "command": "node",
      "args": ["/home/lalpha/projets/ubuntu-mcp-server/dist/index.js"],
      "env": {
        "NODE_ENV": "production",
        "BACKUP_DIR": "/home/lalpha/backups"
      }
    }
  }
}
```
