"""
Moteur ReAct v5.5 - FULL FONCTIONNEL
- THINK -> PLAN -> ACTION -> OBSERVE
- Support multi-paramètres robuste
- Intégration prompt manager v4.0
- Gestion des erreurs et retries
"""

import re
import asyncio
import httpx
import logging
from typing import Optional
from fastapi import WebSocket
from config import get_settings

logger = logging.getLogger("react_engine")
settings = get_settings()

# Configuration ReAct (depuis settings)
MAX_ITERATIONS = settings.max_iterations or 30
LLM_TIMEOUT = settings.llm_timeout or 300
DEFAULT_MODEL = settings.default_model or "qwen3-coder:480b-cloud"

logger.info(f"ReAct Engine v5.5: max_iter={MAX_ITERATIONS}, timeout={LLM_TIMEOUT}s, model={DEFAULT_MODEL}")

def extract_final_answer(text: str) -> Optional[str]:
    """Extraire final_answer - ROBUSTE v5.5"""

    # Méthode 1: Triple quotes (priorité haute) - supporte ''' et """
    for pattern in [r'final_answer\s*\(\s*answer\s*=\s*"""(.*?) যোগ্য"""', 
                    r"final_answer\s*\(\s*answer\s*=\s*'''(.*?)'''"]:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            return m.group(1).strip()

    # Méthode 2: Guillemets simples ou doubles avec support multi-lignes
    for quote in ['"', "'"]:
        # Pattern cherchant final_answer(answer='...')
        pattern = rf'final_answer\s*\(\s*answer\s*=\s*{quote}(.*?){quote}\s*\)'
        m = re.search(pattern, text, re.DOTALL)
        if m:
            return m.group(1).strip()

    # Méthode 3: Fallback - chercher final_answer et extraire le contenu
    if "final_answer" in text:
        parts = text.split("answer=")
        if len(parts) > 1:
            content = parts[-1].strip()
            if content.endswith(")") or content.endswith(");"):
                content = content.rsplit(")", 1)[0]
            if (content.startswith('"') and content.endswith('"')) or (content.startswith("'" ) and content.endswith("'" )):
                content = content[1:-1]
            return content.strip()

    return None


def extract_action(text: str) -> tuple:
    """Extraire action tool(params) - Support multi-params v5.5"""
    
    # Chercher la ligne ACTION:
    lines = text.split('\n')
    action_line = ""
    for line in lines:
        if 'ACTION:' in line.upper():
            action_line = line.split('ACTION:', 1)[1].strip()
            break
    
    if not action_line:
        # Fallback: chercher n'importe quelle ligne qui ressemble à un appel de fonction
        for line in reversed(lines):
            line = line.strip()
            if re.match(r'^\w+\(.*\)$', line) and not any(x in line for x in ['THINK:', 'PLAN:', 'OBSERVE:']):
                action_line = line
                break

    if not action_line:
        return None, {}

    # Extraction du nom de l'outil
    m_tool = re.match(r'^(\w+)\s*\(', action_line)
    if not m_tool:
        return None, {}
    
    tool_name = m_tool.group(1)
    if tool_name == "final_answer":
        return None, {}

    # Extraction des paramètres
    params = {}
    
    # Patterns pour param="valeur" (triple ou simple quotes)
    param_patterns = [
        r'(\w+)\s*=\s*"""(.*?)"""',
        r"(\w+)\s*=\s*'''(.*?)'''",
        r'(\w+)\s*=\s*"([^"]*)"',
        r"(\w+)\s*=\s*'([^']*)'"
    ]
    
    for pattern in param_patterns:
        for pm in re.finditer(pattern, action_line, re.DOTALL):
            params[pm.group(1)] = pm.group(2)
            
    # Fallback pour paramètre unique sans nom (ex: read_file("test.txt"))
    if not params and '(' in action_line:
        content = action_line[action_line.find('(')+1 : action_line.rfind(')')].strip()
        if content:
            if (content.startswith('"') and content.endswith('"')) or (content.startswith("'" ) and content.endswith("'" )):
                val = content[1:-1]
                # Mapping intelligent selon l'outil
                mapping = {"read_file": "file_path", "execute_command": "command", "memory_recall": "query"}
                params[mapping.get(tool_name, "path")] = val

    return tool_name, params


async def react_loop(
    user_message: str,
    model: str,
    conversation_id: str,
    execute_tool_func,
    uploaded_files: list = None,
    websocket: WebSocket = None
):
    """Boucle ReAct v5.5 - THINK -> PLAN -> ACTION -> OBSERVE"""
    
    from tools import get_tools_description
    from prompts import build_system_prompt, get_urgency_message
    
    # Contextes
    files_info = ""
    if uploaded_files:
        files_info = "\n## Fichiers attachés:\n"
        for f in uploaded_files:
            files_info += f"- {f['filename']} (ID: {f['id']}, type: {f['filetype']})\n"
    
    # Prompt initial
    tools_desc = get_tools_description()
    system_prompt = build_system_prompt(tools_desc, files_info)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    last_response = ""
    
    for iteration in range(1, MAX_ITERATIONS + 1):
        if websocket:
            await websocket.send_json({
                "type": "thinking",
                "iteration": iteration,
                "message": f"Réflexion {iteration}/{MAX_ITERATIONS}..."
            })
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(LLM_TIMEOUT)) as client:
                # Retry logic ROBUSTE pour les erreurs 429
                max_retries = 10
                current_model = model
                
                for retry in range(max_retries):
                    try:
                        r = await client.post(
                            f"{settings.ollama_url}/api/chat",
                            json={
                                "model": current_model,
                                "messages": messages,
                                "stream": False,
                                "options": {
                                    "temperature": 0.2,
                                    "num_predict": 4000
                                }
                            }
                        )
                        
                        if r.status_code == 429:
                            # STRATÉGIE AGRESSIVE: Si Cloud 429 -> Passage immédiat en Local
                            if "cloud" in current_model or "gemini" in current_model or "kimi" in current_model:
                                logger.warning(f"⚠️ Cloud saturé (429). Bascule IMMÉDIATE sur modèle local.")
                                if websocket:
                                    await websocket.send_json({"type": "thinking", "message": "⚠️ Cloud saturé. Passage sur modèle local..."})
                                current_model = "qwen2.5-coder:32b-instruct-q4_K_M"
                                await asyncio.sleep(1) # Petite pause technique
                                continue
                            
                            # Si on est déjà en local ou autre, on attend
                            wait_time = 5 * (2 ** retry)
                            msg = f"⚠️ Serveur occupé. Attente {wait_time}s... (Essai {retry+1}/{max_retries})"
                            logger.warning(msg)
                            if websocket:
                                await websocket.send_json({"type": "thinking", "message": msg})
                            await asyncio.sleep(wait_time)
                            continue
                            
                        # Si le modèle cloud échoue (500/404), fallback sur local
                        if r.status_code >= 500 or r.status_code == 404:
                            if "cloud" in current_model and current_model != "qwen2.5-coder:32b-instruct-q4_K_M":
                                logger.warning(f"Erreur {r.status_code} sur {current_model}. Fallback sur local.")
                                current_model = "qwen2.5-coder:32b-instruct-q4_K_M"
                                continue
                                
                        r.raise_for_status()
                        break
                    except httpx.RequestError as e:
                        logger.error(f"Network error: {e}")
                        if retry < max_retries - 1:
                            await asyncio.sleep(5)
                            continue
                        raise e

                if r.status_code == 429:
                     # Ultime tentative en local si le cloud est mort
                    if "cloud" in current_model:
                        logger.warning("Cloud HS, tentative locale forcée")
                        current_model = "qwen2.5-coder:32b-instruct-q4_K_M"
                        # ... relancer un appel simple ici ou retourner erreur
                    
                    error = "⚠️ Le serveur LLM est surchargé malgré plusieurs tentatives."
                    if websocket:
                        await websocket.send_json({"type": "error", "message": error})
                    return error

                data = r.json()
                assistant_text = data.get("message", {}).get("content", "")
        except Exception as e:
            error = f"❌ Erreur LLM: {str(e)}"
            if websocket: await websocket.send_json({"type": "error", "message": error})
            return error
        
        last_response = assistant_text
        
        # 1. Vérifier final_answer
        final = extract_final_answer(assistant_text)
        if final:
            if websocket:
                await websocket.send_json({"type": "complete", "answer": final, "iterations": iteration, "model": model})
            return final
        
        # 2. Chercher une ACTION
        tool_name, params = extract_action(assistant_text)
        
        if tool_name:
            if websocket:
                await websocket.send_json({"type": "tool", "tool": tool_name, "params": params})
            
            # EXÉCUTION
            result = await execute_tool_func(tool_name, params, uploaded_files)
            
            # Formatage ReAct OBSERVE
            observe_msg = get_urgency_message(iteration, MAX_ITERATIONS, result)
            
            if websocket:
                await websocket.send_json({"type": "result", "tool": tool_name, "result": result[:2000]})
            
            messages.append({"role": "assistant", "content": assistant_text})
            messages.append({"role": "user", "content": observe_msg})
        else:
            # Pas d'action : forcer le format
            messages.append({"role": "assistant", "content": assistant_text})
            messages.append({"role": "user", "content": "⚠️ FORMAT INCORRECT. Tu dois utiliser ACTION: outil(param='valeur') ou final_answer."})
    
    # Timeout
    fallback = f"⚠️ Limite d'itérations atteinte ({MAX_ITERATIONS}). Voici l'analyse :\n\n{last_response}"
    if websocket:
        await websocket.send_json({"type": "complete", "answer": fallback, "iterations": MAX_ITERATIONS, "model": model})
    return fallback