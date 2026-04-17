# Requirements — LegacyGraph-MCP

Functional and technical specifications for the next evolution of LegacyGraph-MCP.

## Milestone 2: Portability & Cloud Shift (Target)

### Functional Requirements
- **Docker Support**: Containerize the MCP server to run in any OCI-compliant environment.
- **Hugging Face Spaces Support**: Support deployment to HF Spaces with appropriate metadata and port mappings (7860).
- **Persistent Caching**: Ensure `.legacygraph.json` cache files are handled correctly in a containerized environment (volumes or ephemeral strategy).
- **Unified Entrypoint**: A single Docker entrypoint that determines mode (local/cloud) based on environment variables.

### Technical Requirements
- **Multi-stage Builds**: Use multi-stage Dockerfiles to minimize image size and exclude development dependencies.
- **Environment Parity**: Ensure the server behaves identically in Docker as it does in native Python environments.
- **Dependency Isolation**: All system dependencies (libtree-sitter, etc.) must be bundled in the image.

### Non-Functional Requirements
- **Scalability**: Optimized for high-memory environments (HF Spaces) to process >1M LoC.
- **Security**: Run as a non-root user within the container.
- **Observability**: Standardized logs forwarded to STDOUT for container monitoring.
