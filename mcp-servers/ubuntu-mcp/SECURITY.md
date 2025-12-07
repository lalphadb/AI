# 🔐 Sécurité et Bonnes Pratiques

## ⚠️ Avertissements de Sécurité

### Risques Importants

Le serveur MCP Ubuntu a un accès direct à votre système. **Utilisez-le avec précaution!**

⚠️ **ATTENTION**: 
- L'outil `execute_command` peut exécuter **n'importe quelle commande**
- Certaines opérations nécessitent des privilèges sudo
- Les commandes destructives peuvent supprimer des données
- Les modifications système peuvent affecter la stabilité

## 🛡️ Recommandations de Sécurité

### 1. Principe du Moindre Privilège

**Configuration sudo limitée** (Recommandé)
```bash
sudo visudo
```

Ajoutez uniquement les commandes nécessaires:
```
lalpha ALL=(ALL) NOPASSWD: /bin/systemctl start *, /bin/systemctl stop *, /bin/systemctl restart *
lalpha ALL=(ALL) NOPASSWD: /usr/sbin/ufw status
```

**❌ À ÉVITER**:
```
lalpha ALL=(ALL) NOPASSWD: ALL  # TROP PERMISSIF!
```

### 2. Commandes Dangereuses à Éviter

**Ne JAMAIS exécuter via execute_command**:
```bash
# ❌ DANGER: Suppression récursive
rm -rf /
rm -rf /*

# ❌ DANGER: Écrasement du disque
dd if=/dev/zero of=/dev/sda

# ❌ DANGER: Fork bomb
:(){ :|:& };:

# ❌ DANGER: Modification des permissions root
chmod -R 777 /

# ❌ DANGER: Suppression des fichiers système
rm -rf /boot
rm -rf /etc
```

### 3. Validation des Entrées

**Toujours vérifier** avant d'exécuter:
- Chemins de fichiers
- Noms de services
- Commandes shell
- Paramètres utilisateur

### 4. Limitation des Permissions de Fichiers

```bash
# Le serveur MCP ne devrait pas avoir accès à tout
# Créez un utilisateur dédié si possible
sudo useradd -m -s /bin/bash mcp-user
sudo usermod -aG docker mcp-user  # Si nécessaire

# Limitez l'accès aux fichiers sensibles
chmod 600 ~/.ssh/id_rsa
chmod 600 ~/.config/Claude/claude_desktop_config.json
```

## 🔒 Bonnes Pratiques

### Configuration Sécurisée

**1. Environnement de production**
```json
{
  "mcpServers": {
    "ubuntu-server": {
      "command": "node",
      "args": ["/home/lalpha/projets/ubuntu-mcp-server/dist/index.js"],
      "env": {
        "NODE_ENV": "production",
        "MAX_TIMEOUT": "30000"
      }
    }
  }
}
```

**2. Logging activé**
```bash
# Conservez un historique des commandes exécutées
export HISTTIMEFORMAT="%F %T "
export HISTSIZE=10000
export HISTFILESIZE=10000
```

**3. Backups réguliers**
```bash
# Avant toute opération critique
sudo cp -r /etc /home/lalpha/backups/etc-$(date +%Y%m%d)
```

### Utilisation Prudente

**✅ Bonnes pratiques**:
- Toujours vérifier les commandes avant exécution
- Faire des backups avant modifications critiques
- Tester sur un environnement de dev d'abord
- Lire les logs après chaque opération
- Comprendre ce que fait chaque commande

**❌ Mauvaises pratiques**:
- Exécuter des commandes sans les comprendre
- Donner des permissions sudo illimitées
- Ignorer les erreurs et warnings
- Ne pas faire de backups
- Exécuter en root par défaut

## 🚨 Gestion des Incidents

### En cas de problème

**1. Arrêt d'urgence**
```bash
# Arrêter le serveur MCP
pkill -f "ubuntu-mcp-server"

# Désactiver dans Claude Desktop
mv ~/.config/Claude/claude_desktop_config.json ~/.config/Claude/claude_desktop_config.json.disabled
```

**2. Vérification de sécurité**
```bash
# Vérifier les dernières commandes exécutées
history | tail -50

# Vérifier les connexions actives
ss -tuln

# Vérifier les processus suspects
ps aux | grep -v grep

# Vérifier les logs système
journalctl -n 100 -p err
```

**3. Restauration**
```bash
# Si backup disponible
sudo rsync -av /home/lalpha/backups/latest/ /

# Restaurer config Claude Desktop
mv ~/.config/Claude/claude_desktop_config.json.backup ~/.config/Claude/claude_desktop_config.json
```

## 📋 Checklist de Sécurité

Avant de déployer en production:

- [ ] Configuration sudo limitée et documentée
- [ ] Backups automatiques configurés
- [ ] Logging activé et surveillé
- [ ] Permissions de fichiers vérifiées
- [ ] Tests de sécurité effectués
- [ ] Plan de réponse aux incidents défini
- [ ] Documentation à jour
- [ ] Formation des utilisateurs
- [ ] Monitoring en place
- [ ] Procédure de rollback testée

## 🔍 Audit et Monitoring

### Surveillance continue

**1. Logs d'accès**
```bash
# Surveiller les accès au serveur
tail -f ~/claude-desktop-launcher.log

# Surveiller les commandes système
journalctl -f
```

**2. Alertes automatiques**
```bash
# Exemple de script d'alerte
#!/bin/bash
if [ $(systemctl is-failed ubuntu-mcp-server 2>/dev/null) == "failed" ]; then
    echo "MCP Server failed!" | mail -s "ALERT: MCP Server" admin@example.com
fi
```

**3. Audit régulier**
```bash
# Script d'audit hebdomadaire
# À exécuter via cron
#!/bin/bash
echo "=== Audit de sécurité MCP ===" > /tmp/mcp-audit.log
echo "Date: $(date)" >> /tmp/mcp-audit.log
echo "" >> /tmp/mcp-audit.log

# Vérifier les permissions
echo "Permissions critiques:" >> /tmp/mcp-audit.log
ls -l /home/lalpha/projets/ubuntu-mcp-server/dist/index.js >> /tmp/mcp-audit.log

# Vérifier les dernières commandes sudo
echo "" >> /tmp/mcp-audit.log
echo "Dernières commandes sudo:" >> /tmp/mcp-audit.log
grep sudo /var/log/auth.log | tail -20 >> /tmp/mcp-audit.log

# Envoyer le rapport
cat /tmp/mcp-audit.log | mail -s "MCP Security Audit" admin@example.com
```

## 🎯 Recommandations par Cas d'Usage

### Environnement de Développement
- ✅ Permissions plus larges acceptables
- ✅ Tests et expérimentations encouragés
- ⚠️ Toujours sur des données non critiques

### Environnement de Staging
- ⚠️ Permissions limitées
- ✅ Tests de sécurité obligatoires
- ✅ Backups avant chaque test

### Environnement de Production
- 🔒 Permissions minimales strictes
- 🔒 Audit logging obligatoire
- 🔒 Validation humaine pour opérations critiques
- 🔒 Backups automatiques et testés
- 🔒 Plan de rollback défini

## 📚 Ressources Complémentaires

### Durcissement Ubuntu
- [Ubuntu Security Guide](https://ubuntu.com/security)
- [CIS Ubuntu Benchmarks](https://www.cisecurity.org/)
- [NIST Security Guidelines](https://www.nist.gov/)

### Sécurité Node.js
- [Node.js Security Best Practices](https://nodejs.org/en/docs/guides/security/)
- [OWASP Node.js Security Cheat Sheet](https://cheatsheetseries.owasp.org/)

### MCP Security
- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [Anthropic Security Guidelines](https://docs.anthropic.com/)

## 🆘 Support Sécurité

En cas de problème de sécurité:

1. **Isolez le système** si compromis
2. **Collectez les logs** pour analyse
3. **Documentez l'incident**
4. **Restaurez depuis backup propre**
5. **Analysez la cause racine**
6. **Implémentez les correctifs**
7. **Testez la sécurité**
8. **Mettez à jour la documentation**

---

**Rappel**: La sécurité est un processus continu, pas un état. Restez vigilant et informé!
