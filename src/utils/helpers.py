import subprocess
import tempfile
import shutil
import os
import concurrent.futures
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from src.core.graph import DependencyGraph

from src.core.graph import GraphError
from src.core.parser import CppParser
from src.utils.logger import logger
from src.utils.config import CPP_EXTENSIONS
import src.utils.services as services
import hashlib
import src.utils.config as config


# ============================================================
# Internal Helpers
# ============================================================

def _parse_chunk_worker(
    chunk: list[Tuple[str, str]],
) -> list[tuple[str, list[tuple[str, Set[str]]], float]]:
    """
    Worker function for ProcessPoolExecutor to parse a chunk of C++ files.
    Processing in chunks drastically reduces IPC overhead.
    """
    results = []
    parser = CppParser()
    for file_path_str, relative_path_str in chunk:
        try:
            source_code = Path(file_path_str).read_text(encoding="utf-8", errors="replace")
            parsed_data: list[tuple[str, Set[str]]] = parser.parse_source(source_code)
            mtime = os.path.getmtime(file_path_str)
            results.append((relative_path_str, parsed_data, mtime))
        except Exception as e:
            logger.warning(f"Error in worker parsing {file_path_str}: {e}")
            results.append((relative_path_str, [], -1.0))
    return results


def _scan_directory(workspace: Path, cache_path: Optional[str] = None, graph: Optional["DependencyGraph"] = None, task: Optional[Any] = None) -> tuple[int, int, int]:
    """
    Scan a directory for C++ files, parse them using multi-core processing,
    and populate the given graph incrementally.

    Args:
        workspace: Path to the directory to scan.
        cache_path: Explicit path to the JSON cache file. If None, uses workspace/.legacygraph.json.
        graph: The DependencyGraph instance to operate on. Defaults to the pool's default graph.

    Returns:
        (files_parsed, files_skipped, node_count)
    """
    if cache_path is None:
        cache_path = str(workspace / ".legacygraph.json")

    # Use the provided graph or fall back to graph_service — always the SAME instance
    if graph is None:
        graph = services.graph_service
    if graph is None:
        # graph_service is None in cloud mode; callers there must pass a
        # pool graph explicitly (analyze_codebase always does).
        raise GraphError(
            "No graph available: pass a DependencyGraph explicitly "
            "(the default graph_service is disabled in cloud mode)."
        )

    # 1. Attempt to load existing cache
    if graph.load_cache(cache_path):
        logger.info(f"Cache loaded from {cache_path}. Performing incremental build.")
    else:
        logger.info("No cache found. Performing full build.")

    files_to_parse = []
    files_skipped = 0
    discovered_files: set[str] = set()

    # 2. Gather files and diff-check timestamps
    for pattern in CPP_EXTENSIONS:
        for file_path in workspace.rglob(pattern):
            try:
                mtime = os.path.getmtime(file_path)
                relative_path = str(file_path.relative_to(workspace))
                discovered_files.add(relative_path)

                # Check if file is new or modified
                stored_mtime = graph.file_mtimes.get(relative_path, -1.0)
                if mtime > stored_mtime:
                    # File is modified or new. Drop old nodes if any.
                    if stored_mtime != -1.0:
                        graph.remove_file_nodes(relative_path)

                    files_to_parse.append((str(file_path), relative_path))
            except Exception as e:
                logger.warning(f"Could not stat file {file_path}: {e}")
                files_skipped += 1

    removed_files = set(graph.file_mtimes.keys()) - discovered_files
    for removed_file in removed_files:
        graph.remove_file_nodes(removed_file)
        graph.file_mtimes.pop(removed_file, None)

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

                    # Add nodes and edges to the graph instance
                    graph.build_from_parsed_data(parsed_data, filepath=relative_path)
                    # Update timestamp
                    graph.file_mtimes[relative_path] = mtime
                    files_parsed += 1

                # Report progress after every chunk completes
                percent = (processed_files / total_files) * 100
                logger.info(f"Progress: {processed_files}/{total_files} files processed ({percent:.1f}%)")
                if task:
                    task.update(progress=int(percent), status_text=f"Parsing files: {processed_files}/{total_files}")

        # 4. Save cache after modifying graph
        graph.save_cache(cache_path)
    else:
        logger.info("All files are up-to-date. No parsing needed.")

    node_count = len(graph.get_all_nodes())
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
    graph: "DependencyGraph",
    focus_node: Optional[str] = None,
    max_depth: int = 2,
) -> str:
    """
    Build a Mermaid.js graph string from a specific graph instance.

    Returns:
        The Mermaid markdown string (including fences).

    Raises:
        GraphError: If the graph is empty or focus_node is missing.
    """
    all_nodes = graph.get_all_nodes()
    if not all_nodes:
        raise GraphError("Graph is empty. Run analyze_codebase first.")

    # Determine which nodes to include
    if focus_node is not None:
        if focus_node not in graph.graph:
            raise GraphError(f"Function '{focus_node}' not found in graph.")
        # BFS to collect neighbourhood
        visited: set[str] = set()
        frontier: list[str] = [focus_node]
        for _ in range(max_depth + 1):
            next_frontier: list[str] = []
            for node in frontier:
                if node not in visited:
                    visited.add(node)
                    next_frontier.extend(graph.graph.successors(node))
                    next_frontier.extend(graph.graph.predecessors(node))
            frontier = next_frontier
        included_nodes = visited
    else:
        included_nodes = set(all_nodes)

    # Build Mermaid lines
    mermaid_lines: list[str] = ["```mermaid", "graph TD;"]
    edges_added: set[tuple[str, str]] = set()

    for caller, callee in graph.graph.edges():
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


def _get_project_id(target: str) -> str:
    """Generates a stable 8-character hash for a project target (URL or Path)."""
    return hashlib.sha256(target.encode()).hexdigest()[:8]


def _get_raw_files_project_id(raw_files: List[Dict[str, str]]) -> str:
    """Generates a stable content-based project ID for a raw_files list."""
    sorted_files = sorted(raw_files, key=lambda f: f.get("filename", ""))
    normalized = "".join(
        f"{f.get('filename', '')}:{f.get('content', '')}" for f in sorted_files
    )
    content_hash = hashlib.sha256(normalized.encode()).hexdigest()[:12]
    return f"raw_{content_hash}"


def _get_remote_hash(repo_url: str) -> Optional[str]:
    """Fetches the latest commit hash from a remote git repository."""
    try:
        result = subprocess.run(
            ["git", "ls-remote", repo_url, "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.stdout:
            return result.stdout.split()[0]
    except Exception as e:
        logger.warning(f"Failed to fetch remote hash for {repo_url}: {e}")
    return None


def _sync_to_hf_bucket() -> bool:
    """
    Synchronizes the local cache directory to the configured Hugging Face bucket.

    Priority order:
      1. If a persistent storage volume is mounted at /data (IS_STORAGE_MOUNTED),
         the cache is already on durable storage — no API call needed.
      2. If HF_BUCKET_URL starts with hf://buckets/, use the native sync_bucket API.
      3. Fallback: upload_folder to a standard HF repo (dataset/model/space).
    """
    if config.MCP_MODE != "cloud":
        return False

    # ── Priority 1: Persistent mount detected — cache is already durable ──────
    # This check MUST come before the HF_BUCKET_URL guard so it fires even when
    # no bucket URL is configured (bucket mounted via Spaces UI, not env var).
    if getattr(config, "IS_STORAGE_MOUNTED", False):
        os.makedirs(config.LEGACYGRAPH_CACHE_ROOT, exist_ok=True)
        logger.info(
            f"Persistent storage mounted at '{config.PERSISTENT_STORAGE_ROOT}'. "
            f"Cache is written directly to '{config.LEGACYGRAPH_CACHE_ROOT}'. "
            "Skipping manual HF API sync."
        )
        return True

    if not config.HF_BUCKET_URL:
        logger.warning(
            "No persistent storage mount detected and HF_BUCKET_URL is not set. "
            "Cache will NOT persist across restarts. "
            "Mount a Storage Bucket in the Space settings or set HF_BUCKET_URL."
        )
        return False

    try:
        # ── Priority 2: Native Storage Bucket via hf://buckets/ URL ─────────
        if config.HF_BUCKET_URL.startswith("hf://buckets/"):
            from huggingface_hub import sync_bucket
            logger.info(f"Syncing {config.LEGACYGRAPH_CACHE_ROOT} to native bucket '{config.HF_BUCKET_URL}'...")
            sync_bucket(
                local_path=config.LEGACYGRAPH_CACHE_ROOT,
                remote_path=config.HF_BUCKET_URL,
                token=os.environ.get("HF_TOKEN"),
            )
            logger.info("HF Bucket Sync completed successfully.")
            return True

        # ── Priority 3: Standard HF Repo (dataset / model / space) ──────────
        from huggingface_hub import HfApi
        # Parse hf://datasets/namespace/repo  →  repo_type="dataset", repo_id="namespace/repo"
        url = config.HF_BUCKET_URL.replace("hf://", "")
        parts = url.split("/")

        repo_type = "dataset"
        if parts[0] in ["datasets", "models", "spaces"]:
            repo_type = parts[0].rstrip("s")   # "datasets" → "dataset"
            repo_id = "/".join(parts[1:])
        else:
            repo_id = "/".join(parts)

        logger.info(f"Syncing {config.LEGACYGRAPH_CACHE_ROOT} to {repo_type} repo '{repo_id}' using HfApi...")
        api = HfApi()
        api.upload_folder(
            folder_path=config.LEGACYGRAPH_CACHE_ROOT,
            repo_id=repo_id,
            repo_type=repo_type,
            token=os.environ.get("HF_TOKEN"),
        )
        logger.info("HF Repo Sync completed successfully.")
        return True

    except ImportError:
        logger.warning("huggingface_hub library not found. Skipping sync. Please `pip install huggingface_hub`.")
    except Exception as e:
        logger.error(f"HF Sync failed with error: {e}")
    return False
