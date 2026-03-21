import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional

from src.core.graph import GraphError
from src.utils.logger import logger
from src.utils.config import CPP_EXTENSIONS
import src.utils.services as services


# ============================================================
# Internal Helpers
# ============================================================

def _scan_directory(workspace: Path) -> tuple[int, int, int]:
    """
    Scan a directory for C++ files, parse each, and populate graph_service.

    Returns:
        (files_parsed, files_skipped, node_count)
    """
    files_parsed: int = 0
    files_skipped: int = 0

    for pattern in CPP_EXTENSIONS:
        for file_path in workspace.rglob(pattern):
            try:
                source_code = file_path.read_text(encoding="utf-8", errors="replace")
                parsed_data = services.parser_service.parse_source(source_code)
                relative_path = str(file_path.relative_to(workspace))
                services.graph_service.build_from_parsed_data(parsed_data, filepath=relative_path)
                files_parsed += 1
            except Exception as e:
                logger.warning(f"Skipping file {file_path}: {e}")
                files_skipped += 1

    node_count = len(services.graph_service.get_all_nodes())
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
    all_nodes = services.graph_service.get_all_nodes()
    if not all_nodes:
        raise GraphError("Graph is empty. Run analyze_codebase first.")

    # Determine which nodes to include
    if focus_node is not None:
        if focus_node not in services.graph_service.graph:
            raise GraphError(f"Function '{focus_node}' not found in graph.")
        # BFS to collect neighbourhood
        visited: set[str] = set()
        frontier: list[str] = [focus_node]
        for _ in range(max_depth + 1):
            next_frontier: list[str] = []
            for node in frontier:
                if node not in visited:
                    visited.add(node)
                    next_frontier.extend(services.graph_service.graph.successors(node))
                    next_frontier.extend(services.graph_service.graph.predecessors(node))
            frontier = next_frontier
        included_nodes = visited
    else:
        included_nodes = set(all_nodes)

    # Build Mermaid lines
    mermaid_lines: list[str] = ["```mermaid", "graph TD;"]
    edges_added: set[tuple[str, str]] = set()

    for caller, callee in services.graph_service.graph.edges():
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
