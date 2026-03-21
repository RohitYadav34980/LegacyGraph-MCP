"""Codebase ingestion tool: clone repos, parse raw files, scan directories."""

from typing import Dict, List, Optional
from pathlib import Path
import shutil

from src.core.graph import DependencyGraph, GraphError
from src.utils.logger import logger
import src.utils.config as config
import src.utils.services as services
from src.utils.helpers import _scan_directory, _clone_repo, _apply_patch


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
    if directory_path and config.MCP_MODE == "cloud":
        return (
            "Error: directory_path is not available in cloud mode. "
            "Use repo_url or raw_files instead."
        )

    # Reset graph for a fresh analysis
    services.graph_service = DependencyGraph()

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
                parsed_data = services.parser_service.parse_source(content)
                services.graph_service.build_from_parsed_data(parsed_data, filepath=filename)
                files_parsed += 1
            except Exception as e:
                logger.warning(f"Skipping raw file '{filename}': {e}")
                files_skipped += 1

        node_count = len(services.graph_service.get_all_nodes())
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
