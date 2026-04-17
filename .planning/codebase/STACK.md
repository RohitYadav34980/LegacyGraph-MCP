# Stack — LegacyGraph-MCP

Detailed breakdown of the technology stack, languages, and core dependencies.

## Core Language
- **Python 3.11+**: Primary implementation language.
- **C++**: Target language for analysis (supported via tree-sitter).

## Primary Frameworks & Libraries
| Category | Library | Purpose |
|---|---|---|
| **MCP** | `mcp` / `fastmcp` | Model Context Protocol server implementation. |
| **Parsing** | `tree-sitter` | Incremental AST parsing. |
| **Parsing** | `tree-sitter-cpp` | C++ grammar for tree-sitter. |
| **Graph** | `networkx` | Directed graph data structure for dependency tracking. |
| **Git** | `gitpython` | Repository cloning and management. |
| **Server** | `uvicorn` | ASGI server for HTTP/SSE transport. |
| **Web** | `starlette` | Lightweight ASGI framework for routing. |

## Development & Build Tools
- **Poetry**: Dependency management and packaging.
- **Pytest**: Unit and integration testing framework.
- **Mypy**: Strict static type checking.
- **Black**: Opinionated code formatting.
- **Ruff**: Modern Python linter and formatter.
- **Smithery**: MCP server packaging and distribution.

## CI/CD & Deployment
- **GitHub Actions**: Potential for automated testing and releases.
- **Render**: Infrastructure for cloud-mode deployment.
