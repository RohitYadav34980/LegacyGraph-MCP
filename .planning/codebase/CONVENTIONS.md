# Conventions — LegacyGraph-MCP

Development standards and architectural constraints.

## Coding Style
- **Formatter**: Black (88 character line limit).
- **Linter**: Ruff.
- **Typing**: Strict Mypy compliance (`strict = true`).
- **Docstrings**: Google-style documentation required for all public functions/classes.

## Architectural Constraints
- **Dependency Flow**: `tools` → `utils` → `core`.
- **Statelessness**: Core components should be stateless where possible; global state is managed via `utils/services.py` singletons.
- **Error Handling**: 
    - Internal errors should use custom exceptions (`ParseError`, `GraphError`).
    - MCP tools must catch exceptions and return human-readable error strings rather than crashing the server.

## Git & Commits
- **Workflow**: Feature branches (`feature/`, `fix/`, `docs/`).
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) required.
- **Versioning**: Semantic Versioning (SemVer) followed in `pyproject.toml`.

## Tool Exposure
- Tools are conditionally registered based on the `MCP_MODE` (local vs cloud).
- Local-only tools (like disk export) must be hidden in cloud mode.
