"""
LegacyGraph-MCP Server — MCP registration and server card.

This module is a thin orchestration layer. Business logic lives in
src.tools, graph model in src.core, and infrastructure in src.utils.
"""

from typing import Any, Dict, List
import os

from src.utils.logger import logger
import src.utils.config as config
from src.tools import (
    analyze_codebase,
    get_file_functions,
    get_file_coupling,
    get_callers,
    get_callees,
    detect_cycles,
    get_orphan_functions,
    generate_mermaid_graph,
    export_ide_graph,
)

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore
except ImportError:
    logger.warning("FastMCP not found. Using mock for logic verification.")

    class FastMCP:
        def __init__(self, name: str, **kwargs: Any):
            self.name = name

        def tool(self) -> Any:
            return lambda f: f

        def run(self, *args: Any, **kwargs: Any) -> None:
            logger.error(
                "Cannot start server: FastMCP dependency missing. "
                "Please `pip install fastmcp` or add it to pyproject.toml."
            )

        def custom_route(self, *args: Any, **kwargs: Any) -> Any:
            return lambda f: f


# Initialize Server with rich metadata for MCP clients / Smithery
mcp = FastMCP(
    name="legacy-mcp-analyzer",
    instructions=(
        "LegacyGraph-MCP exposes a parsed C++ call graph over MCP. "
        "1. Use analyze_codebase to ingest code and get a project_id. "
        "2. Pass the project_id to other tools to query that specific graph."
    ),
    website_url="https://github.com/RohitYadav34980/LegacyGraph-MCP",
    # Configure HTTP binding for hosted environments (e.g., Hugging Face, Render).
    host=os.environ.get("MCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("PORT", "8000")),
    streamable_http_path="/mcp",
)


# ============================================================
# Tool Registration (mode-aware)
# ============================================================

def _register_tools(mode: str) -> None:
    """
    Register MCP tools on the FastMCP instance.

    Called from __main__ AFTER the deployment mode is resolved so that
    cloud mode never exposes local-only tools like export_ide_graph.
    """
    # Always available
    mcp.tool()(analyze_codebase)
    mcp.tool()(get_file_functions)
    mcp.tool()(get_file_coupling)
    mcp.tool()(get_callers)
    mcp.tool()(get_callees)
    mcp.tool()(detect_cycles)
    mcp.tool()(get_orphan_functions)
    mcp.tool()(generate_mermaid_graph)

    # Local-only tools
    if mode == "local":
        mcp.tool()(export_ide_graph)
        logger.info("Registered local-only tool: export_ide_graph")
    else:
        logger.info("Cloud mode: export_ide_graph is NOT registered.")


# ============================================================
# Server Card
# ============================================================

@mcp.custom_route("/.well-known/mcp/server-card.json", methods=["GET"])
async def server_card(_: object) -> "JSONResponse":
    from starlette.responses import JSONResponse

    tools: List[Dict[str, str]] = [
        {
            "name": "analyze_codebase",
            "description": (
                "Ingest C++ code. Accepts repo_url (GitHub clone), "
                "raw_files (JSON array of {filename, content}), or "
                "directory_path (local only). Does NOT accept code_content."
            ),
        },
        {
            "name": "get_file_functions",
            "description": "List all functions in a file. Requires project_id for isolation.",
        },
        {
            "name": "get_file_coupling",
            "description": "Cross-file coupling report. Requires project_id for isolation.",
        },
        {
            "name": "get_callers",
            "description": "List upstream callers. Requires project_id for isolation.",
        },
        {
            "name": "get_callees",
            "description": "List downstream callees. Requires project_id for isolation.",
        },
        {
            "name": "detect_cycles",
            "description": "Detect circular dependencies. Requires project_id for isolation.",
        },
        {
            "name": "get_orphan_functions",
            "description": "List uncalled functions. Requires project_id for isolation.",
        },
        {
            "name": "generate_mermaid_graph",
            "description": "Generate inline Mermaid diagram. Requires project_id for isolation.",
        },
    ]

    # Only advertise export_ide_graph in local mode
    if config.MCP_MODE == "local":
        tools.append(
            {
                "name": "export_ide_graph",
                "description": "Save a Mermaid.js diagram to a local .md file (local mode only).",
            }
        )

    return JSONResponse(
        {
            "serverInfo": {
                "name": "legacy-mcp-analyzer",
                "version": "0.4.0",
            },
            "capabilities": {
                "modes": ["local", "cloud"],
                "currentMode": config.MCP_MODE,
            },
            "tools": tools,
            "resources": [],
            "prompts": [],
        }
    )
