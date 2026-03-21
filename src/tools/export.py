"""Export and visualization tools for the dependency graph."""

from typing import Optional
from pathlib import Path

from src.core.graph import GraphError
import src.utils.config as config
from src.utils.helpers import _build_mermaid_string


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
    if config.MCP_MODE == "cloud":
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
