# Concerns — LegacyGraph-MCP

Identified risks, technical debt, and architectural concerns.

## Technical Risks
- **Parsing Precision**: `tree-sitter-cpp` is highly tolerant but may misinterpret extremely complex macros or template metaprogramming patterns compared to a full compiler (Clang/GCC).
- **Memory Usage**: Extremely large codebases (>100k functions) may result in high memory consumption for the NetworkX graph during analysis.
- **Context Windows**: While Graph-RAG mitigates this, very dense subgraphs can still overflow smaller LLM context windows when returned via MCP tools.

## Technical Debt
- **Pickle Transition**: While JSON is now the default, some legacy code paths might still reference pickle-based logic if not fully audited.
- **Singleton Pattern**: The use of singletons in `utils/services.py` simplifies tool design but makes parallelizing certain operations more complex.

## Security
- **Remote Ingestion**: Cloning arbitrary repositories in cloud mode carries risks; sub-path restrictions and timeout guards are implemented but require continuous monitoring.
- **Resource Exhaustion**: Large repos can potentially DOS a cloud instance; resource limits and chunking are used but need further hardening for multi-tenant environments.
