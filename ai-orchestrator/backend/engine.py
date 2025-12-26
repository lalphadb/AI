"""
Moteur ReAct pour AI Orchestrator
Contient la logique principale de la boucle de raisonnement (Think/Plan/Act)
"""

import re
import json
import httpx
from typing import Optional, List, Dict, Any
from fastapi import WebSocket

from config import get_settings
from prompts import build_system_prompt, PROMPTS_ENABLED
from dynamic_context import get_dynamic_context, DYNAMIC_CONTEXT_ENABLED
from tools import get_tools_description

# Configuration
settings = get_settings()
MAX_ITERATIONS = settings.max_iterations

# ===== PARSING DES ACTIONS =====

def parse_action(text: str) -> tuple:
    """Parser une action du format: tool_name(param="value")"""
    text = text.strip()
    
    # CAS SPECIAL: final_answer
    if "final_answer" in text:
        # Support des triple quotes avec regex pour gérer les espaces
        triple_match = re.search(r'answer\s*=\s*"""(.*?) """', text, re.DOTALL)
        if triple_match:
            content = triple_match.group(1)
            content = content.replace('\\n', '\n')
            return "final_answer", {"answer": content.strip()}

        # Support des triple quotes méthode manuelle (fallback)
        if '"""' in text:
            start_marker = '"""'
            start_idx = text.find(start_marker)
            if start_idx != -1:
                end_idx = text.rfind(start_marker)
                if end_idx > start_idx:
                    content = text[start_idx + 3 : end_idx]
                    content = content.replace('\\n', '\n')
                    return "final_answer", {"answer": content.strip()}

        # Méthode 1: Chercher answer="..." avec guillemets doubles
        match = re.search(r'final_answer\s*\(\s*answer\s*=\s*"(.*)"?\s*\)?$', text, re.DOTALL)
        if match:
            answer = match.group(1)
            answer = answer.rstrip()
            while answer and answer[-1] in ')"\'':
                answer = answer[:-1]
            answer = answer.rstrip()
            answer = answer.replace('\\n', '\n')
            return "final_answer", {"answer": answer}
        
        # Méthode 2: Chercher après answer=" jusqu'à la fin
        idx = text.find('answer="')
        if idx >= 0:
            content_start = idx + 8
            content = text[content_start:]
            last_quote_paren = content.rfind('"')
            if last_quote_paren != -1:
                content = content[:last_quote_paren]
            elif content.endswith('"'):
                content = content[:-1]
            if content.startswith('""'):
                content = content[2:]
            content = content.replace('\\n', '\n')
            return "final_answer", {"answer": content.strip()}
        
        # Méthode 3: guillemets simples
        idx = text.find("answer='")
        if idx >= 0:
            content_start = idx + 8
            content = text[content_start:]
            content = content.rstrip()
            if content.endswith("')"):
                content = content[:-2]
            elif content.endswith("'"):
                content = content[:-1]
            content = content.rstrip()
            if content.endswith('"') :
                content = content[:-1]
            elif content.endswith("')"):
                content = content[:-2]
            elif content.endswith("'"):
                content = content[:-1]
            return "final_answer", {"answer": content.strip()}
    
    # Pattern standard pour les autres outils
    match = re.search(r'(\w+)\s*\(([^)]*)\)', text)
    if not match:
        return None, {}
    
    tool_name = match.group(1)
    params_str = match.group(2)
    
    params = {}
    if params_str.strip():
        for m in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', params_str):
            params[m.group(1)] = m.group(2)
        for m in re.finditer(r"(\w+)\s*=\s*'([^']*)'", params_str):
            params[m.group(1)] = m.group(2)
    
    return tool_name, params

# ===== BOUCLE REACT =====

async def react_loop(
    user_message: str,
    model: str,
    conversation_id: str,
    execute_tool_func,  # Fonction injectée pour éviter import circulaire
    uploaded_files: list = None,
    websocket: WebSocket = None
):
    """Boucle ReAct principale"""
    
    # Construire le contexte des fichiers uploadés
    files_context = ""
    if uploaded_files:
        files_context = "\n\nFichiers attachés par l'utilisateur:\n"
        for f in uploaded_files:
            files_context += f"- ID: {f['id']} | Nom: {f['filename']} | Type: {f['filetype']}\n"
        files_context += "\nUtilise analyze_file(file_id=\"...\") ou analyze_image(image_id=\"...\") pour les examiner.\n"
    
    # Prompt système
    tools_desc = get_tools_description()
    
    if PROMPTS_ENABLED:
        dynamic_ctx = ""
        if DYNAMIC_CONTEXT_ENABLED:
            dynamic_ctx = await get_dynamic_context()
        system_prompt = build_system_prompt(tools_desc, files_context, dynamic_ctx)
    else:
        system_prompt = f"""Tu es un assistant IA expert.
Outils disponibles:
{tools_desc}
{files_context}
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": user_message})
    
    iterations = 0
    
    while iterations < MAX_ITERATIONS:
        iterations += 1
        
        # Envoyer le statut via WebSocket
        if websocket:
            await websocket.send_json({
                "type": "thinking",
                "iteration": iterations,
                "message": f"Itération {iterations}/{MAX_ITERATIONS}..."
            })
        
        # Appeler le LLM
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.ollama_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 2000
                        }
                    },
                    timeout=180
                )
                data = response.json()
                assistant_text = data.get("message", {}).get("content", "")
        except Exception as e:
            error_msg = f"Erreur LLM: {str(e)}"
            if websocket:
                await websocket.send_json({"type": "error", "message": error_msg})
            return error_msg
        
        # Envoyer la réponse partielle
        if websocket:
            await websocket.send_json({
                "type": "step",
                "iteration": iterations,
                "content": assistant_text
            })
        
        # Chercher une action
        lines = assistant_text.split('\n')
        action_line = None
        for line in lines:
            if line.strip().startswith('ACTION:'):
                action_line = line.replace('ACTION:', '').strip()
                break
            if re.match(r'^\w+\(.*\)\s*$', line.strip()):
                action_line = line.strip()
                break
        
        if not action_line:
            match = re.search(r'(\w+)\s*\([^)]+\)', assistant_text)
            if match:
                action_line = match.group(0)
        
        if action_line:
            tool_name, params = parse_action(action_line)
            
            if tool_name:
                if tool_name == "final_answer":
                    final = params.get("answer", assistant_text)
                    if websocket:
                        await websocket.send_json({
                            "type": "complete",
                            "answer": final,
                            "iterations": iterations,
                            "model": model
                        })
                    return final
                
                # Exécuter l'outil
                if websocket:
                    await websocket.send_json({
                        "type": "tool",
                        "tool": tool_name,
                        "params": params
                    })
                
                result = await execute_tool_func(tool_name, params, uploaded_files)
                
                # Ajouter au contexte
                messages.append({"role": "assistant", "content": assistant_text})
                
                # Message d'urgence progressive
                if iterations >= MAX_ITERATIONS - 1:
                    msg = f"RÉSULTAT: {result[:500]}\n\n🚨 DERNIER TOUR! Réponds MAINTENANT: final_answer(answer=\"résumé\")"
                elif iterations >= MAX_ITERATIONS - 3:
                    msg = f"RÉSULTAT: {result[:800]}\n\n⚠️ Conclus bientôt avec final_answer()"
                else:
                    msg = f"RÉSULTAT: {result}\n\nContinue ou conclus avec final_answer()."
                
                messages.append({"role": "user", "content": msg})
                
                if websocket:
                    await websocket.send_json({
                        "type": "result",
                        "tool": tool_name,
                        "result": result[:1000]
                    })
            else:
                messages.append({"role": "assistant", "content": assistant_text})
                messages.append({"role": "user", "content": "Format ACTION invalide."})
        else:
            messages.append({"role": "assistant", "content": assistant_text})
            messages.append({"role": "user", "content": "Continue avec une ACTION ou final_answer()."})
    
    timeout_msg = f"Analyse interrompue après {MAX_ITERATIONS} itérations."
    if websocket:
        await websocket.send_json({
            "type": "complete",
            "answer": timeout_msg,
            "iterations": iterations,
            "model": model
        })
    return timeout_msg
