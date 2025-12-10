"""
🌐 API Gateway FastAPI - Agent 4LB v2
"""
import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ajouter le parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.graph import Agent4LBGraph
from brain.memory import AgentMemory
from tools import ALL_TOOLS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Models Pydantic ===

class TaskRequest(BaseModel):
    task: str
    context: Optional[Dict[str, Any]] = None
    max_iterations: Optional[int] = 15
    
class TaskResponse(BaseModel):
    task_id: str
    task: str
    answer: str
    iterations: int
    status: str
    error: Optional[str] = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = "ollama"

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    services: Dict[str, str]


# === Global State ===
memory = AgentMemory()
active_websockets: List[WebSocket] = []


# === Lifespan ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/Shutdown events"""
    logger.info("🚀 Agent 4LB v2 API starting...")
    # Init ChromaDB (optionnel)
    try:
        memory.init_chroma()
    except:
        logger.warning("ChromaDB non disponible")
    yield
    logger.info("👋 Agent 4LB v2 API shutting down...")


# === FastAPI App ===
app = FastAPI(
    title="Agent 4LB v2 API",
    description="API Gateway pour l'Agent IA Autonome",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En prod: limiter aux domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Routes ===

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    import requests
    
    services = {}
    
    # Check Ollama
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        services["ollama"] = "healthy" if r.status_code == 200 else "unhealthy"
    except:
        services["ollama"] = "unavailable"
    
    # Check ChromaDB
    try:
        r = requests.get("http://localhost:8000/api/v1/heartbeat", timeout=5)
        services["chromadb"] = "healthy" if r.status_code == 200 else "unhealthy"
    except:
        services["chromadb"] = "unavailable"
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="2.0.0",
        services=services
    )


@app.post("/api/task", response_model=TaskResponse)
async def run_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """Exécuter une tâche avec l'agent"""
    try:
        graph = Agent4LBGraph(tools=ALL_TOOLS)
        result = graph.run(request.task, verbose=False)
        
        # Sauvegarder en mémoire
        memory.save_conversation(
            result["task_id"],
            request.task,
            [],  # TODO: extraire messages
            result["answer"],
            result["status"]
        )
        
        return TaskResponse(**result)
    except Exception as e:
        logger.error(f"Erreur tâche: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat simple avec l'agent"""
    try:
        from brain.nodes import LLMClient
        
        llm = LLMClient()
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        # Ajouter prompt système
        tools_desc = "\n".join([f"- {n}: {f.__doc__.split('.')[0] if f.__doc__ else 'N/A'}" 
                               for n, f in ALL_TOOLS.items()])
        
        response = llm.call(messages, tools_desc)
        
        return {"response": response}
    except Exception as e:
        logger.error(f"Erreur chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations")
async def list_conversations(limit: int = 20):
    """Lister les conversations récentes"""
    return memory.get_recent_conversations(limit)


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    """Récupérer une conversation"""
    conv = memory.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")
    return conv


@app.get("/api/stats")
async def get_stats():
    """Statistiques de l'agent"""
    return {
        "actions": memory.get_action_stats(),
        "conversations": len(memory.get_recent_conversations(100)),
        "tools_count": len(ALL_TOOLS),
        "tools": list(ALL_TOOLS.keys())
    }


@app.get("/api/tools")
async def list_tools():
    """Lister les outils disponibles"""
    return {
        name: {
            "description": func.__doc__.split('.')[0] if func.__doc__ else "N/A",
            "module": func.__module__
        }
        for name, func in ALL_TOOLS.items()
    }


# === WebSocket pour streaming ===

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pour streaming temps réel"""
    await websocket.accept()
    active_websockets.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "task":
                # Exécuter une tâche avec streaming
                task = data.get("task", "")
                
                await websocket.send_json({
                    "type": "start",
                    "task": task
                })
                
                # TODO: Implémenter streaming réel
                graph = Agent4LBGraph(tools=ALL_TOOLS)
                result = graph.run(task, verbose=False)
                
                await websocket.send_json({
                    "type": "result",
                    "data": result
                })
                
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
        logger.info("WebSocket déconnecté")


# === n8n Webhooks ===

@app.post("/webhook/n8n")
async def n8n_webhook(data: Dict[str, Any]):
    """Webhook pour n8n"""
    logger.info(f"Webhook n8n reçu: {data}")
    
    action = data.get("action")
    
    if action == "run_task":
        task = data.get("task", "")
        graph = Agent4LBGraph(tools=ALL_TOOLS)
        result = graph.run(task, verbose=False)
        return result
    
    elif action == "system_check":
        from tools.system import system_info
        return {"system": system_info()}
    
    elif action == "docker_status":
        from tools.docker import docker_ps
        return {"containers": docker_ps()}
    
    return {"status": "ok", "action": action}


# === Point d'entrée ===

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8889)
