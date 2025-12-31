# 🔧 Référence des Outils - AI Orchestrator v5.2

## Vue d'Ensemble

AI Orchestrator dispose de **57 outils** organisés en 9 catégories. Chaque outil est accessible via l'API et utilisable par l'agent ReAct.

---

## Catégories

| Catégorie | Outils | Description |
|-----------|--------|-------------|
| [Système](#système) | 9 | Commandes système, services, processus |
| [Docker](#docker) | 6 | Gestion des conteneurs |
| [Fichiers](#fichiers) | 5 | Lecture, écriture, recherche |
| [Git](#git) | 5 | Gestion des dépôts |
| [Réseau](#réseau) | 7 | Diagnostic réseau |
| [Mémoire](#mémoire) | 5 | Mémoire sémantique ChromaDB |
| [Ollama](#ollama) | 8 | Gestion des modèles LLM |
| [IA](#ia) | 5 | Outils d'intelligence artificielle |
| [Meta](#meta) | 6 | Outils d'introspection |

---

## Système

### execute_command

Exécute une commande shell sur le serveur.

```json
{
  "name": "execute_command",
  "parameters": {
    "command": "string (required)"
  }
}
```

**Exemple** :
```
execute_command({"command": "df -h"})
```

**Restrictions** : Commandes blacklistées interdites (voir SECURITY.md)

---

### system_info

Retourne les informations système.

```json
{
  "name": "system_info",
  "parameters": {}
}
```

**Retour** : CPU, RAM, disque, uptime, load average

---

### disk_usage

Analyse l'utilisation disque d'un chemin.

```json
{
  "name": "disk_usage",
  "parameters": {
    "path": "string (default: /)"
  }
}
```

---

### process_list

Liste les processus en cours.

```json
{
  "name": "process_list",
  "parameters": {
    "limit": "int (default: 20)",
    "sort_by": "string (cpu|memory|pid)"
  }
}
```

---

### service_status

Vérifie le statut d'un service systemd.

```json
{
  "name": "service_status",
  "parameters": {
    "service": "string (required)"
  }
}
```

**Exemple** : `service_status({"service": "docker"})`

---

### service_control

Contrôle un service systemd.

```json
{
  "name": "service_control",
  "parameters": {
    "service": "string (required)",
    "action": "string (start|stop|restart|status)"
  }
}
```

---

### logs_view

Affiche les logs d'un fichier.

```json
{
  "name": "logs_view",
  "parameters": {
    "file": "string (required)",
    "lines": "int (default: 50)",
    "filter": "string (optional)"
  }
}
```

---

### package_update

Met à jour les paquets système.

```json
{
  "name": "package_update",
  "parameters": {}
}
```

---

### package_install

Installe un paquet.

```json
{
  "name": "package_install",
  "parameters": {
    "package": "string (required)"
  }
}
```

---

## Docker

### docker_status

Liste les conteneurs Docker.

```json
{
  "name": "docker_status",
  "parameters": {
    "all": "bool (default: false)"
  }
}
```

---

### docker_logs

Affiche les logs d'un conteneur.

```json
{
  "name": "docker_logs",
  "parameters": {
    "container": "string (required)",
    "lines": "int (default: 100)",
    "follow": "bool (default: false)"
  }
}
```

---

### docker_restart

Redémarre un conteneur.

```json
{
  "name": "docker_restart",
  "parameters": {
    "container": "string (required)"
  }
}
```

---

### docker_exec

Exécute une commande dans un conteneur.

```json
{
  "name": "docker_exec",
  "parameters": {
    "container": "string (required)",
    "command": "string (required)"
  }
}
```

---

### docker_stats

Statistiques des conteneurs.

```json
{
  "name": "docker_stats",
  "parameters": {}
}
```

---

### docker_compose

Exécute une commande docker-compose.

```json
{
  "name": "docker_compose",
  "parameters": {
    "action": "string (up|down|restart|logs|ps)",
    "service": "string (optional)",
    "path": "string (default: /home/lalpha/projets/infrastructure/unified-stack)"
  }
}
```

---

## Fichiers

### read_file

Lit le contenu d'un fichier.

```json
{
  "name": "read_file",
  "parameters": {
    "path": "string (required)",
    "lines": "int (optional, limit lines)"
  }
}
```

---

### write_file

Écrit du contenu dans un fichier.

```json
{
  "name": "write_file",
  "parameters": {
    "path": "string (required)",
    "content": "string (required)",
    "append": "bool (default: false)"
  }
}
```

---

### list_directory

Liste le contenu d'un répertoire.

```json
{
  "name": "list_directory",
  "parameters": {
    "path": "string (required)",
    "recursive": "bool (default: false)",
    "max_depth": "int (default: 2)"
  }
}
```

---

### search_files

Recherche des fichiers.

```json
{
  "name": "search_files",
  "parameters": {
    "pattern": "string (required)",
    "path": "string (default: .)",
    "type": "string (file|dir|all)"
  }
}
```

---

### file_info

Informations sur un fichier.

```json
{
  "name": "file_info",
  "parameters": {
    "path": "string (required)"
  }
}
```

**Retour** : Taille, permissions, dates, type MIME

---

## Git

### git_status

Statut du dépôt Git.

```json
{
  "name": "git_status",
  "parameters": {
    "path": "string (default: .)"
  }
}
```

---

### git_log

Historique des commits.

```json
{
  "name": "git_log",
  "parameters": {
    "path": "string (default: .)",
    "limit": "int (default: 10)",
    "oneline": "bool (default: true)"
  }
}
```

---

### git_diff

Différences dans le dépôt.

```json
{
  "name": "git_diff",
  "parameters": {
    "path": "string (default: .)",
    "staged": "bool (default: false)"
  }
}
```

---

### git_pull

Pull les changements.

```json
{
  "name": "git_pull",
  "parameters": {
    "path": "string (default: .)"
  }
}
```

---

### git_branch

Gestion des branches.

```json
{
  "name": "git_branch",
  "parameters": {
    "path": "string (default: .)",
    "action": "string (list|current|create|switch)",
    "name": "string (optional)"
  }
}
```

---

## Réseau

### ping_host

Ping un hôte.

```json
{
  "name": "ping_host",
  "parameters": {
    "host": "string (required)",
    "count": "int (default: 4)"
  }
}
```

---

### dns_lookup

Résolution DNS.

```json
{
  "name": "dns_lookup",
  "parameters": {
    "domain": "string (required)",
    "type": "string (default: A)"
  }
}
```

---

### check_url

Vérifie une URL HTTP.

```json
{
  "name": "check_url",
  "parameters": {
    "url": "string (required)",
    "method": "string (default: GET)",
    "timeout": "int (default: 10)"
  }
}
```

---

### network_interfaces

Liste les interfaces réseau.

```json
{
  "name": "network_interfaces",
  "parameters": {}
}
```

---

### udm_status

Statut du UDM-Pro.

```json
{
  "name": "udm_status",
  "parameters": {}
}
```

---

### udm_network_info

Informations réseau UDM-Pro.

```json
{
  "name": "udm_network_info",
  "parameters": {}
}
```

---

### udm_clients

Liste des clients UDM-Pro.

```json
{
  "name": "udm_clients",
  "parameters": {}
}
```

---

## Mémoire

### memory_store

Stocke une information en mémoire sémantique.

```json
{
  "name": "memory_store",
  "parameters": {
    "content": "string (required)",
    "metadata": "object (optional)"
  }
}
```

**Exemple** :
```json
{
  "content": "Le projet JSR utilise React et TailwindCSS",
  "metadata": {"project": "jsr", "type": "tech_stack"}
}
```

---

### memory_recall

Recherche sémantique en mémoire.

```json
{
  "name": "memory_recall",
  "parameters": {
    "query": "string (required)",
    "limit": "int (default: 5)"
  }
}
```

---

### memory_list

Liste les entrées en mémoire.

```json
{
  "name": "memory_list",
  "parameters": {
    "limit": "int (default: 20)",
    "filter": "object (optional)"
  }
}
```

---

### memory_delete

Supprime une entrée mémoire.

```json
{
  "name": "memory_delete",
  "parameters": {
    "id": "string (required)"
  }
}
```

---

### memory_stats

Statistiques de la mémoire.

```json
{
  "name": "memory_stats",
  "parameters": {}
}
```

---

## Ollama

### ollama_list

Liste les modèles installés.

```json
{
  "name": "ollama_list",
  "parameters": {}
}
```

---

### ollama_status

Statut d'Ollama.

```json
{
  "name": "ollama_status",
  "parameters": {}
}
```

---

### ollama_ps

Modèles actuellement chargés.

```json
{
  "name": "ollama_ps",
  "parameters": {}
}
```

---

### ollama_info

Informations sur un modèle.

```json
{
  "name": "ollama_info",
  "parameters": {
    "model": "string (required)"
  }
}
```

---

### ollama_restart

Redémarre Ollama.

```json
{
  "name": "ollama_restart",
  "parameters": {}
}
```

---

### ollama_rm

Supprime un modèle.

```json
{
  "name": "ollama_rm",
  "parameters": {
    "model": "string (required)"
  }
}
```

---

## IA

### summarize

Résume un texte.

```json
{
  "name": "summarize",
  "parameters": {
    "text": "string (required)",
    "max_length": "int (default: 200)"
  }
}
```

---

### create_plan

Crée un plan d'action.

```json
{
  "name": "create_plan",
  "parameters": {
    "goal": "string (required)",
    "context": "string (optional)"
  }
}
```

---

### analyze_image

Analyse une image (vision).

```json
{
  "name": "analyze_image",
  "parameters": {
    "image_path": "string (required)",
    "question": "string (optional)"
  }
}
```

---

### web_search

Recherche web.

```json
{
  "name": "web_search",
  "parameters": {
    "query": "string (required)",
    "limit": "int (default: 5)"
  }
}
```

---

### final_answer

Retourne la réponse finale (termine la boucle ReAct).

```json
{
  "name": "final_answer",
  "parameters": {
    "answer": "string (required)"
  }
}
```

---

## Meta

### list_my_tools

Liste tous les outils disponibles.

```json
{
  "name": "list_my_tools",
  "parameters": {
    "category": "string (optional)"
  }
}
```

---

### reload_my_tools

Recharge les outils dynamiques.

```json
{
  "name": "reload_my_tools",
  "parameters": {}
}
```

---

### view_tool_code

Affiche le code source d'un outil.

```json
{
  "name": "view_tool_code",
  "parameters": {
    "tool_name": "string (required)"
  }
}
```

---

## Créer un Nouvel Outil

### Template

```python
# backend/tools/my_tools.py
from tools import register_tool

@register_tool(
    "mon_outil",
    description="Description de ce que fait l'outil",
    parameters={
        "param1": "string (required) - Description",
        "param2": "int (optional) - Description"
    }
)
async def mon_outil(params: dict) -> str:
    """
    Implémentation de l'outil.
    
    Args:
        params: Dictionnaire des paramètres
        
    Returns:
        Résultat sous forme de string
    """
    param1 = params.get("param1", "")
    param2 = params.get("param2", 10)
    
    # Logique métier
    result = f"Résultat pour {param1}"
    
    return result
```

### Bonnes Pratiques

1. **Async** : Toujours utiliser `async def`
2. **Validation** : Valider les paramètres en entrée
3. **Erreurs** : Retourner des messages d'erreur clairs
4. **Logs** : Logger les actions importantes
5. **Sécurité** : Valider les chemins et commandes

---

*Référence des Outils - AI Orchestrator v5.2*
