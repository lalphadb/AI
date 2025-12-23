#!/usr/bin/env python3
"""
MCP Bridge pour l'AI Orchestrator 4LB.ca
Permet à l'orchestrateur d'utiliser les outils du serveur MCP externe
"""

import httpx
import asyncio
import json
from typing import Optional, Dict, Any

# URL du serveur MCP
MCP_SERVER_URL = "http://localhost:8888"

class MCPClient:
    """Client pour appeler les outils du serveur MCP"""
    
    def __init__(self, base_url: str = MCP_SERVER_URL):
        self.base_url = base_url
        self.session_id = None
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> str:
        """
        Appelle un outil sur le serveur MCP via HTTP
        
        Args:
            tool_name: Nom de l'outil (ex: 'read_file', 'write_file')
            arguments: Dictionnaire des arguments
        
        Returns:
            Résultat de l'outil en string
        """
        if arguments is None:
            arguments = {}
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Appel direct via l'endpoint tools du serveur MCP
                response = await client.post(
                    f"{self.base_url}/tools/{tool_name}",
                    json=arguments
                )
                
                if response.status_code == 200:
                    return response.text
                else:
                    return f"❌ Erreur MCP ({response.status_code}): {response.text}"
                    
        except httpx.ConnectError:
            return f"❌ Serveur MCP non disponible sur {self.base_url}"
        except Exception as e:
            return f"❌ Erreur MCP: {str(e)}"
    
    async def list_tools(self) -> list:
        """Liste les outils disponibles sur le serveur MCP"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/tools")
                if response.status_code == 200:
                    return response.json()
                return []
        except Exception as e:
            print(f"Erreur listing outils MCP: {e}")
            return []


# Instance globale
mcp_client = MCPClient()


# Fonctions utilitaires pour l'orchestrateur
async def mcp_read_file(path: str, lines: int = 0) -> str:
    """Lire un fichier via MCP"""
    return await mcp_client.call_tool("read_file", {"path": path, "lines": lines})


async def mcp_write_file(path: str, content: str, backup: bool = True) -> str:
    """Écrire un fichier via MCP"""
    return await mcp_client.call_tool("write_file", {
        "path": path, 
        "content": content, 
        "backup": backup
    })


async def mcp_patch_file(path: str, old_text: str, new_text: str) -> str:
    """Modifier un fichier via MCP (search/replace)"""
    return await mcp_client.call_tool("patch_file", {
        "path": path,
        "old_text": old_text,
        "new_text": new_text
    })


async def mcp_run_command(command: str, cwd: str = "/home/lalpha") -> str:
    """Exécuter une commande via MCP"""
    return await mcp_client.call_tool("run_command", {
        "command": command,
        "cwd": cwd
    })


async def mcp_docker_restart(container: str) -> str:
    """Redémarrer un container via MCP"""
    return await mcp_client.call_tool("docker_restart", {"container": container})


async def mcp_git_commit(repo_path: str, message: str) -> str:
    """Créer un commit via MCP"""
    return await mcp_client.call_tool("git_commit", {
        "repo_path": repo_path,
        "message": message
    })


# Test rapide
if __name__ == "__main__":
    async def test():
        print("Test MCP Bridge...")
        result = await mcp_client.call_tool("get_system_status", {})
        print(result)
    
    asyncio.run(test())
