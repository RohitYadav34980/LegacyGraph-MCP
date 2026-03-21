import os
from typing import List

# ============================================================
# Deployment Mode
# ============================================================
# Resolved at startup from --mode arg, --transport hint, or MCP_MODE env var.
# "local"  → direct disk access, stdio transport, export_ide_graph available
# "cloud"  → ephemeral /tmp/ clones, HTTP transport, export_ide_graph hidden
MCP_MODE: str = os.environ.get("MCP_MODE", "local")

# C++ file extensions to scan
CPP_EXTENSIONS: List[str] = ["*.cpp", "*.c", "*.h", "*.hpp", "*.cc"]
