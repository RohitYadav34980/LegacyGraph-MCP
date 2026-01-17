import logging
import networkx as nx  # type: ignore
from typing import List, Set, Dict, Any

logger = logging.getLogger(__name__)


class GraphError(Exception):
    """Base class for graph-related errors."""
    pass


class CircularDependencyError(GraphError):
    """Raised when a circular dependency is detected."""
    pass


class DependencyGraph:
    """
    Manages the dependency graph of functions.
    Uses NetworkX for storage and analysis.
    """

    def __init__(self) -> None:
        """Initialize an empty directed graph."""
        self.graph = nx.DiGraph()

    def add_dependency(self, caller: str, callee: str) -> None:
        """
        Adds a dependency: caller -> callee.

        Args:
            caller: The name of the function calling another.
            callee: The name of the function being called.
        """
        self.graph.add_edge(caller, callee)

    def build_from_parsed_data(self, data: List[tuple[str, Set[str]]]) -> None:
        """
        Builds the graph from a list of (function_name, called_functions).

        Args:
            data: List of tuples (caller, set_of_callees).
        """
        for caller, callees in data:
            self.graph.add_node(caller)  # Ensure caller exists even if no callees
            for callee in callees:
                self.add_dependency(caller, callee)

    def detect_cycles(self) -> List[List[str]]:
        """
        Detects all simple cycles in the graph.

        Returns:
            A list of cycles, where each cycle is a list of function names.
        """
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles  # type: ignore
        except Exception as e:
            logger.error(f"Error detecting cycles: {e}")
            raise GraphError(f"Cycle detection failed: {e}")

    def get_downstream_dependencies(self, func_name: str) -> List[str]:
        """
        Returns a list of functions called by the given function (direct children).

        Args:
            func_name: The name of the function.

        Returns:
            List of callee function names.

        Raises:
            GraphError: If the function is not in the graph.
        """
        if func_name not in self.graph:
            raise GraphError(f"Function '{func_name}' not found in graph.")
        
        return list(self.graph.successors(func_name))

    def get_upstream_callers(self, func_name: str) -> List[str]:
        """
        Returns a list of functions that call the given function (direct parents).

        Args:
            func_name: The name of the function.

        Returns:
            List of caller function names.

        Raises:
            GraphError: If the function is not in the graph.
        """
        if func_name not in self.graph:
            raise GraphError(f"Function '{func_name}' not found in graph.")
        
        return list(self.graph.predecessors(func_name))

    def get_all_nodes(self) -> List[str]:
        """Returns all function names in the graph."""
        return list(self.graph.nodes())

    def get_orphan_functions(self) -> List[str]:
        """
        Returns functions that are defined but never called (in-degree 0),
        excluding potential root nodes if they are entry points (main).
        But strictly speaking, orphans are those with in-degree 0.
        """
        return [n for n, d in self.graph.in_degree() if d == 0]
