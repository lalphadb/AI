#!/usr/bin/env python3
"""
🎰 Poker Watcher - Surveille un dossier et analyse les nouveaux screenshots
"""

import os
import sys
import time
import base64
from datetime import datetime
from pathlib import Path

try:
    import cv2
except ImportError:
    print("❌ pip install opencv-python")
    sys.exit(1)

try:
    from groq import Groq
except ImportError:
    print("❌ pip install groq")
    sys.exit(1)

# Dossier à surveiller
WATCH_DIR = os.path.expanduser("~/poker-screenshots")

POKER_PROMPT = """Analyse cette capture d'écran de poker. Réponds en français, format ULTRA COURT:

📍 Position: [ta position]
🃏 Main: [tes 2 cartes]
🎴 Board: [cartes communes ou "Preflop"]
💰 Pot: [montant]
❓ Action à toi: [montant à suivre]

✅ DÉCISION: [FOLD / CALL / RAISE X]
📊 Raison: [1 phrase max]

Si l'image n'est pas une table de poker, dis-le simplement."""


def analyze_image(image_path: str) -> str:
    """Analyse une image avec Groq"""
    frame = cv2.imread(image_path)
    if frame is None:
        return f"❌ Impossible de lire: {image_path}"
    
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    base64_image = base64.standard_b64encode(buffer).decode('utf-8')
    
    start = time.time()
    try:
        client = Groq()
        response = client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": POKER_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }],
            max_tokens=300,
            temperature=0.3
        )
        
        latency = int((time.time() - start) * 1000)
        return f"""
{'─'*60}
🟢 GROQ | ⏱️  {latency}ms | {datetime.now().strftime('%H:%M:%S')}
{'─'*60}
{response.choices[0].message.content}
{'─'*60}
"""
    except Exception as e:
        return f"❌ Erreur: {e}"


def main():
    # Créer le dossier si nécessaire
    Path(WATCH_DIR).mkdir(parents=True, exist_ok=True)
    
    print(f"""
{'='*60}
🎰  POKER WATCHER
{'='*60}
📁 Dossier surveillé: {WATCH_DIR}

📸 Pour analyser une main:
   1. Fais un screenshot de ta table
   2. Sauvegarde-le dans {WATCH_DIR}
   3. L'analyse apparaît ici automatiquement!

💡 Raccourci Ubuntu: Shift+PrintScreen → sélection
   Sauvegarde dans: {WATCH_DIR}

Ctrl+C pour quitter
{'='*60}
""")
    
    processed = set()
    
    # Marquer les fichiers existants comme déjà traités
    for f in Path(WATCH_DIR).glob("*"):
        if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp']:
            processed.add(str(f))
    
    print(f"👀 En attente de nouveaux screenshots...\n")
    
    try:
        while True:
            for f in Path(WATCH_DIR).glob("*"):
                if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp']:
                    path = str(f)
                    if path not in processed:
                        print(f"\n🔄 Nouveau fichier détecté: {f.name}")
                        result = analyze_image(path)
                        print(result)
                        processed.add(path)
                        
                        # Notification desktop (optionnel)
                        try:
                            os.system(f'notify-send "🎰 Poker" "Analyse terminée"')
                        except:
                            pass
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n👋 Arrêt...")


if __name__ == "__main__":
    main()
