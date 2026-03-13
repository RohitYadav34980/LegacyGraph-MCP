# LegacyGraph-MCP: Agentic C++ Modernization 🏗️

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Enabled-green.svg)](https://modelcontextprotocol.io/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![smithery badge](https://smithery.ai/badge/labsofuniverse/legacy-mcp-analyzer)](https://smithery.ai/servers/labsofuniverse/legacy-mcp-analyzer)

## ⚡ The Problem
Legacy modernization using standard LLMs fails because:
1.  **Lost Context:** "Spaghetti code" (intertwined dependencies) cannot fit in a context window.
2.  **Hallucinations:** Agents refactor functions without knowing upstream dependencies, causing breakage.
3.  **Text vs. Logic:** Regex-based parsers miss nuances in C++ macros and templates.

## 🛠️ The Solution
**LegacyGraph-MCP** is a Model Context Protocol (MCP) server that exposes a C++ codebase as a **Knowledge Graph** to AI Agents.

Instead of reading text, the Agent queries the structure:
> *"Agent: Which functions call `calculate_risk()`?"*
> 
> *"MCP: `process_loan()` and `assess_credit()`"*

### Features
* **AST Parsing:** Uses `tree-sitter` for 100% accurate C++ parsing (no Regex).
* **Graph RAG:** Detects **Circular Dependencies** before refactoring begins.
* **Universal Compatibility:** Works with Claude Desktop, DeepSeek-Coder, and any MCP client.

---

## 🚀 Quick Start

### 1. Install
```bash
git clone https://github.com/RohitYadav34980/LegacyGraph-MCP.git
cd LegacyGraph-MCP
poetry install
```

### 2. Run Server

By default, running this in a normal terminal starts **Streamable HTTP** for easy local development.

```bash
# Streamable HTTP (recommended for hosted / URL-based usage)
poetry run python -m src.server --transport streamable-http --path /mcp
```
```bash
# Legacy SSE (only if a client explicitly requires SSE)
poetry run python -m src.server --transport sse --path /mcp
```

#### Deploying on Render (or any PaaS)
The HTTP server binds to `0.0.0.0:$PORT` automatically (Render sets `PORT`).

### 3. Verify Installation
```bash
poetry run python tools/verifier.py
```

Expected output: **100% accuracy** on dependency detection.

---

## � Installing in your MCP Client

### Option 1: Install via Smithery (Recommended)

To install LegacyGraph-MCP for Claude Desktop automatically via [Smithery](https://legacy-mcp-analyzer--labsofuniverse.run.tools):

```bash
npx -y @smithery/cli@latest mcp add labsofuniverse/legacy-mcp-analyzer --client claude-code
```

### Option 2: Manual Configuration

1. Clone the repository and install dependencies:
```bash
git clone https://github.com/RohitYadav34980/LegacyGraph-MCP.git
cd LegacyGraph-MCP
poetry install
```

2. Add the following to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "legacy-mcp-analyzer": {
      "command": "poetry",
      "args": ["run", "python", "-m", "src.server"],
      "cwd": "/path/to/LegacyGraph-MCP"
    }
  }
}
```

Replace `/path/to/LegacyGraph-MCP` with the actual path to your cloned directory.

---

## �📊 Architecture

```mermaid
graph LR
    A[AI Agent] -->|JSON-RPC| B[MCP Server]
    B -->|Parse| C[tree-sitter]
    B -->|Query| D[NetworkX Graph]
    C -->|AST| D
    D -->|Cycles/Deps| B
```

### Three-Layer Design
1. **Ingestion Layer** (`src/parser.py`): Tree-sitter-based C++ parsing
2. **Graph Layer** (`src/graph.py`): NetworkX dependency graph
3. **Interface Layer** (`src/server.py`): MCP tool exposure

---

## 🔧 MCP Tools

| Tool                | Description                          | Example Query                       |
|---------------------|--------------------------------------|-------------------------------------|
| `analyze_codebase`  | Parses C++ and builds graph          | Analyze entire project              |
| `get_callers`       | Find upstream dependencies           | Who calls `validate()`?             |
| `get_callees`       | Find downstream dependencies         | What does `init()` call?            |
| `detect_cycles`     | Identify circular dependencies       | Are there any loops?                |
| `get_orphan_functions` | Find unused code                  | Which functions are never called?   |

---

## 🧪 Testing

### Run All Tests
```bash
poetry run pytest
```

### Run Verifier (Integration Test)
```bash
poetry run python tools/verifier.py
```

Verifies against a sample legacy C++ project in `data/legacy_project/`.

**Current Accuracy:** 100% (10/10 dependencies + cycle detection + orphan detection)

---

## 🤝 Contributing

1. **Fork & Clone**
2. **Create Feature Branch:** `git checkout -b feature/your-feature`
3. **Follow Standards:**
   - Strict `mypy` typing
   - Google-style docstrings
   - Conventional commits (e.g., `feat: add template parsing`)
4. **Test:** Ensure `pytest` passes
5. **Submit PR**

---

## 📚 Documentation

- **[Project Manual](PROJECT_MANUAL.md)**: In-depth guide and API reference
- **[Implementation Plan](https://github.com/RohitYadav34980/LegacyGraph-MCP/tree/main)**: Original design decisions

---

## 🙏 Acknowledgments

Built with:
- [tree-sitter](https://tree-sitter.github.io/tree-sitter/) - Incremental parsing
- [NetworkX](https://networkx.org/) - Graph algorithms
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol

---

**Made with ❤️** 
