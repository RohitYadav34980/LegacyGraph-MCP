# Integrations — LegacyGraph-MCP

Documentation of external systems, protocols, and integration points.

## Model Context Protocol (MCP)
- **Stdio Transport**: Default for local use (e.g., Claude Desktop).
- **HTTP/SSE Transport**: Used for cloud deployments and remote clients.
- **Tools**: Exposes resources (indirectly via tools) and tool definitions for codebase analysis.

## Source Control
- **Git**: Integrated via `GitPython` for cloning remote repositories during ingestion.
- **Local Filesystem**: Supports scanning local directories and reading raw files provided as JSON.

## Deployment Platforms
- **Smithery.ai**: Registered as a benchmarked MCP server.
- **Render**: Primary target for cloud-mode hosting.

## Security Integrations
- **JSON Serialization**: Replaced unsafe legacy pickle caching with secure JSON-based storage (`.legacygraph.json`).
- **Resource Constraints**: Supports benchmark profiles for low-spec environment optimization.
