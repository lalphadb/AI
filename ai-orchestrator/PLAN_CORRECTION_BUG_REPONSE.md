# Plan de Correction: Réponses Incomplètes et Boucles Infinies

## 1. Diagnostic de l'Audit
**Symptôme:** Les réponses de l'IA sont coupées avec le message "Analyse après 15 itérations...".
**Fichiers incriminés:**
- `backend/engine.py` (Ligne ~158: Troncature explicite)
- `backend/config.py` (Limite d'itérations trop basse)

**Cause Racine:**
L'agent entre dans une boucle de réflexion (ReAct loop) et atteint la limite de 15 tours. Lorsqu'il atteint cette limite, le code actuel retourne une version **tronquée** (sliced) des dernières pensées de l'IA, limitée à 1500 caractères.

## 2. Actions Correctives Immédiates

### A. Supprimer la Troncature (URGENT)
Modifier `backend/engine.py` pour retourner la réponse complète en cas d'échec de la boucle.
```python
# AVANT
fallback = f"Analyse après {MAX_ITERATIONS} itérations:\n\n{last_response[:1500]}"

# APRÈS
fallback = f"⚠️ Limite d'itérations atteinte ({MAX_ITERATIONS}). Voici la dernière analyse complète :\n\n{last_response}"
```

### B. Augmenter la Capacité de Réflexion
Modifier `backend/config.py` pour doubler le nombre d'itérations autorisées pour les tâches complexes (comme les audits).
- Passer `MAX_ITERATIONS` de 15 à 30.

## 3. Améliorations de Robustesse (Moyen Terme)

### A. Détection "Soft" de la Réponse Finale
Si l'IA ne génère pas exactement `final_answer(answer="...")` mais fournit une longue explication textuelle sans appeler d'autre outil pendant 3 tours consécutifs, considérer cela comme une réponse finale pour éviter le timeout.

### B. Optimisation du Prompt Système
Renforcer les instructions dans `backend/engine.py` pour s'assurer que l'IA respecte strictement le format de sortie quand elle a fini.

## 4. Validation
- Tester avec une demande complexe ("Audit complet du dossier X").
- Vérifier que la réponse dépasse 1500 caractères sans coupure.

```