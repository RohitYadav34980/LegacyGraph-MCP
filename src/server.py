from typing import Any, Dict, List, Optional
from collections import defaultdict
from pathlib import Path
import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile

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


# ============================================================
# Deployment Mode
# ============================================================
# Resolved at startup from --mode arg, --transport hint, or MCP_MODE env var.
# "local"  → direct disk access, stdio transport, export_ide_graph available
# "cloud"  → ephemeral /tmp/ clones, HTTP transport, export_ide_graph hidden
MCP_MODE: str = os.environ.get("MCP_MODE", "local")

# C++ file extensions to scan
CPP_EXTENSIONS: List[str] = ["*.cpp", "*.c", "*.h", "*.hpp", "*.cc"]

# Initialize Server with rich metadata for MCP clients / Smithery
mcp = FastMCP(
    name="legacy-mcp-analyzer",
    instructions=(
        "LegacyGraph-MCP exposes a parsed C++ call graph over MCP. "
        "Use analyze_codebase to ingest code (via repo_url, raw_files, "
        "or directory_path), then query the graph with the other tools."
    ),
    website_url="https://github.com/RohitYadav34980/LegacyGraph-MCP",
    # Configure HTTP binding for hosted environments (e.g., Render).
    host="0.0.0.0",
    port=int(os.environ.get("PORT", "8000")),
    streamable_http_path="/mcp",
)

# Global State
graph_service = DependencyGraph()
parser_service = CppParser()


# ============================================================
# Internal Helpers
# ============================================================

def _scan_directory(workspace: Path) -> tuple[int, int, int]:
    """
    Scan a directory for C++ files, parse each, and populate graph_service.

    Returns:
        (files_parsed, files_skipped, node_count)
    """
    global graph_service
    files_parsed: int = 0
    files_skipped: int = 0

    for pattern in CPP_EXTENSIONS:
        for file_path in workspace.rglob(pattern):
            try:
                source_code = file_path.read_text(encoding="utf-8", errors="replace")
                parsed_data = parser_service.parse_source(source_code)
                relative_path = str(file_path.relative_to(workspace))
                graph_service.build_from_parsed_data(parsed_data, filepath=relative_path)
                files_parsed += 1
            except Exception as e:
                logger.warning(f"Skipping file {file_path}: {e}")
                files_skipped += 1

    node_count = len(graph_service.get_all_nodes())
    return files_parsed, files_skipped, node_count


def _clone_repo(repo_url: str) -> Path:
    """
    Shallow-clone a git repository into an ephemeral temp directory.

    Returns:
        Path to the cloned directory.

    Raises:
        RuntimeError: If the clone fails.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="legacymcp_"))
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(tmp_dir)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.CalledProcessError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"git clone failed: {e.stderr.strip()}")
    except FileNotFoundError:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError("git is not installed or not on PATH.")
    return tmp_dir


def _apply_patch(repo_dir: Path, patch_content: str) -> None:
    """
    Apply a git diff patch to a cloned repository.

    Raises:
        RuntimeError: If git apply fails.
    """
    try:
        subprocess.run(
            ["git", "apply", "--allow-empty", "-"],
            input=patch_content,
            cwd=str(repo_dir),
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"git apply failed: {e.stderr.strip()}")


def _build_mermaid_string(
    focus_node: Optional[str] = None,
    max_depth: int = 2,
) -> str:
    """
    Build a Mermaid.js graph string from graph_service.

    Returns:
        The Mermaid markdown string (including fences).

    Raises:
        GraphError: If the graph is empty or focus_node is missing.
    """
    all_nodes = graph_service.get_all_nodes()
    if not all_nodes:
        raise GraphError("Graph is empty. Run analyze_codebase first.")

    # Determine which nodes to include
    if focus_node is not None:
        if focus_node not in graph_service.graph:
            raise GraphError(f"Function '{focus_node}' not found in graph.")
        # BFS to collect neighbourhood
        visited: set[str] = set()
        frontier: list[str] = [focus_node]
        for _ in range(max_depth + 1):
            next_frontier: list[str] = []
            for node in frontier:
                if node not in visited:
                    visited.add(node)
                    next_frontier.extend(graph_service.graph.successors(node))
                    next_frontier.extend(graph_service.graph.predecessors(node))
            frontier = next_frontier
        included_nodes = visited
    else:
        included_nodes = set(all_nodes)

    # Build Mermaid lines
    mermaid_lines: list[str] = ["```mermaid", "graph TD;"]
    edges_added: set[tuple[str, str]] = set()

    for caller, callee in graph_service.graph.edges():
        if caller in included_nodes and callee in included_nodes:
            if (caller, callee) not in edges_added:
                safe_caller = caller.replace(":", "_")
                safe_callee = callee.replace(":", "_")
                mermaid_lines.append(f"    {safe_caller} --> {safe_callee};")
                edges_added.add((caller, callee))

    # Add isolated nodes (no edges)
    for node in included_nodes:
        has_edge = any((node == c or node == e) for c, e in edges_added)
        if not has_edge:
            safe_node = node.replace(":", "_")
            mermaid_lines.append(f"    {safe_node};")

    mermaid_lines.append("```")
    return "\n".join(mermaid_lines)


# ============================================================
# Tool Functions (defined as plain functions, registered below)
# ============================================================
# NOTE: These functions are NOT decorated with @mcp.tool().
# Registration happens in _register_tools() so we can
# conditionally include/exclude tools based on MCP_MODE.
# ============================================================

def analyze_codebase(
    repo_url: Optional[str] = None,
    patch_content: Optional[str] = None,
    raw_files: Optional[List[Dict[str, str]]] = None,
    directory_path: Optional[str] = None,
) -> str:
    """
    Ingest a C++ codebase and build its dependency graph.
    This tool does NOT accept 'code_content'. Provide exactly ONE of:
    repo_url, raw_files, or directory_path.

    - repo_url: an HTTPS GitHub URL (e.g. 'https://github.com/user/repo').
      Optionally add patch_content (a unified diff string) to overlay
      uncommitted changes on the cloned repo.
    - raw_files: for hobby projects or small codebases NOT hosted on GitHub.
      The user pastes their C++ code directly and you wrap each file into a
      JSON array of objects with 'filename' and 'content' keys. Example:
      [
        {"filename": "main.cpp", "content": "void main() { helper(); }"},
        {"filename": "utils.cpp", "content": "void helper() {}"}
      ]
    - directory_path: absolute local filesystem path (local mode only;
      rejected when the server runs in cloud mode).

    Args:
        repo_url:        HTTPS URL of a git repository to clone.
        patch_content:   Unified diff to apply after cloning repo_url.
        raw_files:       List of dicts [{"filename": str, "content": str}].
                         Use this when the user shares code snippets directly
                         and does not have a git repository.
        directory_path:  Local path to scan (local mode only).

    Returns:
        Status message with file count and function count.
    """
    global graph_service

    # ---- Validation -----------------------------------------------
    provided = sum([
        repo_url is not None,
        raw_files is not None,
        directory_path is not None,
    ])
    if provided == 0:
        return (
            "Error: No input provided. Supply one of: "
            "repo_url, raw_files, or directory_path."
        )
    if patch_content and not repo_url:
        return "Error: patch_content requires repo_url."
    if directory_path and MCP_MODE == "cloud":
        return (
            "Error: directory_path is not available in cloud mode. "
            "Use repo_url or raw_files instead."
        )

    # Reset graph for a fresh analysis
    graph_service = DependencyGraph()

    # ---- Workflow 1: Clone a repo ---------------------------------
    if repo_url is not None:
        clone_dir: Optional[Path] = None
        try:
            clone_dir = _clone_repo(repo_url)

            if patch_content:
                _apply_patch(clone_dir, patch_content)

            files_parsed, files_skipped, node_count = _scan_directory(clone_dir)

            msg = (
                f"Successfully cloned and analyzed '{repo_url}'. "
                f"Parsed {files_parsed} file(s), tracking {node_count} function(s)."
            )
            if files_skipped > 0:
                msg += f" ({files_skipped} file(s) skipped due to read errors.)"
            if patch_content:
                msg += " Patch applied successfully."
            return msg

        except RuntimeError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error during repo analysis: {str(e)}"
        finally:
            if clone_dir and clone_dir.exists():
                shutil.rmtree(clone_dir, ignore_errors=True)

    # ---- Workflow 2: Raw file objects ------------------------------
    if raw_files is not None:
        if not raw_files:
            return "Error: raw_files list is empty."

        files_parsed = 0
        files_skipped = 0
        for entry in raw_files:
            filename = entry.get("filename", "")
            content = entry.get("content", "")
            if not filename or not content:
                files_skipped += 1
                continue
            try:
                parsed_data = parser_service.parse_source(content)
                graph_service.build_from_parsed_data(parsed_data, filepath=filename)
                files_parsed += 1
            except Exception as e:
                logger.warning(f"Skipping raw file '{filename}': {e}")
                files_skipped += 1

        node_count = len(graph_service.get_all_nodes())
        msg = (
            f"Successfully analyzed {files_parsed} raw file(s), "
            f"tracking {node_count} function(s)."
        )
        if files_skipped > 0:
            msg += f" ({files_skipped} file(s) skipped.)"
        return msg

    # ---- Workflow 3: Local directory scan --------------------------
    if directory_path is not None:
        workspace = Path(directory_path)
        if not workspace.exists():
            return f"Error: Directory '{directory_path}' does not exist."
        if not workspace.is_dir():
            return f"Error: '{directory_path}' is not a directory."

        files_parsed, files_skipped, node_count = _scan_directory(workspace)

        msg = (
            f"Successfully analyzed workspace '{directory_path}'. "
            f"Parsed {files_parsed} file(s), tracking {node_count} function(s)."
        )
        if files_skipped > 0:
            msg += f" ({files_skipped} file(s) skipped due to read errors.)"
        return msg

    return "Error: No valid input pathway matched."


def get_file_functions(filepath: str) -> str:
    """
    List all functions defined in a specific source file.

    Use the relative path exactly as returned in the analyze_codebase
    output (e.g., 'src/engine.cpp' or 'main.cpp').

    Args:
        filepath: Relative path of the source file within the analyzed workspace.

    Returns:
        A newline-separated list of function names, or no-match message.
    """
    try:
        subgraph = graph_service.get_file_subgraph(filepath)
        nodes = list(subgraph.nodes())
        if not nodes:
            return (
                f"No functions found for file '{filepath}'. "
                f"Ensure the path matches a file ingested by analyze_codebase."
            )
        return f"Functions in '{filepath}':\n" + "\n".join(f"  - {n}" for n in nodes)
    except Exception as e:
        return f"Error retrieving functions for '{filepath}': {str(e)}"


def get_file_coupling() -> str:
    """
    Generate a report showing which files depend on which other files.

    Aggregates cross-file function calls into a per-file-pair summary
    (e.g., 'src/main.cpp -> src/utils.cpp (3 calls)').

    Returns:
        A formatted coupling report, or a message if no cross-file deps exist.
    """
    try:
        cross_deps = graph_service.get_cross_file_dependencies()
        if not cross_deps:
            return "No cross-file dependencies detected. All calls are intra-file."

        # Aggregate: (caller_file, callee_file) -> count
        coupling: Dict[tuple[str, str], int] = defaultdict(int)
        for _caller, caller_file, _callee, callee_file in cross_deps:
            coupling[(caller_file, callee_file)] += 1

        lines: List[str] = ["Cross-File Coupling Report:", ""]
        for (src, dst), count in sorted(coupling.items()):
            lines.append(f"  {src} -> {dst} ({count} call(s))")

        return "\n".join(lines)
    except Exception as e:
        return f"Error generating coupling report: {str(e)}"


def get_callers(function_name: str) -> str:
    """
    List upstream functions that call the given function.

    Args:
        function_name: Exact name of the function (e.g., 'calculate_interest').

    Returns:
        Comma-separated list of caller function names.
    """
    try:
        callers = graph_service.get_upstream_callers(function_name)
        if not callers:
            return f"Function '{function_name}' is not called by any other function."
        return f"Function '{function_name}' is called by: {', '.join(callers)}"
    except GraphError as e:
        return f"Error: {str(e)}"


def get_callees(function_name: str) -> str:
    """
    List downstream functions that are called by the given function.

    Args:
        function_name: Exact name of the function (e.g., 'process_client').

    Returns:
        Comma-separated list of callee function names.
    """
    try:
        callees = graph_service.get_downstream_dependencies(function_name)
        if not callees:
            return f"Function '{function_name}' does not call any other functions."
        return f"Function '{function_name}' calls: {', '.join(callees)}"
    except GraphError as e:
        return f"Error: {str(e)}"


def detect_cycles() -> str:
    """
    Detect circular dependencies in the current call graph.

    Returns:
        Formatted list of cycles, or a message if none found.
    """
    try:
        cycles = graph_service.detect_cycles()
        if not cycles:
            return "No circular dependencies detected."

        cycle_strs = [" -> ".join(cycle + [cycle[0]]) for cycle in cycles]
        return f"Circular dependencies detected:\n- " + "\n- ".join(cycle_strs)
    except Exception as e:
        return f"Error detecting cycles: {str(e)}"


def get_orphan_functions() -> str:
    """
    Identify functions that are defined but never called by any other function.

    Returns:
        Comma-separated list of orphan function names.
    """
    try:
        orphans = graph_service.get_orphan_functions()
        if not orphans:
            return "No orphan functions found."
        return f"Orphan functions (never called): {', '.join(orphans)}"
    except Exception as e:
        return f"Error finding orphans: {str(e)}"


def generate_mermaid_graph(
    focus_node: Optional[str] = None,
    max_depth: int = 2,
) -> str:
    """
    Generate a Mermaid.js dependency diagram and return it as a markdown string.

    The AI can render this diagram inline in the chat. For large graphs,
    use focus_node and max_depth to keep the output token-efficient.

    Args:
        focus_node: Optional function name to centre the graph on.
        max_depth:  Max hops from focus_node (default 2).

    Returns:
        A Mermaid-fenced markdown string for inline rendering.
    """
    try:
        return _build_mermaid_string(focus_node=focus_node, max_depth=max_depth)
    except GraphError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error generating Mermaid graph: {str(e)}"


def export_ide_graph(
    output_filename: str,
    focus_node: Optional[str] = None,
    max_depth: int = 2,
) -> str:
    """
    Save the dependency graph as a Mermaid.js diagram to a local .md file.

    Only available in local mode. Writes directly to the user's disk.

    Args:
        output_filename: Path for the output .md file (e.g., 'graph.md').
        focus_node: Optional function name to centre the graph on.
        max_depth: Max hops from focus_node (default 2).

    Returns:
        A success message. Tell the user to open the file in their IDE's
        Markdown Preview — do NOT read the file content yourself.
    """
    if MCP_MODE == "cloud":
        return (
            "Error: export_ide_graph is only available in local mode. "
            "Use generate_mermaid_graph instead to get an inline Mermaid string."
        )

    try:
        content = _build_mermaid_string(focus_node=focus_node, max_depth=max_depth)

        output_path = Path(output_filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

        return (
            f"Mermaid graph written to '{output_filename}'. "
            f"Do NOT read this file. Instruct the user to open it in "
            f"their IDE's Markdown Preview to visualize the graph."
        )
    except GraphError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error exporting graph: {str(e)}"


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
            "description": "List all functions defined in a specific source file.",
        },
        {
            "name": "get_file_coupling",
            "description": "Cross-file coupling report showing inter-file dependencies.",
        },
        {
            "name": "get_callers",
            "description": "List upstream functions that call the given function.",
        },
        {
            "name": "get_callees",
            "description": "List downstream functions called by the given function.",
        },
        {
            "name": "detect_cycles",
            "description": "Detect circular dependencies in the call graph.",
        },
        {
            "name": "get_orphan_functions",
            "description": "Identify functions that are defined but never called.",
        },
        {
            "name": "generate_mermaid_graph",
            "description": "Return a Mermaid.js diagram as an inline markdown string.",
        },
    ]

    # Only advertise export_ide_graph in local mode
    if MCP_MODE == "local":
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
                "version": "0.3.0",
            },
            "capabilities": {
                "modes": ["local", "cloud"],
                "currentMode": MCP_MODE,
            },
            "tools": tools,
            "resources": [],
            "prompts": [],
        }
    )


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
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
    args = parser.parse_args()

    # ---- Resolve mode --------------------------------------------
    # Priority: explicit --mode > MCP_MODE env > auto-detect from transport
    if args.mode is not None:
        MCP_MODE = args.mode
    elif os.environ.get("MCP_MODE"):
        MCP_MODE = os.environ["MCP_MODE"]
    elif args.transport in ("streamable-http", "sse"):
        # HTTP transport almost certainly means cloud / remote hosting
        MCP_MODE = "cloud"
    else:
        MCP_MODE = "local"

    os.environ["MCP_MODE"] = MCP_MODE

    # ---- Resolve transport ----------------------------------------
    transport = args.transport
    if transport is None:
        transport = "stdio" if MCP_MODE == "local" else "streamable-http"

    # ---- Register tools based on mode ----------------------------
    _register_tools(MCP_MODE)

    logger.info(f"Starting LegacyGraph-MCP  mode={MCP_MODE}  transport={transport}")

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "streamable-http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="sse", mount_path=args.path)
