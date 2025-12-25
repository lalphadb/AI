"""
Exécution asynchrone des commandes système
Résout le problème de Blocking I/O avec subprocess.run

AI Orchestrator v4.0
"""

import asyncio
import logging
from typing import Tuple, Dict, List, Optional

logger = logging.getLogger(__name__)


async def run_command_async(
    command: str,
    timeout: int = 60,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None
) -> Tuple[str, int]:
    """
    Exécute une commande shell de manière asynchrone.
    
    Args:
        command: Commande à exécuter
        timeout: Timeout en secondes (défaut: 60)
        cwd: Répertoire de travail (optionnel)
        env: Variables d'environnement (optionnel)
    
    Returns:
        Tuple (output: str, return_code: int)
        - return_code = 0 pour succès
        - return_code = -1 pour timeout
        - return_code = -2 pour erreur d'exécution
    """
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            # Décoder les sorties
            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ''
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ''
            
            # Combiner stdout et stderr
            output = stdout_str
            if stderr_str:
                output += f"\n[STDERR]\n{stderr_str}" if output else stderr_str
            
            return output or "(aucune sortie)", process.returncode or 0
            
        except asyncio.TimeoutError:
            # Tuer le processus si timeout
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
            logger.warning(f"Timeout ({timeout}s) pour: {command[:50]}...")
            return f"⏱️ Commande interrompue après {timeout}s", -1
            
    except Exception as e:
        logger.error(f"Erreur exécution commande: {e}")
        return f"❌ Erreur d'exécution: {str(e)}", -2


async def run_multiple_commands(
    commands: Dict[str, str],
    timeout: int = 10
) -> Dict[str, str]:
    """
    Exécute plusieurs commandes en parallèle.
    
    Args:
        commands: Dict {nom: commande}
        timeout: Timeout par commande
    
    Returns:
        Dict {nom: output}
    """
    async def run_one(name: str, cmd: str) -> Tuple[str, str]:
        output, code = await run_command_async(cmd, timeout=timeout)
        return name, output
    
    tasks = [run_one(name, cmd) for name, cmd in commands.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    output_dict = {}
    for result in results:
        if isinstance(result, Exception):
            continue
        name, output = result
        output_dict[name] = output
    
    return output_dict


async def run_ssh_command(
    host: str,
    command: str,
    key_path: str = None,
    user: str = "root",
    timeout: int = 30
) -> Tuple[str, int]:
    """
    Exécute une commande via SSH de manière asynchrone.
    
    Args:
        host: Hôte distant
        command: Commande à exécuter
        key_path: Chemin de la clé SSH (optionnel)
        user: Utilisateur SSH (défaut: root)
        timeout: Timeout en secondes
    
    Returns:
        Tuple (output, return_code)
    """
    ssh_opts = "-o StrictHostKeyChecking=no -o ConnectTimeout=10"
    
    if key_path:
        ssh_cmd = f"ssh {ssh_opts} -i {key_path} {user}@{host} '{command}'"
    else:
        ssh_cmd = f"ssh {ssh_opts} {user}@{host} '{command}'"
    
    return await run_command_async(ssh_cmd, timeout=timeout)
