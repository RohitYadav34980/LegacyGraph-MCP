import os
from pathlib import Path
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

# ============================================================
# Persistence (Phase 3)
# ============================================================
# Anchor path relative to this file's installation directory so it remains
# stable regardless of the working directory when the process is invoked.
_SRC_ROOT = Path(__file__).resolve().parent.parent.parent
LEGACYGRAPH_CACHE_ROOT: str = str(_SRC_ROOT / "data" / "cache")

# HF Bucket URL — must be set explicitly via environment variable
# to enable cloud serialization. 
# An empty string is provided as the intentional safe default to prevent 
# accidental writes to a developer's personal bucket or unintended syncing.
HF_BUCKET_URL: str = os.environ.get("HF_BUCKET_URL", "")
