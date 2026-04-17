# Structure — LegacyGraph-MCP

Detailed breakdown of the file system and component responsibilities.

## Directory Root
- `src/`: Primary source code.
- `tests/`: Pytest test suite.
- `tools/`: verifier and other maintenance scripts.
- `data/`: Sample C++ snippets and test artifacts.

## `src/` Hierarchy
### `core/` (Business Logic)
- `graph.py`: `DependencyGraph` class; wraps NetworkX DiGraph. Node = function, Edge = call.
- `parser.py`: `CppParser` class; tree-sitter queries for C++ analysis.

### `tools/` (MCP Functional Entry Points)
- `analysis.py`: Ingestion logic (`analyze_codebase`).
- `queries.py`: Graph traversal logic (`get_callers`, `detect_cycles`).
- `export.py`: Visualization logic (`generate_mermaid_graph`).

### `utils/` (Cross-cutting Concerns)
- `config.py`: Environment and flag resolution.
- `logger.py`: Standardized logging format.
- `services.py`: Global singletons for Graph and Parser.
- `helpers.py`: Stateless utility functions (git, filesystem, string builders).

### `server.py`
- Main entry point for MCP registration. Defines the tool and resource surface.
