import logging
from typing import List, Set, Tuple, Optional
try:
    import tree_sitter_cpp as ts_cpp  # type: ignore
    from tree_sitter import Language, Parser, Node  # type: ignore
except ImportError:
    ts_cpp = None
    Language = Parser = Node = None
    logging.warning("Failed to import tree-sitter dependencies. Parser will not work.")

# Configure logging
logging.basicConfig(level=logging.INFO)
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
        if not ts_cpp or not Language:
            raise ParseError("tree-sitter or tree-sitter-cpp not cached/installed correctly.")

        try:
            CPP_LANGUAGE = Language(ts_cpp.language())
            self.parser = Parser(CPP_LANGUAGE)
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
            CPP_LANGUAGE = Language(ts_cpp.language())
            func_query = CPP_LANGUAGE.query("(function_definition) @func")
            # captures(node) returns Dict[str, List[Node]] in newer bindings
            captures = func_query.captures(root_node)

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

    def _extract_function_name(self, func_def_node: Node) -> Optional[str]:
        """
        Extracts the function name from a function_definition node.
        """
        declarator = func_def_node.child_by_field_name("declarator")
        if not declarator:
            return None
        
        curr = declarator
        while curr:
            if curr.type == "identifier":
                return curr.text.decode("utf8")
            elif curr.type == "function_declarator":
                curr = curr.child_by_field_name("declarator")
            elif curr.type == "parenthesized_declarator":
                 curr = curr.child_by_field_name("declarator")
            elif curr.type == "pointer_declarator" or curr.type == "reference_declarator":
                 curr = curr.child_by_field_name("declarator")
            elif curr.type == "field_identifier":
                 return curr.text.decode("utf8")
            else:
                break 
        
        if declarator.type == "function_declarator":
             inner_decl = declarator.child_by_field_name("declarator")
             if inner_decl and inner_decl.type == "qualified_identifier":
                 return inner_decl.text.decode("utf8")

        return None

    def _extract_function_calls(self, root_node: Node) -> Set[str]:
        """
        Extracts names of functions called within a given node scope.
        """
        calls: Set[str] = set()
        
        CPP_LANGUAGE = Language(ts_cpp.language())
        call_query = CPP_LANGUAGE.query("(call_expression) @call")
        
        captures = call_query.captures(root_node)
        
        if isinstance(captures, dict):
            for name, nodes in captures.items():
                for node in nodes:
                     func_node = node.child_by_field_name("function")
                     if func_node:
                        call_name = func_node.text.decode("utf8")
                        calls.add(call_name)
        else:
            for node, _ in captures:
                 func_node = node.child_by_field_name("function")
                 if func_node:
                    call_name = func_node.text.decode("utf8")
                    calls.add(call_name)

        return calls
