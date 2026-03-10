from typing import Any, List, Dict
import argparse
import asyncio
import logging
import os
import sys
from src.parser import CppParser
from src.graph import DependencyGraph, GraphError, CircularDependencyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore
except ImportError:
    logger.warning("FastMCP not found. Using mock for logic verification.")

    class FastMCP:
        def __init__(self, name: str):
            self.name = name

        def tool(self):
            return lambda f: f

        def run(self, *args, **kwargs):
            logger.error(
                "Cannot start server: FastMCP dependency missing. "
                "Please `pip install fastmcp` or add it to pyproject.toml."
            )


# Initialize Server with rich metadata for MCP clients / Smithery
mcp = FastMCP(
    name="legacy-mcp-analyzer",
    instructions=(
        "LegacyGraph-MCP exposes a parsed C++ call graph over MCP. "
        "Use it to analyze legacy C++ codebases: build a dependency graph, "
        "inspect callers/callees, detect cycles, and find orphan functions."
    ),
    website_url="https://github.com/RohitYadav34980/LegacyGraph-MCP",
)

# Global State
# In a real persistent server, this might be a database or re-parsed per request.
# For this stateful MCP server, we'll keep a single global graph instance for simplicity
# or rebuild it if a "analyze_code" tool is called. 
# Let's assume we maintain one graph state.
graph_service = DependencyGraph()
parser_service = CppParser()


@mcp.tool()
def analyze_codebase(code_content: str) -> str:
    """
    Analyze C++ source and build the internal dependency graph.

    Call this first to populate the graph for subsequent queries.

    Args:
        code_content: The full C++ source code string.

    Returns:
        A status message indicating success and node count.
    """
    try:
        parsed_data = parser_service.parse_source(code_content)
        # Clear previous graph for this simple one-shot analysis model
        # In a multi-file scenario, we'd append or manage sessions.
        # Here we re-init for simplicity as requested by "scaffold" nature.
        global graph_service
        graph_service = DependencyGraph() 
        graph_service.build_from_parsed_data(parsed_data)
        
        node_count = len(graph_service.get_all_nodes())
        return f"Successfully analyzed codebase. Graph built with {node_count} functions."
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return f"Error analyzing codebase: {str(e)}"


@mcp.tool()
def get_callers(function_name: str) -> str:
    """
    List upstream functions that call the given function.
    """
    try:
        callers = graph_service.get_upstream_callers(function_name)
        if not callers:
            return f"Function '{function_name}' is not called by any other function."
        return f"Function '{function_name}' is called by: {', '.join(callers)}"
    except GraphError as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_callees(function_name: str) -> str:
    """
    List downstream functions that are called by the given function.
    """
    try:
        callees = graph_service.get_downstream_dependencies(function_name)
        if not callees:
            return f"Function '{function_name}' does not call any other functions."
        return f"Function '{function_name}' calls: {', '.join(callees)}"
    except GraphError as e:
        return f"Error: {str(e)}"


@mcp.tool()
def detect_cycles() -> str:
    """
    Detect circular dependencies in the current call graph.
    """
    try:
        cycles = graph_service.detect_cycles()
        if not cycles:
            return "No circular dependencies detected."
        
        cycle_strs = [" -> ".join(cycle + [cycle[0]]) for cycle in cycles]
        return f"Circular dependencies detected:\n- " + "\n- ".join(cycle_strs)
    except Exception as e:
        return f"Error detecting cycles: {str(e)}"


@mcp.tool()
def get_orphan_functions() -> str:
    """
    Identify functions that are defined but never called by any other function.
    """
    try:
        orphans = graph_service.get_orphan_functions()
        if not orphans:
            return "No orphan functions found."
        return f"Orphan functions (never called): {', '.join(orphans)}"
    except Exception as e:
        return f"Error finding orphans: {str(e)}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LegacyGraph-MCP server")
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "sse"],
        default="streamable-http",
        help="Transport to use. streamable-http is HTTP; sse is legacy.",
    )
    parser.add_argument(
        "--path",
        default="/mcp",
        help="Mount path for HTTP/SSE transports (FastMCP mount_path).",
    )
    args = parser.parse_args()

    # FastMCP's built-in `run()` binds to localhost by default, which won't be detected
    # by platforms like Render. For deployments, we expose an ASGI app and let Uvicorn
    # bind to 0.0.0.0:$PORT.
    if args.transport == "streamable-http":
        from starlette.applications import Starlette
        from starlette.middleware.cors import CORSMiddleware
        from starlette.responses import JSONResponse, PlainTextResponse
        from starlette.routing import Mount, Route
        import uvicorn

        subapp = mcp.streamable_http_app()

        async def health(_: object) -> PlainTextResponse:
            return PlainTextResponse("ok")

        async def server_card(_: object) -> JSONResponse:
            # Static server card so Smithery can skip active scanning.
            return JSONResponse(
                {
                    "serverInfo": {
                        "name": "legacy-mcp-analyzer",
                        "version": "0.1.0",
                    },
                    "tools": [
                        {
                            "name": "analyze_codebase",
                            "description": "Analyze C++ source and build the internal dependency graph.",
                        },
                        {
                            "name": "get_callers",
                            "description": "List upstream functions that call the given function.",
                        },
                        {
                            "name": "get_callees",
                            "description": "List downstream functions that are called by the given function.",
                        },
                        {
                            "name": "detect_cycles",
                            "description": "Detect circular dependencies in the current call graph.",
                        },
                        {
                            "name": "get_orphan_functions",
                            "description": "Identify functions that are defined but never called by any other function.",
                        },
                    ],
                    "resources": [],
                    "prompts": [],
                }
            )

        app = Starlette(
            routes=[
                Route("/", endpoint=health, methods=["GET", "HEAD"]),
                Route(
                    "/.well-known/mcp/server-card.json",
                    endpoint=server_card,
                    methods=["GET"],
                ),
                Mount(args.path, app=subapp),
            ]
        )

        # Allow cross-origin MCP calls (e.g., Smithery / browser-based clients).
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        port = int(os.environ.get("PORT", "8000"))
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        # SSE transport can be mounted at a custom path directly.
        mcp.run(transport="sse", mount_path=args.path)
