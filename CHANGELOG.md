# Changelog

All notable changes to LegacyGraph-MCP are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] — 2026-03-21

### Added
- **Modular sub-package architecture:** Reorganized flat `src/` into `src/core/`, `src/tools/`, and `src/utils/`
- `src/__main__.py` — Clean CLI entry point (`python -m src`)
- `ARCHITECTURE.md` — Detailed architecture documentation with Mermaid diagrams
- `CONTRIBUTING.md` — Development standards, git workflow, PR checklist
- `CHANGELOG.md` — Version history (this file)

### Changed
- `src/server.py` — Slimmed from 577 lines to ~150 lines (thin MCP registration layer)
- `src/tools/analysis.py` — `analyze_codebase` extracted from server
- `src/tools/queries.py` — Query tools (`get_callers`, `get_callees`, etc.) extracted from server
- `src/tools/export.py` — Mermaid export tools extracted from server
- `README.md` — Rewritten with updated project structure and commands
- `PROJECT_MANUAL.md` — Rewritten with updated API reference and architecture
- `tests/test_core.py` — Updated imports for new package structure
- `tools/verifier.py` — Updated imports for new package structure

### Removed
- Flat module files: `src/graph.py`, `src/parser.py`, `src/config.py`, `src/logger.py`, `src/services.py`, `src/helpers.py` (moved into sub-packages)

---

## [0.2.0] — 2026-03-20

### Added
- Hybrid cloud/local deployment (`MCP_MODE`)
- `generate_mermaid_graph` tool — inline Mermaid diagrams (cloud-friendly)
- `export_ide_graph` tool — save Mermaid to local `.md` files
- `analyze_codebase` — unified ingestion tool (repo_url, raw_files, directory_path)
- Mode-aware tool registration (`_register_tools`)
- Server card endpoint (`/.well-known/mcp/server-card.json`)
- Streamable HTTP and SSE transport support
- Auto-mode detection from `--transport` flag

### Changed
- Server now supports both `stdio` and HTTP transports
- Tool functions conditionally registered based on deployment mode

---

## [0.1.0] — 2026-01-17

### Added
- Initial release
- Tree-sitter-based C++ parser (`CppParser`)
- NetworkX dependency graph (`DependencyGraph`)
- File-aware node tagging
- MCP server with 6 core tools
- Cycle detection, orphan detection, caller/callee analysis
- Cross-file dependency analysis
- Pytest test suite (12 test cases)
- End-to-end verifier (`tools/verifier.py`)
- Sample legacy C++ project (`data/legacy_project/`)
