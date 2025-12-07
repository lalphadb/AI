# 🤖 AI Tools - lalpha Infrastructure

Collection d'outils IA pour l'infrastructure lalpha-server-1.

## 📁 Structure

```
AI/
├── mcp-servers/          # Serveurs MCP pour Claude Desktop
│   ├── ubuntu-mcp/       # 12 outils système Ubuntu
│   ├── udm-pro-mcp/      # 8 outils UDM-Pro
│   ├── filesystem-mcp/   # 4 outils fichiers
│   └── chromadb-mcp/     # 9 outils vectoriels
│
├── tools/
│   ├── self-improvement/ # Module auto-amélioration
│   ├── backup-system/    # Système de backup R2
│   └── llm-tools/        # Outils LLM divers
│
└── scripts/
    └── infra-log         # CLI changelog infrastructure
```

## 🔧 MCP Servers

**33 outils** disponibles pour Claude Desktop et Continue.dev.

### Installation

```bash
cd mcp-servers/<server>
npm install
npm run build
```

### Configuration Claude Desktop

```json
{
  "mcpServers": {
    "ubuntu-mcp": {
      "command": "node",
      "args": ["/path/to/mcp-servers/ubuntu-mcp/build/index.js"]
    }
  }
}
```

## 📋 infra-log

Système CRUD pour tracker les changements infrastructure.

```bash
# Ajouter un changement
infra-log add -c docker -a deploy -m nginx -t "ssl,proxy" -d "Deploy nginx"

# Rechercher
infra-log search --tag docker

# Voir les rollbacks
infra-log rollback CHG-xxx

# Sync avec Claude Memory
infra-log sync-memory
```

## 🖥️ Serveur

- **OS**: Ubuntu 25.10
- **CPU**: AMD Ryzen 9 7900X
- **GPU**: NVIDIA RTX 5070 Ti (16GB)
- **RAM**: 64GB DDR5

## 📄 License

MIT
