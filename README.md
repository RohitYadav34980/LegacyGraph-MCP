# LegacyGraph-MCP: Agentic C++ Modernization 🏗️

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Enabled-green.svg)](https://modelcontextprotocol.io/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## ⚡ The Problem
Legacy modernization using standard LLMs fails because:
1.  **Lost Context:** "Spaghetti code" (intertwined dependencies) cannot fit in a context window.
2.  **Hallucinations:** Agents refactor functions without knowing upstream dependencies, causing breakage.
3.  **Text vs. Logic:** Regex-based parsers miss nuances in C++ macros and templates.

## 🛠️ The Solution
**LegacyGraph-MCP** is a Model Context Protocol (MCP) server that exposes a C++ codebase as a **Knowledge Graph** to AI Agents.

Instead of reading text, the Agent queries the structure:
> *"Agent: Which functions call `calculate_risk()`?"*
> *"MCP: `process_loan()` and `assess_credit()`"*

### Features
* **AST Parsing:** Uses `tree-sitter` for 100% accurate C++ parsing (no Regex).
* **Graph RAG:** Detects **Circular Dependencies** ($A \to B \to A$) before refactoring begins.
* **Universal Compatibility:** Works with Claude Desktop, DeepSeek-Coder, and any MCP client.

## 🚀 Quick Start

### 1. Install
```bash
git clone https://github.com/RohitYadav34980/LegacyGraph-MCP.git
cd LegacyGraph-MCP
poetry install
```

### 2. Run Server
```bash
poetry run python -m src.server
```

### 3. Verify
```bash
poetry run python tools/verifier.py
```
