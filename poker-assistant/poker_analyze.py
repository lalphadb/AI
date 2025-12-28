#!/usr/bin/env python3
"""
🎰 Poker Analyzer - Version manuelle
Analyse des screenshots de poker envoyés en argument
"""

import os
import sys
import time
import base64
from datetime import datetime

try:
    import cv2
    import numpy as np
except ImportError:
    print("❌ pip install opencv-python numpy")
    sys.exit(1)

try:
    from groq import Groq
except ImportError:
    print("❌ pip install groq")
    sys.exit(1)


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
    
    # Vérifier la clé API
    if not os.getenv("GROQ_API_KEY"):
        return "❌ GROQ_API_KEY non configurée"
    
    # Charger l'image
    if not os.path.exists(image_path):
        return f"❌ Fichier non trouvé: {image_path}"
    
    frame = cv2.imread(image_path)
    if frame is None:
        return f"❌ Impossible de lire l'image: {image_path}"
    
    # Encoder en base64
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    base64_image = base64.standard_b64encode(buffer).decode('utf-8')
    
    # Appel Groq
    start = time.time()
    try:
        client = Groq()
        response = client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": POKER_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }],
            max_tokens=300,
            temperature=0.3
        )
        
        latency = int((time.time() - start) * 1000)
        advice = response.choices[0].message.content
        
        return f"""
{'─'*60}
🟢 GROQ | ⏱️  {latency}ms | {datetime.now().strftime('%H:%M:%S')}
{'─'*60}
{advice}
{'─'*60}
"""
        
    except Exception as e:
        return f"❌ Erreur Groq: {e}"


def main():
    if len(sys.argv) < 2:
        print("""
🎰 Poker Analyzer - Analyse de screenshots

Usage:
  python poker_analyze.py <image.png>
  python poker_analyze.py screenshot.jpg
  
Exemple:
  python poker_analyze.py ~/Desktop/poker_hand.png
""")
        sys.exit(0)
    
    image_path = sys.argv[1]
    print(f"\n🔄 Analyse de {image_path}...")
    result = analyze_image(image_path)
    print(result)


if __name__ == "__main__":
    main()
