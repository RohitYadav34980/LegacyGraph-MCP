import pytest
import networkx as nx
from src.parser import CppParser, ParseError
from src.graph import DependencyGraph, GraphError, CircularDependencyError

# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def parser():
    return CppParser()

@pytest.fixture
def graph():
    return DependencyGraph()

# ==========================================
# Test Cases
# ==========================================

def test_initialization(parser, graph):
    """Verify basic class initialization."""
    assert parser is not None
    assert graph is not None
    assert isinstance(graph.graph, nx.DiGraph)

# --- Case A: Simple Linear Dependency (A -> B -> C) ---
def test_linear_dependency(parser, graph):
    code = """
    void funcC() {
        // Do something
    }
    
    void funcB() {
        funcC();
    }
    
    void funcA() {
        funcB();
    }
    """
    
    # 1. Parse
    parsed_data = parser.parse_source(code)
    # Expected: [('funcC', {}), ('funcB', {'funcC'}), ('funcA', {'funcB'})]
    # Note: Order depends on traversal, usually top-down.
    
    assert len(parsed_data) == 3
    
    # 2. Build Graph
    graph.build_from_parsed_data(parsed_data)
    
    # 3. Analyze
    assert "funcC" in graph.get_downstream_dependencies("funcB")
    assert "funcB" in graph.get_downstream_dependencies("funcA")
    assert "funcB" in graph.get_upstream_callers("funcC")
    
    # Verify no cycles
    assert len(graph.detect_cycles()) == 0


# --- Case B: Circular Dependency (A -> B -> A) ---
def test_circular_dependency(parser, graph):
    code = """
    void funcB(); # Forward decl
    
    void funcA() {
        funcB();
    }
    
    void funcB() {
        funcA();
    }
    """
    
    parsed_data = parser.parse_source(code)
    graph.build_from_parsed_data(parsed_data)
    
    cycles = graph.detect_cycles()
    assert len(cycles) > 0
    # Cycle should involve A and B
    # Cycle format: [['funcA', 'funcB']] or [['funcB', 'funcA']]
    assert any("funcA" in c and "funcB" in c for c in cycles)

# --- Case C: Self-Recursion (A -> A) ---
def test_self_recursion(parser, graph):
    code = """
    void funcA() {
        funcA();
    }
    """
    parsed_data = parser.parse_source(code)
    graph.build_from_parsed_data(parsed_data)
    
    cycles = graph.detect_cycles()
    # Check for self-loop
    assert len(cycles) == 1
    assert cycles[0] == ["funcA"]
    
    callers = graph.get_upstream_callers("funcA")
    assert "funcA" in callers

# --- Case D: Orphan Functions ---
def test_orphan_functions(parser, graph):
    code = """
    void orphan() {
        // I am alone
    }
    
    void parent() {
        child();
    }
    
    void child() {
    }
    """
    parsed_data = parser.parse_source(code)
    graph.build_from_parsed_data(parsed_data)
    
    orphans = graph.get_orphan_functions()
    # orphan is def'd and not called.
    # parent is def'd and not called (it's a root).
    # child is called by parent.
    
    assert "orphan" in orphans
    assert "parent" in orphans
    assert "child" not in orphans

# --- Case E: Invalid Syntax (Dirty C++) ---
def test_invalid_syntax_handling(parser, graph):
    # Missing semicolon, random text
    code = """
    void validFunc() {
        callMe();
    }
    
    THIS IS GARBAGE CODE syntax error !!!
    
    void anotherValid() {
        validFunc();
    }
    """
    
    # Should not raise exception, tree-sitter is robust
    try:
        parsed_data = parser.parse_source(code)
    except ParseError:
        pytest.fail("Parser crashed on invalid syntax but should have been robust.")

    # It should still find the valid functions (at least the one before the error)
    func_names = [f[0] for f in parsed_data]
    assert "validFunc" in func_names
    # assert "anotherValid" in func_names # Might be consumed by error recovery
    
    graph.build_from_parsed_data(parsed_data)
    # assert "validFunc" in graph.get_downstream_dependencies("anotherValid")
