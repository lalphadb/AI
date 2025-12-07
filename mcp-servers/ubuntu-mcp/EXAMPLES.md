# Exemples d'Utilisation du Serveur MCP Ubuntu

## 📊 Surveillance et Monitoring

### Check de santé complet
```
Fais un check de santé complet de mon serveur Ubuntu:
- Charge CPU et processus les plus gourmands
- Utilisation mémoire
- Espace disque par partition
- Services critiques (nginx, mysql, docker)
- Mises à jour disponibles
```

### Surveillance des ressources
```
Surveille mon système et alerte-moi si:
- CPU > 80%
- RAM > 90%
- Disque > 85% sur n'importe quelle partition
```

### Top processus
```
Montre-moi les 10 processus qui consomment le plus de:
1. CPU
2. Mémoire
Identifie les anomalies possibles
```

## 🔧 Gestion des Services

### Vérification de services web
```
Vérifie l'état de mes services web:
- nginx
- apache2
- mysql
- postgresql
- redis

Dis-moi lesquels sont actifs et lesquels sont en erreur
```

### Redémarrage intelligent
```
Vérifie le service nginx. S'il y a des erreurs, redémarre-le et vérifie à nouveau
```

### Analyse de configuration
```
Récupère la configuration du service nginx et identifie les potentiels problèmes
```

## 🗂️ Gestion des Fichiers et Disques

### Analyse d'espace disque
```
Analyse l'utilisation du disque dans /home et dis-moi:
- Les 5 plus gros répertoires
- Fichiers > 100MB
- Recommandations de nettoyage
```

### Recherche de fichiers volumineux
```
Trouve tous les fichiers de plus de 500MB sur le système et liste-les par taille
```

### Nettoyage de logs
```
Analyse l'espace pris par /var/log et identifie les logs qui peuvent être archivés ou supprimés
```

## 🔍 Analyse de Logs

### Recherche d'erreurs
```
Analyse les 500 dernières lignes du syslog et montre-moi:
- Toutes les erreurs
- Tous les warnings critiques
- Les patterns suspects
```

### Surveillance d'application
```
Analyse les logs nginx des dernières 24h et montre-moi:
- Les erreurs 500
- Les requêtes les plus lentes
- Les IPs suspectes
```

### Debug d'un service
```
Le service mysql ne démarre pas. Analyse les logs pour identifier le problème
```

## 🐳 Gestion Docker

### Vue d'ensemble Docker
```
Donne-moi un rapport complet sur Docker:
- Conteneurs en cours (avec CPU/RAM)
- Conteneurs arrêtés
- Images orphelines
- Volumes inutilisés
- Recommandations de nettoyage
```

### Redémarrage de conteneurs
```
Liste tous mes conteneurs Docker. Ceux qui sont "unhealthy" ou en "restarting", redémarre-les
```

### Analyse de performances Docker
```
Analyse la performance de mes conteneurs Docker et identifie ceux qui consomment trop de ressources
```

## 🔐 Sécurité

### Audit de sécurité complet
```
Fais un audit de sécurité complet:
- Mises à jour de sécurité disponibles
- Ports ouverts non standards
- Utilisateurs avec accès sudo
- État du firewall
- Connexions suspectes récentes
- Fichiers avec permissions 777
```

### Surveillance des connexions
```
Montre-moi toutes les connexions réseau actives et identifie les suspectes
```

### Vérification de ports
```
Liste tous les ports ouverts et pour chaque port dis-moi quel service l'utilise
```

## 💾 Backups

### Backup quotidien
```
Crée un backup de:
- /home/lalpha/projets
- /etc (configs système)
- /var/www (si applicable)

Destination: /home/lalpha/backups
Nom avec timestamp
```

### Vérification de backups
```
Liste tous les backups dans /home/lalpha/backups
Vérifie l'intégrité du dernier backup
Montre-moi son contenu
```

### Rotation de backups
```
Dans /home/lalpha/backups:
- Liste tous les backups par date
- Garde les 7 derniers
- Supprime les plus anciens
```

## 📈 Performance et Optimisation

### Analyse de performance
```
Analyse les performances de mon serveur et recommande:
- Services à désactiver
- Processus à optimiser
- Paramètres kernel à ajuster
- Optimisations mémoire
```

### Détection de bottlenecks
```
Identifie les bottlenecks actuels:
- I/O disque
- CPU
- Mémoire
- Réseau
```

### Optimisation automatique
```
Analyse mon système et applique les optimisations safe suivantes:
- Nettoyage de cache
- Suppression de paquets orphelins
- Optimisation de swap
```

## 🌐 Réseau

### Diagnostic réseau
```
Fais un diagnostic réseau complet:
- Interfaces et leur configuration
- Connexions actives
- Latence vers des serveurs clés
- Bande passante utilisée
```

### Test de connectivité
```
Teste la connectivité vers:
- google.com
- github.com
- Mon serveur de base de données
```

## 🔄 Automatisation

### Script de maintenance
```
Crée un script qui:
1. Vérifie l'état du système
2. Update les paquets
3. Nettoie les logs anciens
4. Redémarre les services en erreur
5. Crée un backup
6. Envoie un rapport

Exécute-le et montre-moi le résultat
```

### Monitoring continu
```
Surveille mon système pendant 5 minutes et rapporte:
- Pics de CPU
- Utilisation mémoire moyenne
- Nouveaux processus
- Erreurs dans les logs
```

## 🆘 Dépannage

### Serveur lent
```
Mon serveur est lent. Aide-moi à diagnostiquer:
1. Charge CPU et processus gourmands
2. Utilisation mémoire et swap
3. I/O disque
4. Connexions réseau
5. Logs d'erreurs récents
```

### Espace disque plein
```
Mon disque est plein. Aide-moi à:
1. Identifier ce qui prend de la place
2. Trouver les gros fichiers
3. Nettoyer en toute sécurité
4. Libérer de l'espace
```

### Service qui crash
```
Mon service nginx crash régulièrement. Aide-moi à:
1. Analyser les logs
2. Vérifier les ressources
3. Identifier la cause
4. Proposer une solution
```

## 💡 Cas d'Usage Avancés

### Déploiement d'application
```
Je vais déployer une nouvelle app Node.js. Aide-moi à:
1. Vérifier les prérequis (Node, npm, PM2)
2. Préparer l'environnement
3. Configurer nginx comme reverse proxy
4. Mettre en place un monitoring
```

### Migration de serveur
```
Prépare mon serveur pour une migration:
1. Liste tous les services installés
2. Backup de toutes les configs
3. Backup des bases de données
4. Liste des cron jobs
5. Documentation de l'architecture
```

### Création d'environnement de dev
```
Configure un environnement de développement complet:
1. Installe Docker et Docker Compose
2. Configure git
3. Installe Node.js, Python, PHP
4. Configure nginx
5. Crée des alias utiles
```

## 📋 Templates de Commandes

### Check quotidien
```
Rapport quotidien:
- État général du système
- Services critiques
- Backups récents
- Mises à jour disponibles
- Erreurs notables
```

### Pré-déploiement
```
Checklist pré-déploiement:
- Espace disque suffisant
- Services fonctionnels
- Backup récent disponible
- Firewall configuré
- Logs propres
```

### Post-incident
```
Rapport post-incident:
- Chronologie des événements
- Services affectés
- Actions prises
- État actuel
- Recommandations
```

---

**Astuce**: Ces exemples peuvent être combinés et adaptés selon vos besoins spécifiques. Le serveur MCP est conçu pour être flexible et répondre à des requêtes en langage naturel!
