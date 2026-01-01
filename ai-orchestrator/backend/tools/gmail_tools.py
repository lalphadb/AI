"""
Outils Gmail pour AI Orchestrator v5.0
Intégration avec Google Gmail API via OAuth2

Outils disponibles:
- gmail_search: Rechercher des emails
- gmail_list: Lister emails par label
- gmail_read: Lire un email complet
- gmail_send: Envoyer un email
- gmail_reply: Répondre à un email
- gmail_delete: Supprimer emails
- gmail_label_list: Lister les libellés
- gmail_label_create: Créer un libellé
- gmail_label_apply: Appliquer libellés
- gmail_archive: Archiver emails
- gmail_stats: Statistiques boîte mail
"""

import base64
import json
import logging
import os
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from tools import register_tool

logger = logging.getLogger(__name__)

# Chemins des credentials
MCP_DIR = Path("/home/lalpha/projets/ai-tools/mcp-servers")
CREDENTIALS_PATH = MCP_DIR / "SECRET_GMAIL_API.json"
TOKEN_PATH = MCP_DIR / "gmail_token.json"

# Client Gmail (lazy init)
_gmail_client = None


def _get_gmail_client():
    """Initialise le client Gmail avec OAuth2."""
    global _gmail_client
    if _gmail_client:
        return _gmail_client

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        if not TOKEN_PATH.exists():
            raise FileNotFoundError(
                f"Token Gmail non trouvé: {TOKEN_PATH}\n"
                "Lancez: cd /home/lalpha/projets/ai-tools/mcp-servers/gmail-mcp && npm run auth"
            )

        token_data = json.loads(TOKEN_PATH.read_text())
        creds = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=json.loads(CREDENTIALS_PATH.read_text())["installed"]["client_id"],
            client_secret=json.loads(CREDENTIALS_PATH.read_text())["installed"]["client_secret"],
        )
        _gmail_client = build("gmail", "v1", credentials=creds)
        logger.info("✅ Client Gmail initialisé")
        return _gmail_client

    except ImportError:
        raise ImportError("Installez: pip install google-auth google-auth-oauthlib google-api-python-client")
    except Exception as e:
        logger.error(f"Erreur Gmail: {e}")
        raise


def _decode_body(payload: dict) -> str:
    """Extrait le corps d'un email."""
    if "body" in payload and payload["body"].get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            elif part["mimeType"] == "text/html":
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    return ""


def _get_headers(headers: list) -> dict:
    """Extrait les headers en dict."""
    return {h["name"].lower(): h["value"] for h in headers if h.get("name")}


def _format_message(msg: dict, include_body: bool = False) -> dict:
    """Formate un message Gmail."""
    headers = _get_headers(msg.get("payload", {}).get("headers", []))
    result = {
        "id": msg["id"],
        "threadId": msg.get("threadId"),
        "snippet": msg.get("snippet"),
        "from": headers.get("from"),
        "to": headers.get("to"),
        "subject": headers.get("subject"),
        "date": headers.get("date"),
        "labels": msg.get("labelIds", []),
        "isUnread": "UNREAD" in msg.get("labelIds", []),
    }
    if include_body:
        result["body"] = _decode_body(msg.get("payload", {}))
    return result


@register_tool(
    "gmail_search",
    description="Rechercher des emails Gmail (from:, to:, subject:, is:unread, after:, before:, label:, has:attachment)",
    parameters={"query": "str - Requête Gmail", "max_results": "int - Max résultats (défaut: 20)", "include_body": "bool - Inclure contenu (défaut: false)"}
)
async def gmail_search(params: dict) -> str:
    """Rechercher des emails."""
    try:
        gmail = _get_gmail_client()
        query = params.get("query", "")
        max_results = min(params.get("max_results", 20), 100)
        include_body = params.get("include_body", False)

        results = gmail.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        messages = []

        for msg_ref in results.get("messages", []):
            msg = gmail.users().messages().get(
                userId="me",
                id=msg_ref["id"],
                format="full" if include_body else "metadata",
                metadataHeaders=["From", "To", "Subject", "Date"]
            ).execute()
            messages.append(_format_message(msg, include_body))

        return json.dumps({
            "query": query,
            "count": len(messages),
            "total_estimate": results.get("resultSizeEstimate", 0),
            "messages": messages
        }, indent=2, ensure_ascii=False)

    except Exception as e:
        return f"❌ Erreur recherche Gmail: {e}"


@register_tool(
    "gmail_list",
    description="Lister les emails par label (INBOX, SENT, TRASH, SPAM, ou libellé custom)",
    parameters={"label": "str - Label (défaut: INBOX)", "max_results": "int - Max résultats", "page_token": "str - Token pagination"}
)
async def gmail_list(params: dict) -> str:
    """Lister emails par label."""
    try:
        gmail = _get_gmail_client()
        label = params.get("label", "INBOX")
        max_results = min(params.get("max_results", 20), 100)
        page_token = params.get("page_token")

        results = gmail.users().messages().list(
            userId="me",
            labelIds=[label],
            maxResults=max_results,
            pageToken=page_token
        ).execute()

        messages = []
        for msg_ref in results.get("messages", []):
            msg = gmail.users().messages().get(
                userId="me",
                id=msg_ref["id"],
                format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"]
            ).execute()
            messages.append(_format_message(msg))

        return json.dumps({
            "label": label,
            "count": len(messages),
            "nextPageToken": results.get("nextPageToken"),
            "messages": messages
        }, indent=2, ensure_ascii=False)

    except Exception as e:
        return f"❌ Erreur listing Gmail: {e}"


@register_tool(
    "gmail_read",
    description="Lire le contenu complet d'un email",
    parameters={"message_id": "str - ID du message", "mark_as_read": "bool - Marquer comme lu (défaut: true)"}
)
async def gmail_read(params: dict) -> str:
    """Lire un email complet."""
    try:
        gmail = _get_gmail_client()
        message_id = params.get("message_id")
        mark_as_read = params.get("mark_as_read", True)

        if not message_id:
            return "❌ message_id requis"

        msg = gmail.users().messages().get(userId="me", id=message_id, format="full").execute()

        if mark_as_read and "UNREAD" in msg.get("labelIds", []):
            gmail.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()

        headers = _get_headers(msg.get("payload", {}).get("headers", []))

        # Extraire pièces jointes
        attachments = []
        def extract_attachments(part):
            if part.get("filename") and part.get("body", {}).get("attachmentId"):
                attachments.append({
                    "filename": part["filename"],
                    "mimeType": part.get("mimeType"),
                    "size": part.get("body", {}).get("size")
                })
            for p in part.get("parts", []):
                extract_attachments(p)
        
        if msg.get("payload"):
            extract_attachments(msg["payload"])

        return json.dumps({
            "id": msg["id"],
            "threadId": msg.get("threadId"),
            "from": headers.get("from"),
            "to": headers.get("to"),
            "cc": headers.get("cc"),
            "subject": headers.get("subject"),
            "date": headers.get("date"),
            "body": _decode_body(msg.get("payload", {})),
            "attachments": attachments,
            "labels": msg.get("labelIds", [])
        }, indent=2, ensure_ascii=False)

    except Exception as e:
        return f"❌ Erreur lecture Gmail: {e}"


@register_tool(
    "gmail_send",
    description="Envoyer un email",
    parameters={"to": "str - Destinataire", "subject": "str - Sujet", "body": "str - Contenu", "cc": "str - CC (optionnel)", "html": "bool - Format HTML (défaut: false)"}
)
async def gmail_send(params: dict) -> str:
    """Envoyer un email."""
    try:
        gmail = _get_gmail_client()
        to = params.get("to")
        subject = params.get("subject")
        body = params.get("body")
        cc = params.get("cc")
        is_html = params.get("html", False)

        if not all([to, subject, body]):
            return "❌ to, subject et body requis"

        message = MIMEText(body, "html" if is_html else "plain", "utf-8")
        message["To"] = to
        message["Subject"] = subject
        if cc:
            message["Cc"] = cc

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        result = gmail.users().messages().send(userId="me", body={"raw": raw}).execute()

        return json.dumps({
            "success": True,
            "messageId": result["id"],
            "to": to,
            "subject": subject
        }, indent=2)

    except Exception as e:
        return f"❌ Erreur envoi Gmail: {e}"


@register_tool(
    "gmail_reply",
    description="Répondre à un email",
    parameters={"message_id": "str - ID du message original", "body": "str - Contenu de la réponse", "reply_all": "bool - Répondre à tous (défaut: false)"}
)
async def gmail_reply(params: dict) -> str:
    """Répondre à un email."""
    try:
        gmail = _get_gmail_client()
        message_id = params.get("message_id")
        body = params.get("body")
        reply_all = params.get("reply_all", False)

        if not all([message_id, body]):
            return "❌ message_id et body requis"

        # Récupérer l'email original
        orig = gmail.users().messages().get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=["From", "To", "Cc", "Subject", "Message-ID"]
        ).execute()

        headers = _get_headers(orig.get("payload", {}).get("headers", []))
        subject = headers.get("subject", "")
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        to = headers.get("from")
        cc = ""
        if reply_all:
            all_recipients = []
            if headers.get("to"):
                all_recipients.extend(headers["to"].split(","))
            if headers.get("cc"):
                all_recipients.extend(headers["cc"].split(","))
            cc = ", ".join([r.strip() for r in all_recipients if r.strip() != to])

        message = MIMEText(body, "plain", "utf-8")
        message["To"] = to
        message["Subject"] = subject
        if cc:
            message["Cc"] = cc
        if headers.get("message-id"):
            message["In-Reply-To"] = headers["message-id"]
            message["References"] = headers["message-id"]

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        result = gmail.users().messages().send(
            userId="me",
            body={"raw": raw, "threadId": orig.get("threadId")}
        ).execute()

        return json.dumps({
            "success": True,
            "messageId": result["id"],
            "to": to,
            "subject": subject
        }, indent=2)

    except Exception as e:
        return f"❌ Erreur réponse Gmail: {e}"


@register_tool(
    "gmail_delete",
    description="Supprimer des emails (mettre à la corbeille)",
    parameters={"message_ids": "list - Liste des IDs à supprimer"}
)
async def gmail_delete(params: dict) -> str:
    """Supprimer emails (corbeille)."""
    try:
        gmail = _get_gmail_client()
        message_ids = params.get("message_ids", [])

        if not message_ids:
            return "❌ message_ids requis (liste d'IDs)"

        gmail.users().messages().batchModify(
            userId="me",
            body={"ids": message_ids, "addLabelIds": ["TRASH"], "removeLabelIds": ["INBOX"]}
        ).execute()

        return json.dumps({
            "success": True,
            "action": "trash",
            "count": len(message_ids)
        }, indent=2)

    except Exception as e:
        return f"❌ Erreur suppression Gmail: {e}"


@register_tool(
    "gmail_label_list",
    description="Lister tous les libellés Gmail"
)
async def gmail_label_list(params: dict) -> str:
    """Lister les libellés."""
    try:
        gmail = _get_gmail_client()
        results = gmail.users().labels().list(userId="me").execute()

        labels = []
        for label in results.get("labels", []):
            detail = gmail.users().labels().get(userId="me", id=label["id"]).execute()
            labels.append({
                "id": label["id"],
                "name": label["name"],
                "type": label.get("type"),
                "total": detail.get("messagesTotal", 0),
                "unread": detail.get("messagesUnread", 0)
            })

        system_labels = [l for l in labels if l["type"] == "system"]
        user_labels = [l for l in labels if l["type"] == "user"]

        return json.dumps({
            "system": system_labels,
            "user": user_labels
        }, indent=2, ensure_ascii=False)

    except Exception as e:
        return f"❌ Erreur listing labels: {e}"


@register_tool(
    "gmail_label_create",
    description="Créer un nouveau libellé",
    parameters={"name": "str - Nom du libellé", "color": "str - Couleur hex (optionnel, ex: #ff0000)"}
)
async def gmail_label_create(params: dict) -> str:
    """Créer un libellé."""
    try:
        gmail = _get_gmail_client()
        name = params.get("name")
        color = params.get("color")

        if not name:
            return "❌ name requis"

        body = {
            "name": name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show"
        }
        if color:
            body["color"] = {"backgroundColor": color, "textColor": "#ffffff"}

        result = gmail.users().labels().create(userId="me", body=body).execute()

        return json.dumps({
            "success": True,
            "id": result["id"],
            "name": result["name"]
        }, indent=2)

    except Exception as e:
        return f"❌ Erreur création label: {e}"


@register_tool(
    "gmail_label_apply",
    description="Appliquer ou retirer des libellés à des emails",
    parameters={"message_ids": "list - IDs des messages", "add_labels": "list - Labels à ajouter", "remove_labels": "list - Labels à retirer"}
)
async def gmail_label_apply(params: dict) -> str:
    """Appliquer/retirer labels."""
    try:
        gmail = _get_gmail_client()
        message_ids = params.get("message_ids", [])
        add_labels = params.get("add_labels", [])
        remove_labels = params.get("remove_labels", [])

        if not message_ids:
            return "❌ message_ids requis"

        body = {"ids": message_ids}
        if add_labels:
            body["addLabelIds"] = add_labels
        if remove_labels:
            body["removeLabelIds"] = remove_labels

        gmail.users().messages().batchModify(userId="me", body=body).execute()

        return json.dumps({
            "success": True,
            "count": len(message_ids),
            "added": add_labels,
            "removed": remove_labels
        }, indent=2)

    except Exception as e:
        return f"❌ Erreur application labels: {e}"


@register_tool(
    "gmail_archive",
    description="Archiver des emails (retirer de INBOX)",
    parameters={"message_ids": "list - IDs des messages à archiver"}
)
async def gmail_archive(params: dict) -> str:
    """Archiver emails."""
    try:
        gmail = _get_gmail_client()
        message_ids = params.get("message_ids", [])

        if not message_ids:
            return "❌ message_ids requis"

        gmail.users().messages().batchModify(
            userId="me",
            body={"ids": message_ids, "removeLabelIds": ["INBOX"]}
        ).execute()

        return json.dumps({
            "success": True,
            "archived": len(message_ids)
        }, indent=2)

    except Exception as e:
        return f"❌ Erreur archivage: {e}"


@register_tool(
    "gmail_stats",
    description="Obtenir les statistiques de la boîte mail"
)
async def gmail_stats(params: dict) -> str:
    """Statistiques boîte mail."""
    try:
        gmail = _get_gmail_client()

        # Profil
        profile = gmail.users().getProfile(userId="me").execute()

        # Labels avec stats
        labels_result = gmail.users().labels().list(userId="me").execute()
        stats = []

        for label in labels_result.get("labels", []):
            detail = gmail.users().labels().get(userId="me", id=label["id"]).execute()
            if detail.get("messagesTotal", 0) > 0:
                stats.append({
                    "name": detail["name"],
                    "total": detail.get("messagesTotal", 0),
                    "unread": detail.get("messagesUnread", 0)
                })

        stats.sort(key=lambda x: x["total"], reverse=True)

        return json.dumps({
            "email": profile.get("emailAddress"),
            "totalMessages": profile.get("messagesTotal"),
            "totalThreads": profile.get("threadsTotal"),
            "topLabels": stats[:15]
        }, indent=2, ensure_ascii=False)

    except Exception as e:
        return f"❌ Erreur stats Gmail: {e}"
