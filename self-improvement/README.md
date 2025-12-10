# 🧠 Self-Improvement Module v1.0

> **Module d'auto-amélioration pour infrastructure IA**
> **Date** : 6 décembre 2025

---

## 🎯 Objectif

Ce module analyse automatiquement les métriques système et génère des recommandations d'amélioration en utilisant le LLM local (Qwen/DeepSeek).

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Self-Improvement Module v1.0                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Collecteur  │───▶│  Analyseur   │───▶│   Rapport    │  │
│  │  Métriques   │    │  IA (Qwen)   │    │    JSON      │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                    │          │
│         ▼                   ▼                    ▼          │
│  • Prometheus API    • Pattern Analysis   • Health Score   │
│  • Docker Stats      • Anomaly Detection  • Issues List    │
│  • Logs (Loki)       • Recommendations    • Optimizations  │
│  • GPU/CPU Usage                          • Summary        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Installation

```bash
cd /home/lalpha/projets/ai-tools/self-improvement
./setup.sh
```

---

## 📋 Utilisation

### Analyse Complète
```bash
python3 analyzer.py
```

### Analyse Rapide (sans logs)
```bash
python3 analyzer.py --quick
```

---

## 📊 Métriques Collectées

| Métrique | Source | Description |
|----------|--------|-------------|
| CPU Usage | Prometheus | Utilisation CPU moyenne |
| Memory Usage | Prometheus | Utilisation RAM |
| Disk System | Prometheus | Espace disque système |
| Disk Ollama | Prometheus | Espace disque modèles |
| GPU Usage | DCGM Exporter | Utilisation GPU |
| GPU Memory | DCGM Exporter | Mémoire GPU |
| Docker Containers | Docker CLI | Nombre de conteneurs |
| Network Traffic | Prometheus | Trafic réseau |
| Error Count | Loki | Erreurs dans les logs (24h) |

---

## 📝 Format du Rapport

```json
{
    "timestamp": "2025-12-06T...",
    "version": "1.0.0",
    "metrics": { ... },
    "containers": [ ... ],
    "logs": { ... },
    "analysis": {
        "health_score": 85,
        "status": "healthy",
        "issues": [
            {
                "severity": "low|medium|high|critical",
                "component": "...",
                "description": "...",
                "recommendation": "..."
            }
        ],
        "optimizations": [
            {
                "type": "performance|cost|security|maintenance",
                "description": "...",
                "impact": "low|medium|high",
                "effort": "low|medium|high"
            }
        ],
        "summary": "..."
    }
}
```

---

## ⏰ Automatisation

Le cron job exécute l'analyse tous les jours à 6h00 :

```
0 6 * * * /usr/bin/python3 /home/lalpha/projets/ai-tools/self-improvement/analyzer.py
```

Logs cron : `cron.log`

---

## 📁 Structure

```
self-improvement/
├── analyzer.py      # Script principal
├── setup.sh         # Installation
├── README.md        # Cette doc
├── cron.log         # Logs d'exécution
└── reports/         # Rapports JSON
    └── report_YYYYMMDD_HHMMSS.json
```

---

## 🔧 Configuration

Variables d'environnement :

| Variable | Défaut | Description |
|----------|--------|-------------|
| PROMETHEUS_URL | http://localhost:9090 | URL Prometheus |
| OLLAMA_URL | http://localhost:11434 | URL Ollama |
| LOKI_URL | http://localhost:3100 | URL Loki |
| MODEL | qwen2.5-coder:32b | Modèle LLM |

---

## 🔗 Intégrations Futures

- [ ] Notifications Slack/Discord
- [ ] Dashboard Grafana dédié
- [ ] Auto-apply pour certaines optimisations
- [ ] Historique et tendances
- [ ] Comparaison avec baseline

---

*Module créé le 6 décembre 2025*
