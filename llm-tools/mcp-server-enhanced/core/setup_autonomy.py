"""
MCP Server Extended Permissions Configuration
Donne plus d'autonomie à Claude pour gérer le serveur
"""

import json
import os
from pathlib import Path

# Configuration étendue pour le serveur MCP
MCP_EXTENDED_CONFIG = {
    "version": "2.0.0",
    "server_name": "studiosdb-extended",
    "description": "Extended MCP Server with full autonomy",
    
    # Répertoires accessibles
    "allowed_directories": [
        "/home/studiosdb",
        "/home/studiosdb/MCP-HUB",
        "/var/www",
        "/var/www/html",
        "/var/www/4lb.ca",
        "/etc/nginx/sites-available",
        "/etc/nginx/sites-enabled",
        "/var/log",
        "/tmp",
        "/home/studiosdb/studiosunisdb",
        "/home/studiosdb/mcp-server",
        "/home/studiosdb/backups"
    ],
    
    # Commandes autorisées étendues
    "allowed_commands": [
        # Commandes existantes
        "ls", "cat", "apt", "head", "tail", "grep", "find", "du", "df", 
        "ps", "systemctl", "php", "composer", "npm", "git", "pwd", "whoami",
        "chmod", "chown", "mkdir", "touch", "cp", "mv", "mysql", "mysqldump",
        "netstat", "telnet", "postconf", "doveconf",
        
        # Nouvelles commandes pour autonomie
        "rm",           # Supprimer des fichiers
        "rmdir",        # Supprimer des dossiers
        "ln",           # Créer des liens
        "wget",         # Télécharger des fichiers
        "curl",         # Requêtes HTTP
        "tar",          # Archives
        "zip",          # Compression
        "unzip",        # Décompression
        "sed",          # Édition de texte
        "awk",          # Traitement de texte
        "cut",          # Extraction de colonnes
        "sort",         # Tri
        "uniq",         # Lignes uniques
        "wc",           # Comptage
        "date",         # Date/heure
        "uptime",       # Uptime du système
        "free",         # Mémoire disponible
        "top",          # Processus en temps réel
        "htop",         # Monitoring avancé
        "iostat",       # Stats I/O
        "vmstat",       # Stats VM
        "lsof",         # Fichiers ouverts
        "ss",           # Sockets
        "ip",           # Configuration réseau
        "ping",         # Test réseau
        "traceroute",   # Route réseau
        "dig",          # DNS lookup
        "nslookup",     # DNS query
        "host",         # DNS resolution
        "service",      # Gestion des services
        "journalctl",   # Logs systemd
        "crontab",      # Tâches planifiées
        "at",           # Tâches différées
        "python3",      # Python
        "python",       # Python
        "node",         # Node.js
        "npm",          # NPM
        "yarn",         # Yarn
        "docker",       # Docker
        "docker-compose", # Docker Compose
        "nginx",        # Nginx
        "apache2ctl",   # Apache
        "redis-cli",    # Redis
        "mongod",       # MongoDB
        "psql",         # PostgreSQL
        "sqlite3",      # SQLite
        "certbot",      # SSL certificates
        "ufw",          # Firewall
        "iptables",     # Firewall rules
        "fail2ban-client", # Fail2ban
        "rsync",        # Synchronisation
        "scp",          # Secure copy
        "ssh",          # SSH client
        "screen",       # Terminal multiplexer
        "tmux",         # Terminal multiplexer
        "nano",         # Éditeur de texte
        "vi",           # Éditeur Vi
        "vim",          # Éditeur Vim
        "emacs",        # Éditeur Emacs
        "jq",           # JSON processor
        "yq",           # YAML processor
        "xmlstarlet",   # XML processor
        "bc",           # Calculator
        "expr",         # Expression evaluator
        "test",         # Test conditions
        "basename",     # Nom de fichier
        "dirname",      # Nom de répertoire
        "realpath",     # Chemin absolu
        "which",        # Localiser commande
        "whereis",      # Localiser binaire
        "type",         # Type de commande
        "env",          # Variables d'environnement
        "export",       # Exporter variables
        "source",       # Sourcer script
        "bash",         # Bash shell
        "sh",           # Shell
        "zsh",          # Z shell
        "echo",         # Afficher texte
        "printf",       # Formater sortie
        "read",         # Lire entrée
        "sleep",        # Pause
        "wait",         # Attendre processus
        "kill",         # Terminer processus
        "killall",      # Terminer tous les processus
        "pkill",        # Pattern kill
        "pgrep",        # Pattern grep processus
        "jobs",         # Jobs en arrière-plan
        "bg",           # Background
        "fg",           # Foreground
        "nohup",        # No hangup
        "nice",         # Priorité processus
        "renice",       # Changer priorité
        "time",         # Mesurer temps
        "watch",        # Répéter commande
        "xargs",        # Construire commandes
        "parallel",     # Exécution parallèle
        "tee",          # Dupliquer sortie
        "tr",           # Traduire caractères
        "fold",         # Replier lignes
        "paste",        # Fusionner lignes
        "split",        # Diviser fichiers
        "comm",         # Comparer fichiers
        "diff",         # Différences
        "patch",        # Appliquer patch
        "file",         # Type de fichier
        "stat",         # Statistiques fichier
        "md5sum",       # Checksum MD5
        "sha256sum",    # Checksum SHA256
        "base64",       # Encodage base64
        "openssl",      # OpenSSL toolkit
        "gpg",          # GPG encryption
        "shred",        # Suppression sécurisée
        "dd",           # Copy/convert
        "mount",        # Monter système de fichiers
        "umount",       # Démonter
        "fdisk",        # Partitions disque
        "lsblk",        # Lister block devices
        "blkid",        # Block device attributes
        "findmnt",      # Trouver montages
        "lscpu",        # Info CPU
        "lsmem",        # Info mémoire
        "lspci",        # Périphériques PCI
        "lsusb",        # Périphériques USB
        "dmidecode",    # Info hardware
        "sensors",      # Capteurs température
        "acpi",         # Info batterie
        "hostnamectl",  # Hostname control
        "timedatectl",  # Time/date control
        "localectl",    # Locale control
        "loginctl",     # Login control
        "systemd-analyze", # Analyse boot
        "pm2",          # Process manager Node.js
        "forever",      # Forever Node.js
        "supervisor",   # Supervisor
        "monit",        # Monitoring
        "logrotate",    # Rotation logs
        "certbot",      # Let's Encrypt
        "wp",           # WP-CLI
        "drush",        # Drupal CLI
        "artisan",      # Laravel CLI
        "symfony",      # Symfony CLI
        "django-admin", # Django CLI
        "flask",        # Flask CLI
        "pipenv",       # Python env
        "poetry",       # Python poetry
        "virtualenv",   # Virtual env
        "conda",        # Anaconda
        "cargo",        # Rust
        "go",           # Go
        "rustc",        # Rust compiler
        "gcc",          # C compiler
        "g++",          # C++ compiler
        "make",         # Make
        "cmake",        # CMake
        "automake",     # Automake
        "gradle",       # Gradle
        "maven",        # Maven
        "ant",          # Apache Ant
    ],
    
    # Permissions spéciales
    "special_permissions": {
        "allow_pipes": True,        # Permettre | 
        "allow_redirections": True, # Permettre > et >>
        "allow_background": True,   # Permettre &
        "allow_chaining": True,     # Permettre && et ;
        "allow_wildcards": True,    # Permettre * et ?
        "allow_variables": True,    # Permettre $VAR
        "allow_subshells": True,    # Permettre $(command)
        "allow_scripts": True,      # Permettre bash script.sh
        "allow_sudo": False,        # Pas de sudo (sécurité)
        "allow_su": False,          # Pas de su (sécurité)
    },
    
    # Configuration du monitoring
    "monitoring": {
        "enabled": True,
        "interval": 30,  # secondes
        "metrics": [
            "cpu_usage",
            "memory_usage",
            "disk_usage",
            "network_io",
            "process_count",
            "load_average",
            "uptime",
            "temperature"
        ],
        "alerts": {
            "cpu_threshold": 80,
            "memory_threshold": 85,
            "disk_threshold": 90,
            "load_threshold": 4.0
        }
    },
    
    # Auto-management
    "auto_management": {
        "enabled": True,
        "features": {
            "auto_cleanup_logs": True,
            "auto_cleanup_tmp": True,
            "auto_restart_services": True,
            "auto_update_packages": False,  # Prudent
            "auto_backup": True,
            "auto_optimize_database": True,
            "auto_clear_cache": True,
            "auto_fix_permissions": True,
            "auto_rotate_logs": True
        },
        "schedules": {
            "cleanup": "0 3 * * *",      # 3h du matin
            "backup": "0 2 * * *",        # 2h du matin
            "optimize": "0 4 * * 0",      # Dimanche 4h
            "monitoring": "*/5 * * * *"   # Toutes les 5 min
        }
    },
    
    # Accès aux bases de données
    "database_access": {
        "mysql": {
            "enabled": True,
            "host": "localhost",
            "user": "root",
            "databases": ["studiosdb", "studiosunisdb", "postfixadmin"]
        },
        "postgresql": {
            "enabled": False,
            "host": "localhost",
            "user": "postgres"
        },
        "redis": {
            "enabled": True,
            "host": "localhost",
            "port": 6379
        }
    },
    
    # Services managés
    "managed_services": [
        "nginx",
        "mysql",
        "php8.3-fpm",
        "postfix",
        "dovecot",
        "redis-server",
        "mcp-hub",
        "ssh",
        "cron"
    ]
}

# Sauvegarder la configuration
config_path = Path("/home/studiosdb/MCP-HUB/config/extended-permissions.json")
config_path.parent.mkdir(parents=True, exist_ok=True)

with open(config_path, 'w') as f:
    json.dump(MCP_EXTENDED_CONFIG, f, indent=2)

print(f"✅ Configuration étendue sauvegardée: {config_path}")
print(f"📊 {len(MCP_EXTENDED_CONFIG['allowed_commands'])} commandes autorisées")
print(f"📁 {len(MCP_EXTENDED_CONFIG['allowed_directories'])} répertoires accessibles")
print("🚀 Autonomie complète configurée!")
