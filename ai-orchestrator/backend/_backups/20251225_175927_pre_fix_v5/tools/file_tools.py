"""
Outils de gestion de fichiers pour AI Orchestrator v4.0
- read_file
- write_file
- list_directory
- search_files
"""

import os
from pathlib import Path
from tools import register_tool
from utils.async_subprocess import run_command_async


@register_tool("read_file")
async def read_file(params: dict, security_validator=None, audit_logger=None) -> str:
    """Lire le contenu d'un fichier"""
    path = params.get("path", "")
    if not path:
        return "Erreur: chemin du fichier requis"
    
    # Validation de sécurité si disponible
    if security_validator:
        allowed, reason = security_validator(f"cat {path}")
        if not allowed:
            return f"🚫 Accès bloqué: {reason}"
    
    try:
        # Vérifier si le fichier existe
        if not os.path.exists(path):
            return f"❌ Fichier non trouvé: {path}"
        
        if not os.path.isfile(path):
            return f"❌ Ce n'est pas un fichier: {path}"
        
        # Limiter la taille
        file_size = os.path.getsize(path)
        if file_size > 500000:  # 500KB max
            return f"⚠️ Fichier trop volumineux ({file_size} octets). Utilisez head/tail."
        
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Numéroter les lignes
        lines = content.split('\n')
        numbered = [f"{i+1:4d}| {line}" for i, line in enumerate(lines)]
        
        return f"Fichier: {path} ({len(lines)} lignes)\n" + "-"*50 + "\n" + "\n".join(numbered[:500])
        
    except PermissionError:
        return f"🚫 Permission refusée: {path}"
    except Exception as e:
        return f"❌ Erreur lecture: {str(e)}"


@register_tool("write_file")
async def write_file(params: dict, security_validator=None, audit_logger=None) -> str:
    """Écrire du contenu dans un fichier"""
    path = params.get("path", "")
    content = params.get("content", "")
    
    if not path:
        return "Erreur: chemin du fichier requis"
    
    # Validation de sécurité si disponible
    if security_validator:
        allowed, reason = security_validator(f"write {path}")
        if not allowed:
            return f"🚫 Écriture bloquée: {reason}"
    
    try:
        # Créer le répertoire parent si nécessaire
        parent = Path(path).parent
        parent.mkdir(parents=True, exist_ok=True)
        
        # Créer un backup si le fichier existe
        if os.path.exists(path):
            backup_path = f"{path}.backup"
            import shutil
            shutil.copy2(path, backup_path)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"✅ Fichier écrit: {path} ({len(content)} caractères)"
        
    except PermissionError:
        return f"🚫 Permission refusée: {path}"
    except Exception as e:
        return f"❌ Erreur écriture: {str(e)}"


@register_tool("list_directory")
async def list_directory(params: dict) -> str:
    """Lister le contenu d'un répertoire"""
    path = params.get("path", ".")
    recursive = params.get("recursive", False)
    
    try:
        if not os.path.exists(path):
            return f"❌ Répertoire non trouvé: {path}"
        
        if not os.path.isdir(path):
            return f"❌ Ce n'est pas un répertoire: {path}"
        
        if recursive:
            # Listing récursif avec tree
            output, code = await run_command_async(
                f"tree -L 3 --dirsfirst {path} 2>/dev/null || find {path} -maxdepth 3 -type f",
                timeout=30
            )
            return f"Structure de {path}:\n{output}"
        else:
            # Listing simple avec ls
            output, code = await run_command_async(
                f"ls -la {path}",
                timeout=10
            )
            return f"Contenu de {path}:\n{output}"
            
    except Exception as e:
        return f"❌ Erreur listing: {str(e)}"


@register_tool("search_files")
async def search_files(params: dict) -> str:
    """Rechercher des fichiers par pattern"""
    pattern = params.get("pattern", "")
    path = params.get("path", ".")
    
    if not pattern:
        return "Erreur: pattern de recherche requis"
    
    output, code = await run_command_async(
        f"find {path} -name '{pattern}' -type f 2>/dev/null | head -50",
        timeout=30
    )
    
    if not output.strip():
        return f"Aucun fichier trouvé pour '{pattern}' dans {path}"
    
    return f"Fichiers trouvés ({pattern}):\n{output}"


@register_tool("file_info")
async def file_info(params: dict) -> str:
    """Obtenir des informations détaillées sur un fichier"""
    path = params.get("path", "")
    
    if not path:
        return "Erreur: chemin requis"
    
    if not os.path.exists(path):
        return f"❌ Fichier non trouvé: {path}"
    
    output, code = await run_command_async(
        f"stat {path} && file {path}",
        timeout=10
    )
    
    return f"Informations sur {path}:\n{output}"
