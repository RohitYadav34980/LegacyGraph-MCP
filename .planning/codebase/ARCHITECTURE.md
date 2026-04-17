# Architecture — LegacyGraph-MCP

High-level design and data flow of the LegacyGraph-MCP system.

## Layered Design
1. **MCP Interface Layer (`server.py`, `tools/`)**: Handles JSON-RPC communication, tool registration, and mode-based capability switching.
2. **Business Logic Layer (`core/`)**:
    - **Parser (`parser.py`)**: Uses tree-sitter to extract function definitions and call sites from C++.
    - **Graph (`graph.py`)**: Manages a NetworkX directed graph representing function-level dependencies.
3. **Infrastructure Layer (`utils/`)**: Provides configuration management, logging, global services (singletons), and helper functions for git/filesystem operations.

## Key Component Interaction
- **Ingestion**: `tools/analysis.py` → `utils/helpers.py` → `core/parser.py` → `core/graph.py`.
- **Querying**: `tools/queries.py` → `utils/services.py` → `core/graph.py`.

## Design Principles
- **Separation of Concerns**: Core logic is independent of the MCP framework.
- **Dependency Direction**: `tools` → `utils` → `core`. Strict avoidance of circular dependencies.
- **Thin Server**: `server.py` is dedicated to registration and routing, delegating work to tool components.
- **Testability**: Core modules are designed to be tested in isolation without spawning an MCP server.
