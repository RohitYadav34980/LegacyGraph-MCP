# LegacyGraph-MCP: Agentic C++ Modernization 🏗️

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Enabled-green.svg)](https://modelcontextprotocol.io/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![smithery badge](https://smithery.ai/badge/labsofuniverse/legacy-mcp-analyzer)](https://smithery.ai/servers/labsofuniverse/legacy-mcp-analyzer)

## ⚡ The Problem

Legacy C++ codebases are too large for LLM context windows, leading to:
1. **Lost Context** – spaghetti code cannot be processed in one pass.
2. **Hallucinations** – agents refactor without full dependency awareness.
3. **Parsing Gaps** – regex‑based parsers miss macros and templates.

## 🛠️ The Solution

**LegacyGraph‑MCP** is a Model Context Protocol (MCP) server that exposes a C++ codebase as a **knowledge graph**. Agents query the graph instead of raw text:
> *"Agent: Which functions call `calculate_risk()`?"*
> *"MCP: `process_loan()` and `assess_credit()`"*

### Core Features
- **Accurate AST parsing** via `tree‑sitter` – 100 % C++ syntax coverage.
- **Graph‑RAG** – detects circular dependencies before refactoring.
- **Hybrid deployment** – local (stdio) or cloud (HTTP) with a single codebase.
- **Universal MCP client support** – works with Claude Desktop, DeepSeek‑Coder, etc.
- **Omni‑ingestion** – clone repos, apply patches, upload raw files, or scan local directories.
- **Token‑safe visualisation** – Mermaid diagrams returned inline (cloud) or saved to disk (local).

---

## 📊 Performance (LLVM – 67 k files)

LegacyGraph‑MCP now uses **JSON** for cache files (`.legacygraph.json`) instead of unsafe pickle, and supports a constrained‑resource benchmark profile.

| Metric | Sequential (v0.1) | Distributed (v0.3) | ⚡ Improvement |
|---|---|---|---|
| **CPU Utilisation** | `~6 % (1 core)` | `~80 % dynamic cores` | Adaptive |
| **AST Build Time** | `5 h` | `10 min` | `≈30×` |
| **Throughput** | `3.8 files/s` | `113 files/s` | `≈30×` |
| **Incremental Updates** | N/A | `< 1 s` | Instant |

---

## 📐 Architecture

```
src/
├── __init__.py            # package root
├── __main__.py            # CLI entry point (python -m src)
├── server.py              # MCP registration & server card
│
├── core/                  # business logic
│   ├── graph.py           # NetworkX dependency graph model
│   └── parser.py          # tree‑sitter C++ parser
│
├── tools/                 # MCP tool functions
│   ├── analysis.py        # analyze_codebase (ingestion)
│   ├── queries.py         # get_callers, get_callees, detect_cycles …
│   └── export.py          # Mermaid graph generation & export
│
└── utils/                 # cross‑cutting infrastructure
    ├── config.py          # MCP_MODE, CPP_EXTENSIONS
    ├── logger.py          # centralized logging
    ├── services.py        # singletons (graph, parser)
    └── helpers.py         # git clone, directory scanning, Mermaid builder
```

```mermaid
graph LR
    A[AI Agent] -->|JSON‑RPC| B[MCP Server]
    B -->|Parse| C[tree‑sitter]
    B -->|Query| D[NetworkX Graph]
    C -->|AST| D
    D -->|Cycles/Deps| B
    E{MCP_MODE} -->|local| F[stdio + Disk]
    E -->|cloud| G[HTTP + /tmp/ Clone]
```

> 📖 See `ARCHITECTURE.md` for detailed component diagrams.

---

## 🚀 Quick Start

### 1. Install
```bash
git clone https://github.com/RohitYadav34980/LegacyGraph-MCP.git
cd LegacyGraph-MCP
pip install poetry && poetry install
```

### 2. Run Server
#### Local (CLI / Claude Desktop)
```bash
python -m src --mode local
```
#### Cloud (Smithery / Render)
```bash
python -m src --mode cloud
```
#### Override Transport (optional)
```bash
# Force streamable‑http in local mode
python -m src --mode local --transport streamable-http
# Force SSE in cloud mode
python -m src --mode cloud --transport sse --path /mcp
```

### 3. Verify Installation
```bash
python -m pytest tests/ -v
python tools/verifier.py
```
Expected output: **100 % accuracy** on dependency detection.

---

## 🔌 Installing in Your MCP Client
### Option 1 – Smithery (recommended)
```bash
npx -y @smithery/cli@latest mcp add labsofuniverse/legacy-mcp-analyzer --client claude-code
```
### Option 2 – Manual configuration
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "legacy-mcp-analyzer": {
      "command": "python",
      "args": ["-m", "src", "--mode", "local"],
      "cwd": "/path/to/LegacyGraph-MCP"
    }
  }
}
```

---

## 🔧 MCP Tools
| Tool | Description | Mode |
|---|---|---|
| `analyze_codebase` | Unified ingestion (repo URL, patch, raw files, or local dir) | Both |
| `get_file_functions` | List functions defined in a specific source file | Both |
| `get_file_coupling` | Cross‑file coupling report (file A → file B) | Both |
| `get_callers` | Find upstream dependencies | Both |
| `get_callees` | Find downstream dependencies | Both |
| `detect_cycles` | Identify circular dependencies | Both |
| `get_orphan_functions` | Find unused code | Both |
| `generate_mermaid_graph` | Return Mermaid diagram inline (token‑safe) | Both |
| `export_ide_graph` | Save Mermaid `.md` file to local disk | Local only |

---

## 🧪 Testing
```bash
# Unit + integration tests (≈30 cases)
python -m pytest tests/ -v
# End‑to‑end verifier against sample legacy project
python tools/verifier.py
```
**Current Accuracy:** 100 % (all dependencies, cycles, and orphan detection verified).

---

## 📚 Documentation
| Document | Description |
|---|---|
| `PROJECT_MANUAL.md` | In‑depth guide, API reference, deployment modes |
| `ARCHITECTURE.md` | Detailed architecture, data flows, component diagrams |
| `CONTRIBUTING.md` | Development standards, commit protocol, PR process |
| `CHANGELOG.md` | Version history and release notes |

---

## 🤝 Contributing
1. Fork & clone the repo.
2. Create a feature branch: `git checkout -b feature/your-feature`.
3. Follow strict `mypy` typing, Google‑style docstrings, conventional commits.
4. Run `pytest` – ensure all tests pass.
5. Submit a PR.

---

## 🙏 Acknowledgments
Built with:
- [tree‑sitter](https://tree-sitter.github.io/tree-sitter/)
- [NetworkX](https://networkx.org/)
- [MCP](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/jlowin/fastmcp)

---

**Made with ❤️**
