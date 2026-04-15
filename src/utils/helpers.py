import subprocess
import tempfile
import shutil
import os
import concurrent.futures
from pathlib import Path
from typing import Optional, Tuple

from src.core.graph import GraphError
from src.core.parser import CppParser
from src.utils.logger import logger
from src.utils.config import CPP_EXTENSIONS
import src.utils.services as services


# ============================================================
# Internal Helpers
# ============================================================

def _parse_chunk_worker(chunk: list[Tuple[str, str]]) -> list[tuple[str, list, float]]:
    """
    Worker function for ProcessPoolExecutor to parse a chunk of C++ files.
    Processing in chunks drastically reduces IPC overhead.
    """
    results = []
    parser = CppParser()
    for file_path_str, relative_path_str in chunk:
        try:
            source_code = Path(file_path_str).read_text(encoding="utf-8", errors="replace")
            parsed_data = parser.parse_source(source_code)
            mtime = os.path.getmtime(file_path_str)
            results.append((relative_path_str, parsed_data, mtime))
        except Exception as e:
            logger.warning(f"Error in worker parsing {file_path_str}: {e}")
            results.append((relative_path_str, [], -1.0))
    return results


def _scan_directory(workspace: Path) -> tuple[int, int, int]:
    """
    Scan a directory for C++ files, parse them using multi-core processing,
    and populate graph_service incrementally.

    Returns:
        (files_parsed, files_skipped, node_count)
    """
    cache_path = workspace / ".legacygraph.json"
    
    # 1. Attempt to load existing cache
    if services.graph_service.load_cache(str(cache_path)):
        logger.info("Cache loaded successfully. Performing incremental build.")
    else:
        logger.info("No cache found. Performing full build.")

    files_to_parse = []
    files_skipped = 0

    # 2. Gather files and diff-check timestamps
    for pattern in CPP_EXTENSIONS:
        for file_path in workspace.rglob(pattern):
            try:
                mtime = os.path.getmtime(file_path)
                relative_path = str(file_path.relative_to(workspace))
                
                # Check if file is new or modified
                stored_mtime = services.graph_service.file_mtimes.get(relative_path, -1.0)
                if mtime > stored_mtime:
                    # File is modified or new. Drop old nodes if any.
                    if stored_mtime != -1.0:
                        services.graph_service.remove_file_nodes(relative_path)
                    
                    files_to_parse.append((str(file_path), relative_path))
            except Exception as e:
                logger.warning(f"Could not stat file {file_path}: {e}")
                files_skipped += 1

    files_parsed = 0

    # 3. Parse in parallel using ProcessPoolExecutor
    if files_to_parse:
        logger.info(f"Parsing {len(files_to_parse)} files across multiple cores...")
        
        # Calculate optimal chunk size to minimize IPC overhead
        total_cores = os.cpu_count() or 4
        # LEGACYMCP_MAX_WORKERS lets CI / constrained benchmarks cap parallelism
        _env_workers = os.environ.get("LEGACYMCP_MAX_WORKERS", "")
        if _env_workers.isdigit() and int(_env_workers) > 0:
            num_cores = int(_env_workers)
        else:
            # Use 80% of available cores (min 1) to keep the system responsive
            num_cores = max(1, int(total_cores * 0.8))

        # LEGACYMCP_CHUNK_SIZE overrides the auto-calculated IPC chunk size
        _env_chunk = os.environ.get("LEGACYMCP_CHUNK_SIZE", "")
        if _env_chunk.isdigit() and int(_env_chunk) > 0:
            chunk_size = int(_env_chunk)
        else:
            chunk_size = max(1, len(files_to_parse) // (num_cores * 4))
        
        # Split into chunks
        chunks = [
            files_to_parse[i:i + chunk_size] 
            for i in range(0, len(files_to_parse), chunk_size)
        ]
        
        total_files = len(files_to_parse)
        processed_files = 0
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_cores) as executor:
            # Map over chunks
            results_iter = executor.map(_parse_chunk_worker, chunks)
            
            for chunk_results in results_iter:
                for relative_path, parsed_data, mtime in chunk_results:
                    processed_files += 1
                    if mtime == -1.0:
                        files_skipped += 1
                        continue
                    
                    # Add nodes and edges to the global graph
                    services.graph_service.build_from_parsed_data(parsed_data, filepath=relative_path)
                    # Update timestamp
                    services.graph_service.file_mtimes[relative_path] = mtime
                    files_parsed += 1
                
                # Report progress after every chunk completes
                percent = (processed_files / total_files) * 100
                logger.info(f"Progress: {processed_files}/{total_files} files processed ({percent:.1f}%)")

        # 4. Save cache after modifying graph
        services.graph_service.save_cache(str(cache_path))
    else:
        logger.info("All files are up-to-date. No parsing needed.")

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
