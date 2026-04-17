"""
Entry point for LegacyGraph-MCP.

Usage:
    python -m src [--mode local|cloud] [--transport stdio|streamable-http|sse] [--path /mcp]
"""

import argparse
import os

from src.utils.logger import logger
import src.utils.config as config



def main() -> None:
    parser = argparse.ArgumentParser(description="LegacyGraph-MCP server")
    parser.add_argument(
        "--mode",
        choices=["local", "cloud"],
        default=None,
        help=(
            "Deployment mode. 'local' = stdio + disk access; "
            "'cloud' = HTTP + ephemeral clones. "
            "Auto-detected from --transport if not set. "
            "Override with MCP_MODE env var."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "sse", "stdio"],
        default=None,
        help="Transport protocol. Defaults to stdio (local) or streamable-http (cloud).",
    )
    parser.add_argument(
        "--path",
        default="/mcp",
        help="Mount path for HTTP/SSE transports (FastMCP mount_path).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to listen on for HTTP/SSE transports.",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind to for HTTP/SSE transports.",
    )
    args = parser.parse_args()

    # ---- Resolve mode --------------------------------------------
    # Priority: explicit --mode > MCP_MODE env > auto-detect from transport
    if args.mode is not None:
        config.MCP_MODE = args.mode
    elif os.environ.get("MCP_MODE"):
        config.MCP_MODE = os.environ["MCP_MODE"]
    elif args.transport in ("streamable-http", "sse"):
        # HTTP transport almost certainly means cloud / remote hosting
        config.MCP_MODE = "cloud"
    else:
        config.MCP_MODE = "local"

    os.environ["MCP_MODE"] = config.MCP_MODE

    # ---- Resolve transport ----------------------------------------
    transport = args.transport
    if transport is None:
        transport = "stdio" if config.MCP_MODE == "local" else "streamable-http"

    # ---- Run Server ----------------------------------------------
    # Update environment variables so server.py picks them up during initialization
    if args.port is not None:
        os.environ["PORT"] = str(args.port)
    if args.host is not None:
        os.environ["MCP_HOST"] = args.host

    # Lazy import so environment variables take effect
    from src.server import mcp, _register_tools

    # ---- Register tools based on mode ----------------------------
    _register_tools(config.MCP_MODE)

    logger.info(f"Starting LegacyGraph-MCP  mode={config.MCP_MODE}  transport={transport}")
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "streamable-http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="sse", mount_path=args.path)


if __name__ == "__main__":
    main()
