#!/usr/bin/env python3
"""
🎰 Poker Assistant Temps Réel
Analyse tes mains de poker en temps réel avec IA vision.
Fallback automatique: Groq (rapide) → Gemini (backup) → Claude (précis)
"""

import os
import sys
import time
import base64
import threading
from queue import Queue
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Tuple
import json

# Capture d'écran
try:
    from mss import mss
    import cv2
    import numpy as np
except ImportError:
    print("❌ Installe les dépendances: pip install mss opencv-python numpy")
    sys.exit(1)

# APIs (optionnelles selon ce que tu utilises)
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️  Groq non disponible (pip install groq)")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️  Gemini non disponible (pip install google-generativeai)")

try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    print("⚠️  Claude non disponible (pip install anthropic)")


@dataclass
class AnalysisResult:
    """Résultat d'une analyse"""
    provider: str
    latency_ms: int
    advice: str
    timestamp: datetime
    success: bool
    error: Optional[str] = None


class PokerAnalyzer:
    """Gestionnaire des APIs avec fallback automatique"""
    
    POKER_PROMPT = """Analyse cette capture d'écran de poker. Réponds en français, format ULTRA COURT:

📍 Position: [ta position]
🃏 Main: [tes 2 cartes]
🎴 Board: [cartes communes ou "Preflop"]
💰 Pot: [montant]
❓ Action à toi: [montant à suivre]

✅ DÉCISION: [FOLD / CALL / RAISE X]
📊 Raison: [1 phrase max]

Si l'image n'est pas une table de poker, dis-le simplement."""

    def __init__(self):
        self.groq_client = None
        self.gemini_model = None
        self.claude_client = None
        self._init_clients()
        
    def _init_clients(self):
        """Initialise les clients API disponibles"""
        # Groq (le plus rapide)
        if GROQ_AVAILABLE and os.getenv("GROQ_API_KEY"):
            try:
                self.groq_client = Groq()
                print("✅ Groq initialisé")
            except Exception as e:
                print(f"⚠️  Erreur Groq: {e}")
        
        # Gemini (backup rapide)
        if GEMINI_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
            try:
                genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
                print("✅ Gemini initialisé")
            except Exception as e:
                print(f"⚠️  Erreur Gemini: {e}")
        
        # Claude (précis)
        if CLAUDE_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
            try:
                self.claude_client = anthropic.Anthropic()
                print("✅ Claude initialisé")
            except Exception as e:
                print(f"⚠️  Erreur Claude: {e}")
    
    def _encode_image(self, frame: np.ndarray, quality: int = 85) -> str:
        """Encode une image en base64"""
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return base64.standard_b64encode(buffer).decode('utf-8')
    
    def analyze_with_groq(self, frame: np.ndarray) -> AnalysisResult:
        """Analyse avec Groq (Llama Vision) - Le plus rapide ~100-200ms"""
        if not self.groq_client:
            return AnalysisResult("groq", 0, "", datetime.now(), False, "Client non disponible")
        
        start = time.time()
        try:
            base64_image = self._encode_image(frame)
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.POKER_PROMPT},
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
            return AnalysisResult("groq", latency, advice, datetime.now(), True)
            
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return AnalysisResult("groq", latency, "", datetime.now(), False, str(e))
    
    def analyze_with_gemini(self, frame: np.ndarray) -> AnalysisResult:
        """Analyse avec Gemini Flash - Rapide ~200-400ms"""
        if not self.gemini_model:
            return AnalysisResult("gemini", 0, "", datetime.now(), False, "Client non disponible")
        
        start = time.time()
        try:
            # Gemini accepte directement les images PIL
            from PIL import Image
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            
            response = self.gemini_model.generate_content(
                [self.POKER_PROMPT, pil_image],
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=300,
                    temperature=0.3
                )
            )
            
            latency = int((time.time() - start) * 1000)
            advice = response.text
            return AnalysisResult("gemini", latency, advice, datetime.now(), True)
            
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return AnalysisResult("gemini", latency, "", datetime.now(), False, str(e))
    
    def analyze_with_claude(self, frame: np.ndarray) -> AnalysisResult:
        """Analyse avec Claude - Plus lent mais précis ~500-1000ms"""
        if not self.claude_client:
            return AnalysisResult("claude", 0, "", datetime.now(), False, "Client non disponible")
        
        start = time.time()
        try:
            base64_image = self._encode_image(frame)
            
            response = self.claude_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_image
                            }
                        },
                        {"type": "text", "text": self.POKER_PROMPT}
                    ]
                }]
            )
            
            latency = int((time.time() - start) * 1000)
            advice = response.content[0].text
            return AnalysisResult("claude", latency, advice, datetime.now(), True)
            
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return AnalysisResult("claude", latency, "", datetime.now(), False, str(e))
    
    def analyze(self, frame: np.ndarray) -> AnalysisResult:
        """Analyse avec fallback automatique: Groq → Gemini → Claude"""
        
        # 1. Essayer Groq (le plus rapide)
        if self.groq_client:
            result = self.analyze_with_groq(frame)
            if result.success:
                return result
            print(f"⚠️  Groq échec: {result.error}, fallback...")
        
        # 2. Essayer Gemini (backup rapide)
        if self.gemini_model:
            result = self.analyze_with_gemini(frame)
            if result.success:
                return result
            print(f"⚠️  Gemini échec: {result.error}, fallback...")
        
        # 3. Essayer Claude (toujours fiable)
        if self.claude_client:
            result = self.analyze_with_claude(frame)
            if result.success:
                return result
            print(f"⚠️  Claude échec: {result.error}")
        
        return AnalysisResult("none", 0, "", datetime.now(), False, "Aucune API disponible")


class ScreenCapture:
    """Gestionnaire de capture d'écran"""
    
    def __init__(self, region: dict = None):
        self.region = region or {'top': 100, 'left': 100, 'width': 1000, 'height': 700}
        self.last_frame = None
        
    def capture(self) -> np.ndarray:
        """Capture la zone définie"""
        with mss() as sct:
            screenshot = sct.grab(self.region)
            frame = np.array(screenshot)
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    
    def has_changed(self, frame: np.ndarray, threshold: float = 0.02) -> bool:
        """Détecte si l'écran a changé significativement"""
        if self.last_frame is None:
            self.last_frame = frame.copy()
            return True
        
        # Redimensionner pour comparaison rapide
        small_new = cv2.resize(frame, (100, 100))
        small_old = cv2.resize(self.last_frame, (100, 100))
        
        diff = cv2.absdiff(small_new, small_old)
        change_ratio = np.sum(diff) / diff.size / 255
        
        if change_ratio > threshold:
            self.last_frame = frame.copy()
            return True
        return False
    
    def select_region_interactive(self) -> dict:
        """Sélection interactive de la zone à capturer"""
        print("\n🎯 Sélection de la zone de capture...")
        print("   1. Une fenêtre va s'ouvrir avec ton écran")
        print("   2. Dessine un rectangle autour de ta table de poker")
        print("   3. Appuie sur ENTER pour confirmer, ESC pour annuler\n")
        
        with mss() as sct:
            # Capture écran complet
            monitor = sct.monitors[1]  # Écran principal
            screenshot = sct.grab(monitor)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            # Redimensionner pour affichage
            scale = 0.5
            small = cv2.resize(frame, None, fx=scale, fy=scale)
            
            # Sélection ROI
            roi = cv2.selectROI("Sélectionne la zone poker (ENTER=ok, ESC=annuler)", 
                               small, fromCenter=False, showCrosshair=True)
            cv2.destroyAllWindows()
            
            if roi[2] > 0 and roi[3] > 0:
                self.region = {
                    'top': int(roi[1] / scale),
                    'left': int(roi[0] / scale),
                    'width': int(roi[2] / scale),
                    'height': int(roi[3] / scale)
                }
                print(f"✅ Zone sélectionnée: {self.region}")
            else:
                print("❌ Sélection annulée, utilisation zone par défaut")
        
        return self.region


class PokerAssistant:
    """Application principale"""
    
    def __init__(self):
        self.analyzer = PokerAnalyzer()
        self.capture = ScreenCapture()
        self.running = False
        self.paused = False
        self.stats = {'total': 0, 'groq': 0, 'gemini': 0, 'claude': 0}
        
    def print_header(self):
        """Affiche l'en-tête"""
        print("\n" + "="*60)
        print("🎰  POKER ASSISTANT TEMPS RÉEL")
        print("="*60)
        print("Commandes clavier:")
        print("  [SPACE] Pause/Reprendre")
        print("  [R]     Re-sélectionner zone")
        print("  [Q]     Quitter")
        print("="*60 + "\n")
    
    def print_result(self, result: AnalysisResult):
        """Affiche le résultat d'analyse"""
        provider_colors = {
            'groq': '🟢',
            'gemini': '🔵', 
            'claude': '🟣'
        }
        
        icon = provider_colors.get(result.provider, '⚪')
        
        print("\n" + "─"*60)
        print(f"{icon} {result.provider.upper()} | ⏱️  {result.latency_ms}ms | {result.timestamp.strftime('%H:%M:%S')}")
        print("─"*60)
        print(result.advice)
        print("─"*60)
        
        self.stats['total'] += 1
        self.stats[result.provider] = self.stats.get(result.provider, 0) + 1
    
    def run(self, auto_select: bool = True):
        """Boucle principale"""
        self.print_header()
        
        # Sélection zone
        if auto_select:
            self.capture.select_region_interactive()
        
        print("\n🚀 Démarrage de l'analyse...")
        print("   (L'analyse se déclenche automatiquement quand l'écran change)\n")
        
        self.running = True
        check_interval = 0.3  # Vérifie toutes les 300ms
        
        # Thread pour les commandes clavier (optionnel)
        def keyboard_listener():
            try:
                import keyboard
                keyboard.on_press_key('space', lambda _: setattr(self, 'paused', not self.paused))
                keyboard.on_press_key('q', lambda _: setattr(self, 'running', False))
                keyboard.on_press_key('r', lambda _: self.capture.select_region_interactive())
            except ImportError:
                pass  # keyboard module optionnel
        
        threading.Thread(target=keyboard_listener, daemon=True).start()
        
        try:
            while self.running:
                if self.paused:
                    time.sleep(0.5)
                    continue
                
                # Capture
                frame = self.capture.capture()
                
                # Vérifie si changement
                if self.capture.has_changed(frame, threshold=0.015):
                    print("\n🔄 Changement détecté, analyse en cours...")
                    
                    # Analyse avec fallback
                    result = self.analyzer.analyze(frame)
                    
                    if result.success:
                        self.print_result(result)
                    else:
                        print(f"❌ Échec analyse: {result.error}")
                
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\n\n👋 Arrêt demandé...")
        
        # Stats finales
        print("\n" + "="*60)
        print("📊 STATISTIQUES SESSION")
        print("="*60)
        print(f"Total analyses: {self.stats['total']}")
        for provider in ['groq', 'gemini', 'claude']:
            if self.stats.get(provider, 0) > 0:
                print(f"  {provider}: {self.stats[provider]}")
        print("="*60 + "\n")


def check_api_keys():
    """Vérifie les clés API configurées"""
    print("\n🔑 Vérification des clés API...")
    
    keys = {
        'GROQ_API_KEY': GROQ_AVAILABLE,
        'GOOGLE_API_KEY': GEMINI_AVAILABLE,
        'ANTHROPIC_API_KEY': CLAUDE_AVAILABLE
    }
    
    available = []
    for key, lib_available in keys.items():
        value = os.getenv(key)
        if value and lib_available:
            print(f"  ✅ {key}: Configurée")
            available.append(key)
        elif value and not lib_available:
            print(f"  ⚠️  {key}: Clé présente mais librairie manquante")
        else:
            print(f"  ❌ {key}: Non configurée")
    
    if not available:
        print("\n❌ Aucune API configurée!")
        print("Configure au moins une clé API:")
        print("  export GROQ_API_KEY='...'")
        print("  export GOOGLE_API_KEY='...'")
        print("  export ANTHROPIC_API_KEY='...'")
        return False
    
    return True


def main():
    """Point d'entrée"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Poker Assistant Temps Réel')
    parser.add_argument('--no-select', action='store_true', 
                        help='Skip interactive region selection')
    parser.add_argument('--region', type=str, 
                        help='Region as JSON: {"top":100,"left":100,"width":800,"height":600}')
    args = parser.parse_args()
    
    # Vérification API
    if not check_api_keys():
        sys.exit(1)
    
    # Création assistant
    assistant = PokerAssistant()
    
    # Region personnalisée
    if args.region:
        try:
            assistant.capture.region = json.loads(args.region)
            print(f"📐 Région: {assistant.capture.region}")
        except json.JSONDecodeError:
            print("❌ Format région invalide")
            sys.exit(1)
    
    # Lancement
    assistant.run(auto_select=not args.no_select and not args.region)


if __name__ == "__main__":
    main()
