"""
Outils Ollama pour AI Orchestrator v5.1
Gestion des modeles LLM via Ollama sur l'hote
"""

import json
import os

from tools import register_tool
from utils.async_subprocess import run_command_async

HOST = os.getenv("HOST_IP", "host.docker.internal")
USER = os.getenv("HOST_USER", "lalpha")
KEY = "/root/.ssh/id_ed25519"
SSH = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -i {KEY} {USER}@{HOST}"

OLLAMA_HOST = "localhost:11434"


async def ssh_cmd(cmd: str, timeout: int = 60) -> tuple:
    """Execute une commande sur l'hote via SSH"""
    return await run_command_async(f'{SSH} "{cmd}"', timeout=timeout)


@register_tool("ollama_list", description="Liste les modeles Ollama installes")
async def ollama_list(params: dict) -> str:
    """Liste tous les modeles Ollama disponibles sur l'hote"""
    out, code = await ssh_cmd("ollama list", 30)
    if code != 0:
        return f"❌ Erreur Ollama: {out}"

    lines = out.strip().split("\n")
    if len(lines) <= 1:
        return "📭 Aucun modele Ollama installe"

    result = ["🤖 **Modeles Ollama installes:**\n"]
    result.append("| Modele | Taille | Modifie |")
    result.append("|--------|--------|---------|")

    for line in lines[1:]:  # Skip header
        parts = line.split()
        if len(parts) >= 3:
            name = parts[0]
            size = parts[2] if len(parts) > 2 else "?"
            modified = " ".join(parts[3:5]) if len(parts) > 4 else "?"
            result.append(f"| {name} | {size} | {modified} |")

    return "\n".join(result)


@register_tool("ollama_status", description="Verifie le statut du service Ollama")
async def ollama_status(params: dict) -> str:
    """Verifie si Ollama est en cours d'execution"""
    # Verifier le service systemd
    out, code = await ssh_cmd("systemctl is-active ollama", 10)
    service_status = out.strip()

    # Verifier l'API
    api_out, api_code = await ssh_cmd(f"curl -s http://{OLLAMA_HOST}/api/tags | head -c 100", 10)
    api_ok = api_code == 0 and "models" in api_out

    # Verifier les processus
    ps_out, _ = await ssh_cmd("pgrep -a ollama | head -3", 10)

    result = ["🦙 **Statut Ollama:**\n"]
    result.append(
        f"- Service systemd: {'🟢 actif' if service_status == 'active' else '🔴 ' + service_status}"
    )
    result.append(f"- API ({OLLAMA_HOST}): {'🟢 repond' if api_ok else '🔴 inaccessible'}")

    if ps_out.strip():
        result.append(f"\n**Processus:**\n```\n{ps_out}\n```")

    return "\n".join(result)


@register_tool(
    "ollama_pull", description="Telecharge un modele Ollama", parameters={"model": "str"}
)
async def ollama_pull(params: dict) -> str:
    """Telecharge un nouveau modele Ollama"""
    model = params.get("model", "")
    if not model:
        return "❌ Erreur: nom du modele requis"

    # Validation basique du nom
    if not all(c.isalnum() or c in ".-:_" for c in model):
        return "❌ Nom de modele invalide"

    out, code = await ssh_cmd(f"ollama pull {model}", 600)  # 10 min timeout

    if code == 0:
        return f"✅ Modele {model} telecharge avec succes\n{out[-1000:]}"
    return f"❌ Erreur telechargement {model}:\n{out[-1000:]}"


@register_tool(
    "ollama_run",
    description="Execute une requete sur un modele",
    parameters={"model": "str", "prompt": "str"},
)
async def ollama_run(params: dict) -> str:
    """Execute une requete simple sur un modele Ollama"""
    model = params.get("model", "")
    prompt = params.get("prompt", "")

    if not model or not prompt:
        return "❌ Erreur: model et prompt requis"

    # Echapper les guillemets dans le prompt
    prompt_escaped = prompt.replace('"', '\\"').replace("'", "\\'")

    # Utiliser l'API directement
    cmd = f'curl -s http://{OLLAMA_HOST}/api/generate -d \'{{"model":"{model}","prompt":"{prompt_escaped}","stream":false}}\''
    out, code = await ssh_cmd(cmd, 120)

    if code != 0:
        return f"❌ Erreur API Ollama: {out}"

    try:
        data = json.loads(out)
        response = data.get("response", "Pas de reponse")
        return f"🤖 **{model}:**\n{response}"
    except json.JSONDecodeError:
        return f"❌ Reponse invalide: {out[:500]}"


@register_tool("ollama_info", description="Informations sur un modele", parameters={"model": "str"})
async def ollama_info(params: dict) -> str:
    """Affiche les informations detaillees d'un modele"""
    model = params.get("model", "")
    if not model:
        return "❌ Erreur: nom du modele requis"

    out, code = await ssh_cmd(f"ollama show {model}", 30)
    if code != 0:
        return f"❌ Modele non trouve: {model}"

    return f"📋 **Infos {model}:**\n```\n{out[:2000]}\n```"


@register_tool("ollama_rm", description="Supprime un modele Ollama", parameters={"model": "str"})
async def ollama_rm(params: dict) -> str:
    """Supprime un modele Ollama"""
    model = params.get("model", "")
    if not model:
        return "❌ Erreur: nom du modele requis"

    out, code = await ssh_cmd(f"ollama rm {model}", 30)
    if code == 0:
        return f"✅ Modele {model} supprime"
    return f"❌ Erreur suppression: {out}"


@register_tool("ollama_ps", description="Liste les modeles en cours d'execution")
async def ollama_ps(params: dict) -> str:
    """Liste les modeles actuellement charges en memoire"""
    out, code = await ssh_cmd("ollama ps", 10)
    if code != 0:
        return f"❌ Erreur: {out}"

    if not out.strip() or "NAME" not in out:
        return "📭 Aucun modele actuellement charge en memoire"

    return f"🔄 **Modeles en memoire:**\n```\n{out}\n```"


@register_tool("ollama_restart", description="Redemarre le service Ollama")
async def ollama_restart(params: dict) -> str:
    """Redemarre le service Ollama sur l'hote"""
    out, code = await ssh_cmd(
        "sudo systemctl restart ollama && sleep 2 && systemctl is-active ollama", 30
    )

    if "active" in out:
        return "✅ Service Ollama redemarre avec succes"
    return f"❌ Erreur redemarrage: {out}"
