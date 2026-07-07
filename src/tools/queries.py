"""Query tools for the dependency graph."""

from typing import Dict, List, Optional
from collections import defaultdict

from src.core.graph import GraphError
import src.utils.services as services


def get_file_functions(filepath: str, project_id: Optional[str] = None) -> str:
    """
    List all functions defined in a specific source file.

    Use the relative path exactly as returned in the analyze_codebase
    output (e.g., 'src/engine.cpp' or 'main.cpp').

    Args:
        filepath: Relative path of the source file within the analyzed workspace.
        project_id: Optional unique identifier for the project/session.

    Returns:
        A newline-separated list of function names, or no-match message.
    """
    try:
        graph = services.graph_pool.get_graph(project_id)
        subgraph = graph.get_file_subgraph(filepath)
        nodes = list(subgraph.nodes())
        if not nodes:
            return (
                f"No functions found for file '{filepath}'. "
                f"Ensure the path matches a file ingested by analyze_codebase."
            )
        return f"Functions in '{filepath}':\n" + "\n".join(f"  - {n}" for n in nodes)
    except Exception as e:
        return f"Error retrieving functions for '{filepath}': {str(e)}"


def get_file_coupling(project_id: Optional[str] = None) -> str:
    """
    Generate a report showing which files depend on which other files.

    Aggregates cross-file function calls into a per-file-pair summary
    (e.g., 'src/main.cpp -> src/utils.cpp (3 calls)').

    Args:
        project_id: Optional unique identifier for the project/session.

    Returns:
        A formatted coupling report, or a message if no cross-file deps exist.
    """
    try:
        graph = services.graph_pool.get_graph(project_id)
        cross_deps = graph.get_cross_file_dependencies()
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


def get_callers(function_name: str, project_id: Optional[str] = None) -> str:
    """
    List upstream functions that call the given function.

    Args:
        function_name: Exact name of the function (e.g., 'calculate_interest').
        project_id: Optional unique identifier for the project/session.

    Returns:
        Comma-separated list of caller function names.
    """
    try:
        graph = services.graph_pool.get_graph(project_id)
        callers = graph.get_upstream_callers(function_name)
        if not callers:
            return f"Function '{function_name}' is not called by any other function."
        return f"Function '{function_name}' is called by: {', '.join(callers)}"
    except GraphError as e:
        return f"Error: {str(e)}"


def get_callees(function_name: str, project_id: Optional[str] = None) -> str:
    """
    List downstream functions that are called by the given function.

    Args:
        function_name: Exact name of the function (e.g., 'process_client').
        project_id: Optional unique identifier for the project/session.

    Returns:
        Comma-separated list of callee function names.
    """
    try:
        graph = services.graph_pool.get_graph(project_id)
        callees = graph.get_downstream_dependencies(function_name)
        if not callees:
            return f"Function '{function_name}' does not call any other functions."
        return f"Function '{function_name}' calls: {', '.join(callees)}"
    except GraphError as e:
        return f"Error: {str(e)}"


def detect_cycles(project_id: Optional[str] = None) -> str:
    """
    Detect circular dependencies in the current call graph.

    Args:
        project_id: Optional unique identifier for the project/session.

    Returns:
        Formatted list of cycles, or a message if none found.
    """
    try:
        graph = services.graph_pool.get_graph(project_id)
        cycles = graph.detect_cycles()
        if not cycles:
            return "No circular dependencies detected."

        cycle_strs = [" -> ".join(cycle + [cycle[0]]) for cycle in cycles]
        return "Circular dependencies detected:\n- " + "\n- ".join(cycle_strs)
    except Exception as e:
        return f"Error detecting cycles: {str(e)}"


def get_orphan_functions(project_id: Optional[str] = None) -> str:
    """
    Identify functions that are defined but never called by any other function.

    Args:
        project_id: Optional unique identifier for the project/session.

    Returns:
        Comma-separated list of orphan function names.
    """
    try:
        graph = services.graph_pool.get_graph(project_id)
        orphans = graph.get_orphan_functions()
        if not orphans:
            return "No orphan functions found."
        return f"Orphan functions (never called): {', '.join(orphans)}"
    except Exception as e:
        return f"Error finding orphans: {str(e)}"
