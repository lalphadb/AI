"""
🧠 Mémoire Persistante - Agent 4LB v2
SQLite + ChromaDB (vectorielle)
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
MEMORY_DIR = BASE_DIR / "memory"
MEMORY_DIR.mkdir(exist_ok=True)


class AgentMemory:
    """
    Système de mémoire hybride:
    - SQLite: conversations, tâches, faits
    - ChromaDB: recherche sémantique (optionnel)
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(MEMORY_DIR / "agent_memory.db")
        self._init_db()
        self.chroma_client = None
        
    def _init_db(self):
        """Initialiser la base SQLite"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Conversations
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    task TEXT NOT NULL,
                    messages TEXT,
                    result TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Faits appris
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    source TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, key)
                );
                
                -- Workflows (pour n8n)
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    trigger TEXT,
                    steps TEXT,
                    schedule TEXT,
                    enabled INTEGER DEFAULT 1,
                    last_run TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Logs d'actions
                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT,
                    action TEXT NOT NULL,
                    input TEXT,
                    output TEXT,
                    success INTEGER,
                    duration_ms INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Index
                CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category);
                CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
                CREATE INDEX IF NOT EXISTS idx_action_logs_conv ON action_logs(conversation_id);
            """)
    
    # === CONVERSATIONS ===
    
    def save_conversation(self, conv_id: str, task: str, messages: List[Dict], 
                         result: str = None, status: str = "pending"):
        """Sauvegarder une conversation"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO conversations (id, task, messages, result, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (conv_id, task, json.dumps(messages), result, status, datetime.now().isoformat()))
    
    def get_conversation(self, conv_id: str) -> Optional[Dict]:
        """Récupérer une conversation"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (conv_id,)
            ).fetchone()
            if row:
                return {
                    "id": row[0], "task": row[1], "messages": json.loads(row[2] or "[]"),
                    "result": row[3], "status": row[4], "created_at": row[5]
                }
        return None
    
    def get_recent_conversations(self, limit: int = 10) -> List[Dict]:
        """Récupérer les conversations récentes"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, task, status, created_at FROM conversations ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [{"id": r[0], "task": r[1], "status": r[2], "created_at": r[3]} for r in rows]
    
    # === KNOWLEDGE ===
    
    def store_fact(self, category: str, key: str, value: str, 
                  confidence: float = 1.0, source: str = None):
        """Stocker un fait"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO knowledge (category, key, value, confidence, source)
                VALUES (?, ?, ?, ?, ?)
            """, (category, key, value, confidence, source))
    
    def get_fact(self, category: str, key: str) -> Optional[str]:
        """Récupérer un fait"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM knowledge WHERE category = ? AND key = ?",
                (category, key)
            ).fetchone()
            return row[0] if row else None
    
    def get_facts_by_category(self, category: str) -> List[Dict]:
        """Récupérer tous les faits d'une catégorie"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT key, value, confidence FROM knowledge WHERE category = ?",
                (category,)
            ).fetchall()
            return [{"key": r[0], "value": r[1], "confidence": r[2]} for r in rows]
    
    def search_knowledge(self, query: str) -> List[Dict]:
        """Rechercher dans la base de connaissances"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT category, key, value FROM knowledge 
                WHERE key LIKE ? OR value LIKE ?
                LIMIT 20
            """, (f"%{query}%", f"%{query}%")).fetchall()
            return [{"category": r[0], "key": r[1], "value": r[2]} for r in rows]
    
    # === ACTION LOGS ===
    
    def log_action(self, conv_id: str, action: str, input_data: Dict,
                   output: str, success: bool, duration_ms: int = 0):
        """Logger une action"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO action_logs (conversation_id, action, input, output, success, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (conv_id, action, json.dumps(input_data), output, int(success), duration_ms))
    
    def get_action_stats(self) -> Dict[str, Any]:
        """Statistiques des actions"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Total actions
            stats["total"] = conn.execute("SELECT COUNT(*) FROM action_logs").fetchone()[0]
            
            # Succès/échecs
            stats["success"] = conn.execute(
                "SELECT COUNT(*) FROM action_logs WHERE success = 1"
            ).fetchone()[0]
            
            # Par action
            rows = conn.execute("""
                SELECT action, COUNT(*), AVG(duration_ms), SUM(success) 
                FROM action_logs GROUP BY action
            """).fetchall()
            stats["by_action"] = [
                {"action": r[0], "count": r[1], "avg_duration_ms": r[2], "success_count": r[3]}
                for r in rows
            ]
            
            return stats
    
    # === CHROMADB (optionnel) ===
    
    def init_chroma(self, host: str = "localhost", port: int = 8000):
        """Initialiser ChromaDB pour recherche sémantique"""
        try:
            import chromadb
            self.chroma_client = chromadb.HttpClient(host=host, port=port)
            logger.info("ChromaDB connecté")
        except Exception as e:
            logger.warning(f"ChromaDB non disponible: {e}")
    
    def semantic_search(self, query: str, collection: str = "agent_memory", n: int = 5) -> List[Dict]:
        """Recherche sémantique via ChromaDB"""
        if not self.chroma_client:
            return []
        try:
            coll = self.chroma_client.get_or_create_collection(collection)
            results = coll.query(query_texts=[query], n_results=n)
            return [
                {"id": r, "document": d, "distance": dist}
                for r, d, dist in zip(
                    results["ids"][0], 
                    results["documents"][0], 
                    results["distances"][0]
                )
            ]
        except Exception as e:
            logger.error(f"Erreur recherche ChromaDB: {e}")
            return []


# Instance globale
memory = AgentMemory()
