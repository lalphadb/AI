# 🔧 Référence des Outils - AI Orchestrator v5.2.1

## Vue d'Ensemble

AI Orchestrator dispose de **70 outils** organisés en 10 catégories. Chaque outil est accessible via l'API et utilisable par l'agent ReAct.

> **Mise à jour** : 2026-01-01 - Ajout de 11 outils Gmail

---

## Catégories

| Catégorie | Outils | Description |
|-----------|--------|-------------|
| [Système](#système) | 12 | Commandes système, services, processus |
| [Docker](#docker) | 6 | Gestion des conteneurs |
| [Fichiers](#fichiers) | 4 | Lecture, écriture, recherche |
| [Git](#git) | 5 | Gestion des dépôts |
| [Réseau](#réseau) | 4 | Diagnostic réseau |
| [Mémoire](#mémoire) | 5 | Mémoire sémantique ChromaDB |
| [RAG](#rag) | 4 | Recherche documentaire augmentée |
| [Ollama](#ollama) | 8 | Gestion des modèles LLM |
| [Gmail](#gmail) | 11 | Gestion emails Google |
| [Meta](#meta) | 11 | Outils d'introspection |

---

## Gmail ⭐ NOUVEAU

### gmail_search

Recherche des emails avec requête Google (from:, subject:, is:unread, etc.).

```json
{
  "name": "gmail_search",
  "parameters": {
    "query": "string (required) - ex: from:amazon is:unread",
    "max_results": "int (default: 20)",
    "include_body": "bool (default: false)"
  }
}
```

---

### gmail_list

Liste les emails par label (INBOX, SENT, SPAM, etc.).

```json
{
  "name": "gmail_list",
  "parameters": {
    "label_id": "string (default: INBOX)",
    "max_results": "int (default: 20)",
    "include_body": "bool (default: false)"
  }
}
```

---

### gmail_read

Lit le contenu complet d'un email.

```json
{
  "name": "gmail_read",
  "parameters": {
    "message_id": "string (required)",
    "mark_as_read": "bool (default: true)"
  }
}
```

---

### gmail_send

Envoie un nouvel email.

```json
{
  "name": "gmail_send",
  "parameters": {
    "to": "string (required)",
    "subject": "string (required)",
    "body": "string (required)",
    "cc": "string (optional)",
    "bcc": "string (optional)",
    "is_html": "bool (default: false)"
  }
}
```

---

### gmail_reply

Répond à un email existant.

```json
{
  "name": "gmail_reply",
  "parameters": {
    "message_id": "string (required)",
    "body": "string (required)",
    "reply_all": "bool (default: false)"
  }
}
```

---

### gmail_delete

Supprime des emails (déplace vers corbeille).

```json
{
  "name": "gmail_delete",
  "parameters": {
    "message_ids": "array[string] (required)"
  }
}
```

---

### gmail_label_list

Liste tous les libellés disponibles.

```json
{
  "name": "gmail_label_list",
  "parameters": {}
}
```

---

### gmail_label_create

Crée un nouveau libellé.

```json
{
  "name": "gmail_label_create",
  "parameters": {
    "name": "string (required)",
    "background_color": "string (optional)",
    "text_color": "string (optional)"
  }
}
```

---

### gmail_label_apply

Applique ou retire des libellés à des emails.

```json
{
  "name": "gmail_label_apply",
  "parameters": {
    "message_ids": "array[string] (required)",
    "add_label_ids": "array[string] (optional)",
    "remove_label_ids": "array[string] (optional)"
  }
}
```

---

### gmail_archive

Archive des emails (retire de INBOX).

```json
{
  "name": "gmail_archive",
  "parameters": {
    "message_ids": "array[string] (required)"
  }
}
```

---

### gmail_stats

Statistiques de la boîte mail.

```json
{
  "name": "gmail_stats",
  "parameters": {}
}
```

**Retourne** : nombre d'emails, non lus, threads, etc.

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

**Restrictions** : Commandes blacklistées interdites (voir SECURITY.md)

---

### system_info

Informations système (CPU, RAM, disque, OS).

```json
{
  "name": "system_info",
  "parameters": {}
}
```

---

### process_list

Liste les processus actifs.

```json
{
  "name": "process_list",
  "parameters": {
    "filter": "string (optional)"
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

---

### service_control

Contrôle un service (start, stop, restart, enable, disable).

```json
{
  "name": "service_control",
  "parameters": {
    "service": "string (required)",
    "action": "string (required) - start|stop|restart|enable|disable"
  }
}
```

---

## Docker

### docker_status

Liste tous les conteneurs avec leur état.

### docker_logs

Récupère les logs d'un conteneur.

### docker_restart

Redémarre un conteneur.

### docker_exec

Exécute une commande dans un conteneur.

### docker_stats

Statistiques de ressources des conteneurs.

### docker_compose

Exécute des commandes docker compose.

---

## Fichiers

### read_file

Lit le contenu d'un fichier.

### write_file

Écrit du contenu dans un fichier.

### file_info

Informations sur un fichier (taille, permissions, dates).

### search_files

Recherche de fichiers par pattern.

---

## Git

### git_status

Statut du dépôt git.

### git_log

Historique des commits.

### git_diff

Différences entre fichiers/commits.

### git_pull

Pull les changements distants.

### git_branch

Gestion des branches.

---

## Réseau

### ping_host

Ping un hôte.

### dns_lookup

Résolution DNS.

### network_interfaces

Liste des interfaces réseau.

### udm_network_info

Informations réseau UDM-Pro.

---

## Mémoire (ChromaDB)

### memory_store

Stocke une information en mémoire sémantique.

### memory_recall

Recherche une information par similarité.

### memory_list

Liste les mémoires stockées.

### memory_delete

Supprime une mémoire.

### memory_stats

Statistiques de la mémoire.

---

## RAG (Retrieval Augmented Generation)

### rag_search

Recherche dans la documentation indexée.

### rag_index

Indexe un fichier.

### rag_index_directory

Indexe un répertoire entier.

### rag_stats

Statistiques du système RAG.

---

## Ollama

### ollama_list

Liste des modèles installés.

### ollama_ps

Modèles actuellement chargés en mémoire.

### ollama_pull

Télécharge un modèle.

### ollama_run

Lance une inférence.

### ollama_info

Informations sur un modèle.

### ollama_stop

Arrête un modèle.

### ollama_restart

Redémarre le service Ollama.

### ollama_switch_model

Change le modèle actif.

---

## Meta

### list_tools

Liste tous les outils disponibles.

### reload_tools

Recharge les outils dynamiquement.

### create_tool

Crée un nouvel outil.

### delete_tool

Supprime un outil.

### analyze_image

Analyse une image avec un modèle vision.

### create_plan

Crée un plan d'action structuré.

### web_fetch

Récupère le contenu d'une page web.

### check_url

Vérifie la disponibilité d'une URL.

### self_improve

Propose des améliorations automatiques.

### save_learning

Sauvegarde un apprentissage.

### get_learnings

Récupère les apprentissages.

---

## Configuration

Les outils sont chargés dynamiquement depuis `backend/tools/*_tools.py`.

Pour ajouter un nouvel outil :

1. Créer un fichier `backend/tools/mon_outil_tools.py`
2. Utiliser le décorateur `@register_tool`
3. Redémarrer ou appeler `reload_tools()`

```python
from tools import register_tool

@register_tool("mon_outil", description="Description de l'outil")
async def mon_outil(params: dict) -> str:
    # Implémentation
    return "Résultat"
```

---

*Dernière mise à jour : 2026-01-01*
