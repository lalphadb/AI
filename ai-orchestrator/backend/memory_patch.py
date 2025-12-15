#!/usr/bin/env python3
"""
Patch pour améliorer le système de mémoire de l'AI Orchestrator
Intègre ChromaDB pour une mémoire sémantique intelligente
"""

import re
import sys

# Lire le fichier original
with open('/home/lalpha/projets/ai-tools/ai-orchestrator/backend/main.py', 'r') as f:
    content = f.read()

# 1. Ajouter l'import ChromaDB après les autres imports
import_patch = '''import chromadb
from chromadb.config import Settings'''

# Trouver où ajouter l'import (après "from pydantic import BaseModel")
content = content.replace(
    'from pydantic import BaseModel',
    'from pydantic import BaseModel\n' + import_patch
)

# 2. Ajouter la configuration ChromaDB après UPLOAD_DIR
chromadb_config = '''
# ChromaDB pour mémoire sémantique
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "chromadb")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))

def get_chroma_client():
    """Obtenir le client ChromaDB"""
    try:
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        return client
    except Exception as e:
        print(f"Erreur ChromaDB: {e}")
        return None

def get_memory_collection():
    """Obtenir ou créer la collection de mémoire"""
    client = get_chroma_client()
    if client:
        return client.get_or_create_collection(
            name="ai_orchestrator_memory",
            metadata={"description": "Mémoire sémantique de l'AI Orchestrator"}
        )
    return None
'''

content = content.replace(
    'UPLOAD_DIR = "/data/uploads"',
    'UPLOAD_DIR = "/data/uploads"' + chromadb_config
)

# 3. Améliorer les descriptions des outils de mémoire
old_memory_store = '''    "memory_store": {
        "description": "Stocker une information en mémoire persistante",
        "parameters": {"key": "string - Clé", "value": "string - Valeur"},
        "example": "memory_store(key=\\"projet\\", value=\\"Migration Docker\\")"
    },'''

new_memory_store = '''    "memory_store": {
        "description": "IMPORTANT: Stocker une information importante en mémoire sémantique. Utilise cet outil pour mémoriser: les préférences utilisateur, les contextes de projets, les décisions importantes, les faits clés. La mémoire persiste entre les conversations!",
        "parameters": {"key": "string - Catégorie/sujet (ex: projet_actuel, preference, fait_important)", "value": "string - Information détaillée à mémoriser"},
        "example": "memory_store(key=\\"utilisateur\\", value=\\"Lalpha travaille sur un homelab IA avec Ollama et ChromaDB\\")"
    },'''

content = content.replace(old_memory_store, new_memory_store)

old_memory_recall = '''    "memory_recall": {
        "description": "Rappeler une information de la mémoire",
        "parameters": {"key": "string - Clé (ou 'all' pour tout)"},
        "example": "memory_recall(key=\\"projet\\")"
    },'''

new_memory_recall = '''    "memory_recall": {
        "description": "IMPORTANT: Rechercher dans la mémoire sémantique. Utilise 'all' pour voir toutes les mémoires récentes, ou une question/mot-clé pour une recherche sémantique. TOUJOURS utiliser au début d'une conversation pour se rappeler du contexte!",
        "parameters": {"query": "string - 'all' pour tout voir, ou question/mot-clé pour recherche sémantique"},
        "example": "memory_recall(query=\\"projets en cours\\")"
    },'''

content = content.replace(old_memory_recall, new_memory_recall)

# 4. Remplacer l'implémentation de memory_store (chercher le bloc)
old_memory_store_impl = '''        elif tool_name == "memory_store":
            key = params.get("key", "")
            value = params.get("value", "")
            if not key or not value:
                return "Erreur: clé et valeur requises"
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO memory (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
                     (key, value))
            conn.commit()
            conn.close()
            return f"Mémorisé: {key} = {value[:100]}..."'''

new_memory_store_impl = '''        elif tool_name == "memory_store":
            key = params.get("key", "")
            value = params.get("value", "")
            if not key or not value:
                return "Erreur: clé et valeur requises"
            
            # Stocker dans ChromaDB (mémoire sémantique)
            try:
                collection = get_memory_collection()
                if collection:
                    import uuid
                    memory_id = str(uuid.uuid4())[:8]
                    collection.add(
                        documents=[f"{key}: {value}"],
                        metadatas=[{"key": key, "type": "user_memory", "timestamp": datetime.now().isoformat()}],
                        ids=[f"mem_{memory_id}"]
                    )
            except Exception as e:
                print(f"Erreur ChromaDB store: {e}")
            
            # Backup dans SQLite aussi
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO memory (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
                     (key, value))
            conn.commit()
            conn.close()
            return f"✅ Mémorisé dans mémoire sémantique: {key} = {value[:100]}..."'''

content = content.replace(old_memory_store_impl, new_memory_store_impl)

# 5. Remplacer l'implémentation de memory_recall
old_memory_recall_impl = '''        elif tool_name == "memory_recall":
            key = params.get("key", "all")
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            if key == "all":
                c.execute('SELECT key, value FROM memory ORDER BY updated_at DESC LIMIT 20')
                rows = c.fetchall()
                conn.close()
                if rows:
                    return "\\n".join([f"- {r[0]}: {r[1]}" for r in rows])
                return "Aucune mémoire stockée"
            else:
                c.execute('SELECT value FROM memory WHERE key = ?', (key,))
                row = c.fetchone()
                conn.close()
                if row:
                    return row[0]
                return f"Clé non trouvée: {key}"'''

new_memory_recall_impl = '''        elif tool_name == "memory_recall":
            query = params.get("query", params.get("key", "all"))
            
            results = []
            
            # Recherche dans ChromaDB (sémantique)
            try:
                collection = get_memory_collection()
                if collection and collection.count() > 0:
                    if query == "all":
                        # Récupérer toutes les mémoires récentes
                        all_data = collection.get(limit=20, include=["documents", "metadatas"])
                        if all_data and all_data.get("documents"):
                            results.extend([f"🧠 {doc}" for doc in all_data["documents"]])
                    else:
                        # Recherche sémantique
                        search_results = collection.query(
                            query_texts=[query],
                            n_results=5,
                            include=["documents", "metadatas", "distances"]
                        )
                        if search_results and search_results.get("documents") and search_results["documents"][0]:
                            for doc, distance in zip(search_results["documents"][0], search_results["distances"][0]):
                                relevance = round((1 - distance) * 100, 1)
                                results.append(f"🧠 [{relevance}%] {doc}")
            except Exception as e:
                print(f"Erreur ChromaDB recall: {e}")
            
            # Fallback SQLite
            if not results:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                if query == "all":
                    c.execute('SELECT key, value FROM memory ORDER BY updated_at DESC LIMIT 20')
                    rows = c.fetchall()
                    results = [f"📝 {r[0]}: {r[1]}" for r in rows]
                else:
                    c.execute('SELECT key, value FROM memory WHERE key LIKE ? OR value LIKE ? ORDER BY updated_at DESC LIMIT 5',
                             (f"%{query}%", f"%{query}%"))
                    rows = c.fetchall()
                    results = [f"📝 {r[0]}: {r[1]}" for r in rows]
                conn.close()
            
            if results:
                return "\\n".join(results)
            return "Aucune mémoire trouvée. Utilise memory_store() pour créer des souvenirs."'''

content = content.replace(old_memory_recall_impl, new_memory_recall_impl)

# 6. Améliorer le prompt système (ajouter section mémoire)
old_prompt = '''system_prompt = f"""Tu es un assistant pour le serveur 4LB.ca (Ubuntu).

OUTILS:
{tools_desc}

RÈGLES:
1. UNE action par réponse: tool_name(param="valeur")
2. JAMAIS sudo (tu es déjà root)
3. Maximum 3-4 actions puis CONCLUS avec final_answer()
4. Si tu as l'info demandée, RÉPONDS IMMÉDIATEMENT
{files_context}
FORMAT:
THINK: [réflexion courte]
ACTION: outil(param="valeur")

EXEMPLES:
- "uptime" → execute_command(command="uptime") puis final_answer(answer="Le serveur...")
- "bonjour" → final_answer(answer="Bonjour! Comment puis-je aider?")
- Tâche complexe → 2-3 actions max puis final_answer avec résumé

⚠️ NE FAIS PAS plus de 4 actions. Conclus TOUJOURS avec final_answer()."""'''

new_prompt = '''system_prompt = f"""Tu es un assistant intelligent pour le serveur 4LB.ca (Ubuntu).
Tu as une MÉMOIRE PERSISTANTE qui te permet de te souvenir des conversations précédentes.

🧠 MÉMOIRE:
- AU DÉBUT de chaque conversation: utilise memory_recall(query="all") pour voir le contexte
- QUAND tu apprends quelque chose d'important: utilise memory_store() pour le mémoriser
- La mémoire est SÉMANTIQUE: tu peux chercher par concept, pas seulement par clé exacte

OUTILS:
{tools_desc}

RÈGLES:
1. UNE action par réponse: tool_name(param="valeur")
2. JAMAIS sudo (tu es déjà root)
3. Maximum 3-4 actions puis CONCLUS avec final_answer()
4. Si tu as l'info demandée, RÉPONDS IMMÉDIATEMENT
5. MÉMORISE les informations importantes sur l'utilisateur et ses projets
{files_context}
FORMAT:
THINK: [réflexion courte, incluant ce que tu te rappelles]
ACTION: outil(param="valeur")

EXEMPLES:
- Nouvelle conversation → memory_recall(query="all") pour contexte
- "Je travaille sur X" → memory_store(key="projet_actuel", value="X") puis répondre
- "uptime" → execute_command(command="uptime") puis final_answer()

⚠️ NE FAIS PAS plus de 4 actions. Conclus TOUJOURS avec final_answer()."""'''

content = content.replace(old_prompt, new_prompt)

# Écrire le fichier modifié
with open('/home/lalpha/projets/ai-tools/ai-orchestrator/backend/main.py', 'w') as f:
    f.write(content)

print("✅ Patch appliqué avec succès!")
print("Les modifications:")
print("1. Import ChromaDB ajouté")
print("2. Configuration ChromaDB ajoutée")
print("3. Outils memory_store et memory_recall améliorés")
print("4. Mémoire sémantique intégrée")
print("5. Prompt système amélioré avec instructions mémoire")
