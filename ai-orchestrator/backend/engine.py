"""
Moteur ReAct v5.0 - Robuste et fonctionnel
"""

import re
import httpx
from typing import Optional
from fastapi import WebSocket
from config import get_settings

settings = get_settings()
MAX_ITERATIONS = 10

def extract_final_answer(text: str) -> Optional[str]:
    """Extraire final_answer - ROBUSTE"""
    
    # Méthode 1: Triple quotes
    for pattern in [r"final_answer\s*\(\s*answer\s*=\s*'''(.+?)'''",
                    r'final_answer\s*\(\s*answer\s*=\s*"""(.+?)"""']:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            return m.group(1).strip()
    
    # Méthode 2: Guillemets simples/doubles
    m = re.search(r'final_answer\s*\(\s*answer\s*=\s*["\'](.+?)["\']', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    
    # Méthode 3: Fallback - tout après answer=
    if "final_answer" in text and "answer=" in text:
        idx = text.find("answer=")
        if idx >= 0:
            content = text[idx + 7:].strip()
            for q in ['"""', "'''", '"', "'"]:
                if content.startswith(q):
                    content = content[len(q):]
                    break
            content = re.sub(r'["\')]+\s*$', '', content)
            if content and len(content) > 5:  # Éviter les réponses trop courtes
                return content.strip()
    
    return None


def extract_action(text: str) -> tuple:
    """Extraire action tool(params)"""
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('ACTION:'):
            line = line[7:].strip()
        
        m = re.match(r'(\w+)\s*\((.*)?\)', line)
        if m:
            tool = m.group(1)
            params_str = m.group(2) or ""
            params = {}
            for pm in re.finditer(r'(\w+)\s*=\s*["\']([^"\']*)["\']', params_str):
                params[pm.group(1)] = pm.group(2)
            return tool, params
    
    # Fallback
    m = re.search(r'(\w+)\s*\(\s*(\w+)\s*=\s*["\']([^"\']+)["\']', text)
    if m:
        return m.group(1), {m.group(2): m.group(3)}
    
    return None, {}


async def react_loop(
    user_message: str,
    model: str,
    conversation_id: str,
    execute_tool_func,
    uploaded_files: list = None,
    websocket: WebSocket = None
):
    """Boucle ReAct"""
    
    from tools import get_tools_description
    tools_desc = get_tools_description()
    
    files_info = ""
    if uploaded_files:
        files_info = "\n\nFichiers attachés:\n"
        for f in uploaded_files:
            files_info += f"- {f['filename']} (ID: {f['id']})\n"
    
    # Prompt SANS exemple qui peut être copié
    system_prompt = f"""Tu es un assistant IA expert. Tu DOIS utiliser les outils pour répondre aux questions.

OUTILS:
{tools_desc}
{files_info}

RÈGLES:
1. Pour CHAQUE question, utilise d'abord un outil approprié
2. Après avoir obtenu les informations, conclus avec: final_answer(answer="[ton analyse des résultats]")
3. Ne réponds JAMAIS sans avoir d'abord utilisé un outil

EXEMPLES DE FORMAT:
- docker_status() pour voir les containers
- system_info() pour les infos système  
- execute_command(command="ls -la") pour exécuter une commande
- final_answer(answer="Voici ce que j'ai trouvé: ...") pour conclure"""

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
                "message": f"Réflexion {iteration}/{MAX_ITERATIONS}"
            })
        
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"{settings.ollama_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": 0.3, "num_predict": 2000}
                    },
                    timeout=180
                )
                data = r.json()
                assistant_text = data.get("message", {}).get("content", "")
        except Exception as e:
            error = f"Erreur LLM: {e}"
            if websocket:
                await websocket.send_json({"type": "error", "message": error})
            return error
        
        last_response = assistant_text
        
        # Vérifier final_answer
        final = extract_final_answer(assistant_text)
        if final:
            if websocket:
                await websocket.send_json({
                    "type": "complete",
                    "answer": final,
                    "iterations": iteration,
                    "model": model
                })
            return final
        
        # Chercher une action
        tool_name, params = extract_action(assistant_text)
        
        if tool_name and tool_name != "final_answer":
            if websocket:
                await websocket.send_json({
                    "type": "tool",
                    "tool": tool_name,
                    "params": params
                })
            
            result = await execute_tool_func(tool_name, params, uploaded_files)
            
            if websocket:
                await websocket.send_json({
                    "type": "result",
                    "tool": tool_name,
                    "result": result[:500]
                })
            
            messages.append({"role": "assistant", "content": assistant_text})
            
            if iteration >= MAX_ITERATIONS - 1:
                messages.append({"role": "user", "content": f"RÉSULTAT: {result[:1000]}\n\n🚨 RÉPONDS MAINTENANT avec final_answer(answer=\"[résumé des résultats]\")"})
            else:
                messages.append({"role": "user", "content": f"RÉSULTAT: {result}\n\nAnalyse ce résultat et réponds avec final_answer(answer=\"[ton analyse]\") ou utilise un autre outil si nécessaire."})
        else:
            # Pas d'action - forcer l'utilisation d'un outil
            messages.append({"role": "assistant", "content": assistant_text})
            messages.append({"role": "user", "content": "Tu DOIS utiliser un outil. Choisis parmi: docker_status(), system_info(), execute_command(command=\"...\"), etc."})
    
    # Timeout - retourner la dernière réponse
    fallback = f"Analyse après {MAX_ITERATIONS} itérations:\n\n{last_response[:1500]}"
    if websocket:
        await websocket.send_json({
            "type": "complete",
            "answer": fallback,
            "iterations": MAX_ITERATIONS,
            "model": model
        })
    return fallback
