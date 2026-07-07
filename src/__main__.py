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
        choices=["http", "streamable-http", "sse", "stdio"],
        default=None,
        help=(
            "Transport protocol. Defaults to stdio (local) or http (cloud). "
            "'streamable-http' is accepted as an alias for 'http'."
        ),
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
    elif args.transport in ("http", "streamable-http", "sse"):
        # HTTP transport almost certainly means cloud / remote hosting
        config.MCP_MODE = "cloud"
    else:
        config.MCP_MODE = "local"

    os.environ["MCP_MODE"] = config.MCP_MODE

    # ---- Resolve transport ----------------------------------------
    transport = args.transport
    if transport is None:
        transport = "stdio" if config.MCP_MODE == "local" else "http"
    elif transport == "streamable-http":
        # FastMCP 2.x canonical name for the Streamable HTTP transport
        transport = "http"

    # ---- Resolve HTTP binding -------------------------------------
    # FastMCP 2.x takes host/port/path via run(), not the constructor.
    host = args.host or os.environ.get("MCP_HOST", "0.0.0.0")
    port = args.port if args.port is not None else int(os.environ.get("PORT", "8000"))

    from src.server import mcp, _register_tools

    # ---- Register tools based on mode ----------------------------
    _register_tools(config.MCP_MODE)

    logger.info(f"Starting LegacyGraph-MCP  mode={config.MCP_MODE}  transport={transport}")
    if transport == "stdio":
        # Banner off: keep stdio sessions clean for desktop MCP clients.
        mcp.run(transport="stdio", show_banner=False)
    elif transport == "http":
        mcp.run(transport="http", host=host, port=port, path=args.path)
    else:
        # SSE fallback (legacy clients)
        os.environ["FORWARDED_ALLOW_IPS"] = "*"
        mcp.run(transport="sse", host=host, port=port, path=args.path)


if __name__ == "__main__":
    main()
