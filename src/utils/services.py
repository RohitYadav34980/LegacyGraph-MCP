from typing import Dict, Optional
import os
import threading

from src.core.graph import DependencyGraph
from src.core.parser import CppParser
import src.utils.config as config

class GraphPool:
    """Manages multiple DependencyGraph instances, indexed by project_id."""
    def __init__(self) -> None:
        self._pool: Dict[str, DependencyGraph] = {}
        self._lock = threading.Lock()

    def get_graph(self, project_id: Optional[str] = None) -> DependencyGraph:
        """
        Retrieves a graph for a project. 
        In Cloud mode, project_id is usually required.
        In Local mode, it defaults to the workspace root if not provided.
        """
        # Deterministic project key
        key = project_id or "default_workspace"
        
        with self._lock:
            if key not in self._pool:
                graph = DependencyGraph()
                
                # Auto-load if cache exists (Mode-aware path resolution)
                cache_path = self._get_cache_path(key)
                if cache_path and os.path.exists(cache_path):
                    graph.load_cache(cache_path)
                
                self._pool[key] = graph
            
            return self._pool[key]

    def _sanitize_project_id(self, project_id: str) -> str:
        """
        Sanitizes a project_id to prevent path traversal attacks.
        Only alphanumeric characters, hyphens, and underscores are allowed.
        """
        import re
        safe = re.sub(r"[^a-zA-Z0-9_\-]", "", project_id)
        if not safe:
            raise ValueError(f"Invalid project_id '{project_id}': must contain alphanumeric characters.")
        return safe

    def _get_cache_path(self, project_id: str) -> Optional[str]:
        """Resolves the cache file path based on deployment mode."""
        safe_id = self._sanitize_project_id(project_id)
        if config.MCP_MODE == "cloud":
            # Cloud: <CACHE_ROOT>/<safe_project_id>.json
            return os.path.join(config.LEGACYGRAPH_CACHE_ROOT, f"{safe_id}.json")
        else:
            # Local: Standard workspace .legacygraph.json (legacy behavior)
            if project_id == "default_workspace":
                return ".legacygraph.json"
            return None

# Global State
graph_pool = GraphPool()
parser_service = CppParser()

# Legacy alias helper to minimize massive refactoring in tools
def get_graph_service() -> DependencyGraph:
    """Legacy helper to get the 'default' graph. Avoid in new code."""
    return graph_pool.get_graph()
