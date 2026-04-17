# Project Baseline — LegacyGraph-MCP

Providing high-performance, portable Graph-RAG for C++ legacy codebases.

## Mission
To solve the "lost context" problem in legacy C++ analysis by exposing codebases as rich, queryable knowledge graphs that agents can interact with via MCP.

## Core Values
- **Portability**: Seamless deployment across local environments and cloud providers via Docker.
- **Scalability**: Capable of processing massive codebases (e.g., LLVM) with deterministic accuracy.
- **Accuracy**: 100% dependency detection through robust AST parsing.

## Success Metrics
- **Performance**: Analyze 50k+ files in under 10 minutes.
- **Portability**: One-command deployment to Hugging Face Spaces using Docker.
- **User Experience**: Token-safe visualization (Mermaid) for all graph queries.

## Domain Context
Legacy C++ codebases often contain circular dependencies, complex macros, and deep inclusion chains that overwhelm standard RAG systems. LegacyGraph-MCP bridges this gap by using `tree-sitter` for precise parsing and `NetworkX` for graph analytics.
