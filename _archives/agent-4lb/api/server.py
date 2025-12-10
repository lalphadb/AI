"""
🌐 API REST FastAPI pour Agent 4LB
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import time
import uuid

from core.config import AGENT_NAME, OLLAMA_HOST, OLLAMA_MODEL, API_HOST, API_PORT
from core.agent import Agent4LB
from memory.persistent import PersistentMemory

app = FastAPI(title=f"{AGENT_NAME} API", version="1.0.0",
              description="API REST pour l'Agent IA Autonome 4LB")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

memory = PersistentMemory()
sessions: Dict[str, Agent4LB] = {}

class TaskRequest(BaseModel):
    task: str
    verbose: bool = False
    llm: str = "ollama"

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class TaskResponse(BaseModel):
    task_id: int
    result: str
    iterations: int
    duration: float
    status: str

@app.get("/")
async def root():
    return {"name": AGENT_NAME, "version": "1.0.0", "status": "running",
            "endpoints": ["/status", "/run", "/chat", "/history", "/memory/stats"]}

@app.get("/status")
async def status():
    import requests
    try:
        ollama_ok = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5).status_code == 200
    except: ollama_ok = False
    stats = memory.get_stats()
    return {"agent": AGENT_NAME, "ollama": {"host": OLLAMA_HOST, "model": OLLAMA_MODEL, "status": "ok" if ollama_ok else "error"},
            "memory": stats, "active_sessions": len(sessions)}

@app.post("/run", response_model=TaskResponse)
async def run_task(req: TaskRequest):
    start = time.time()
    task_id = memory.save_task(req.task)
    try:
        agent = Agent4LB(llm=req.llm)
        result = agent.run(req.task, verbose=req.verbose)
        memory.complete_task(task_id, result[:5000], agent.iteration_count)
        return TaskResponse(task_id=task_id, result=result, iterations=agent.iteration_count,
                           duration=round(time.time() - start, 2), status="completed")
    except Exception as e:
        memory.fail_task(task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    if session_id not in sessions: sessions[session_id] = Agent4LB()
    memory.save_message(session_id, "user", req.message)
    response = sessions[session_id].chat(req.message)
    memory.save_message(session_id, "assistant", response)
    return {"session_id": session_id, "response": response}

@app.get("/history")
async def history(limit: int = 20):
    return {"tasks": memory.get_task_history(limit)}

@app.get("/memory/stats")
async def memory_stats():
    return memory.get_stats()

@app.get("/memory/knowledge")
async def get_knowledge(category: str = None):
    return {"knowledge": memory.get_knowledge(category=category)}

@app.post("/memory/knowledge")
async def save_knowledge(category: str, key: str, value: str, confidence: float = 1.0):
    memory.save_knowledge(category, key, value, confidence)
    return {"status": "saved", "key": key}

@app.get("/sessions")
async def list_sessions():
    return {"active": list(sessions.keys()), "count": len(sessions)}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in sessions: del sessions[session_id]
    return {"status": "deleted", "session_id": session_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
