import logging
from typing import List, Set, Tuple, Optional

try:
    import tree_sitter_cpp as ts_cpp
    from tree_sitter import Language, Parser, Node
except ImportError:
    ts_cpp = None  # type: ignore[assignment]
    Language = Parser = Node = None  # type: ignore[assignment,misc]
    logging.warning("Failed to import tree-sitter dependencies. Parser will not work.")

# Module logger only — never call logging.basicConfig() in a library module:
# it hijacks the root logger for every consumer of this package.
logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Custom exception for parsing errors."""
    pass


class CppParser:
    """
    Parses C++ code to extract function definitions and their calls.

    Attributes:
        parser (Parser): The tree-sitter parser instance initialized with C++.
    """

    def __init__(self) -> None:
        """Initialize the CppParser with tree-sitter-cpp."""
        if ts_cpp is None or Language is None:
            raise ParseError("tree-sitter or tree-sitter-cpp not cached/installed correctly.")

        try:
            self.cpp_language = Language(ts_cpp.language())
            self.parser = Parser(self.cpp_language)
            self.func_query = self.cpp_language.query("(function_definition) @func")
            self.call_query = self.cpp_language.query("(call_expression) @call")
        except Exception as e:
            logger.error(f"Failed to initialize tree-sitter parser: {e}")
            raise ParseError(f"Parser initialization failed: {e}")

    def parse_source(self, source_code: str) -> List[Tuple[str, Set[str]]]:
        """
        Parses C++ source code to find function definitions and the functions they call.

        Args:
            source_code: The C++ source code as a string.

        Returns:
            A list of tuples, where each tuple contains:
            - The name of the defined function (str).
            - A set of names of functions called within that definition (Set[str]).

        Raises:
            ParseError: If parsing fails unexpectedly.
        """
        try:
            tree = self.parser.parse(bytes(source_code, "utf8"))
            root_node = tree.root_node
            results: List[Tuple[str, Set[str]]] = []

            # Use a Query to find all function definitions anywhere in the tree
            # This is robust against hierarchy changes caused by syntax errors
            # captures(node) returns Dict[str, List[Node]] in newer bindings
            captures = self.func_query.captures(root_node)

            # Handle both list (older) and dict (newer) return types just in case, 
            # but based on debug we know it is dict.
            if isinstance(captures, dict):
                for name, nodes in captures.items():
                    for node in nodes:
                        func_name = self._extract_function_name(node)
                        if func_name:
                            calls = self._extract_function_calls(node)
                            results.append((func_name, calls))
            else:
                 # Fallback if specific version changes
                 for node, _ in captures:
                    func_name = self._extract_function_name(node)
                    if func_name:
                        calls = self._extract_function_calls(node)
                        results.append((func_name, calls))
            
            return results

        except Exception as e:
            logger.error(f"Error parsing source code: {e}")
            raise ParseError(f"Parsing failed: {e}")

    @staticmethod
    def _node_text(node: Node) -> str:
        """Decodes a node's source text (tree-sitter types it as Optional)."""
        return (node.text or b"").decode("utf8")

    def _extract_function_name(self, func_def_node: Node) -> Optional[str]:
        """
        Extracts the function name from a function_definition node.
        """
        declarator = func_def_node.child_by_field_name("declarator")
        if not declarator:
            return None

        curr: Optional[Node] = declarator
        while curr:
            if curr.type == "identifier":
                return self._node_text(curr)
            elif curr.type == "function_declarator":
                curr = curr.child_by_field_name("declarator")
            elif curr.type == "parenthesized_declarator":
                 curr = curr.child_by_field_name("declarator")
            elif curr.type == "pointer_declarator" or curr.type == "reference_declarator":
                 curr = curr.child_by_field_name("declarator")
            elif curr.type == "field_identifier":
                 return self._node_text(curr)
            else:
                break

        if declarator.type == "function_declarator":
             inner_decl = declarator.child_by_field_name("declarator")
             if inner_decl and inner_decl.type == "qualified_identifier":
                 return self._node_text(inner_decl)

        return None

    def _extract_function_calls(self, root_node: Node) -> Set[str]:
        """
        Extracts names of functions called within a given node scope.
        """
        calls: Set[str] = set()
        
        captures = self.call_query.captures(root_node)
        
        if isinstance(captures, dict):
            for name, nodes in captures.items():
                for node in nodes:
                     func_node = node.child_by_field_name("function")
                     if func_node:
                        calls.add(self._node_text(func_node))
        else:
            for node, _ in captures:
                 func_node = node.child_by_field_name("function")
                 if func_node:
                    calls.add(self._node_text(func_node))

        return calls
