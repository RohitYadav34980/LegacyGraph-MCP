from typing import Dict, Optional
import os
import re
import threading

from src.core.graph import DependencyGraph
from src.core.parser import CppParser
from src.utils.tasks import TaskRegistry
import src.utils.config as config

class GraphPool:
    """Manages multiple DependencyGraph instances, indexed by project_id."""
    def __init__(self) -> None:
        self._pool: Dict[str, DependencyGraph] = {}
        self._graph_locks: Dict[str, threading.RLock] = {}
        self._lock = threading.Lock()

    def get_graph(self, project_id: Optional[str] = None) -> DependencyGraph:
        """
        Retrieves a graph for a project.
        In Cloud mode, project_id is required to prevent cross-project data leakage.
        In Local mode, it defaults to the workspace root if not provided.
        """
        if config.MCP_MODE == "cloud" and project_id is None:
            raise ValueError(
                "project_id is required in cloud mode to prevent cross-project data leakage."
            )

        # Sanitize once; use safe_id as the canonical key for both pool and cache
        raw_key = project_id or "default_workspace"
        safe_id = self._sanitize_project_id(raw_key)

        with self._lock:
            if safe_id not in self._pool:
                graph = DependencyGraph()
                self._graph_locks[safe_id] = threading.RLock()

                # Auto-load if cache exists (Mode-aware path resolution)
                cache_path = self._get_cache_path(safe_id)
                if cache_path and os.path.exists(cache_path):
                    graph.load_cache(cache_path)

                self._pool[safe_id] = graph

            return self._pool[safe_id]

    def get_graph_lock(self, project_id: Optional[str] = None) -> threading.RLock:
        """Returns the per-graph RLock for the given project_id."""
        raw_key = project_id or "default_workspace"
        safe_id = self._sanitize_project_id(raw_key)
        with self._lock:
            if safe_id not in self._graph_locks:
                self._graph_locks[safe_id] = threading.RLock()
            return self._graph_locks[safe_id]

    def _sanitize_project_id(self, project_id: str) -> str:
        """
        Validates and returns a project_id.
        Rejects IDs containing characters outside [a-zA-Z0-9_-] to prevent
        path traversal attacks and cross-project cache collisions.
        """
        safe = re.sub(r"[^a-zA-Z0-9_\-]", "", project_id)
        if not safe:
            raise ValueError(
                "Invalid project_id: must contain alphanumeric characters, "
                "hyphens, or underscores."
            )
        if safe != project_id:
            raise ValueError(
                "Invalid project_id: contains disallowed characters. "
                "Use only alphanumeric characters, hyphens, and underscores."
            )
        return safe

    def _get_cache_path(self, safe_id: str) -> Optional[str]:
        """Resolves the cache file path based on deployment mode. safe_id must already be sanitized."""
        if config.MCP_MODE == "cloud":
            # Cloud: <CACHE_ROOT>/<safe_project_id>.json
            return os.path.join(config.LEGACYGRAPH_CACHE_ROOT, f"{safe_id}.json")
        else:
            # Local: Standard workspace .legacygraph.json (legacy behavior)
            if safe_id == "default_workspace":
                return ".legacygraph.json"
            return None

# Global State
graph_pool = GraphPool()
parser_service = CppParser()
task_registry = TaskRegistry()

# Backward-compat shim: graph_service → default pool graph (local mode only).
# In cloud mode, project_id is required per-request, so we leave this as None.
# Tests and legacy local callers may rebind this module-level var to reset state.
graph_service = graph_pool.get_graph() if config.MCP_MODE != "cloud" else None


def reset_graph_service(graph: Optional[DependencyGraph] = None) -> DependencyGraph:
    """
    Resets the legacy default graph service.

    This preserves backwards compatibility for tests and older callers that
    rebind src.utils.services.graph_service to reset state.
    """
    global graph_service
    if config.MCP_MODE == "cloud":
        # In cloud mode there is no single default graph; callers must use project_id.
        graph_service = None
        return graph_service  # type: ignore[return-value]
    graph_service = graph if graph is not None else graph_pool.get_graph()
    return graph_service


# Legacy alias helper to minimize massive refactoring in tools
def get_graph_service() -> DependencyGraph:
    """Legacy helper to get the 'default' graph. Avoid in new code."""
    return graph_service
