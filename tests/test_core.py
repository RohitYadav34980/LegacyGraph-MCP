import os
import tempfile
from pathlib import Path
import pytest
import networkx as nx
from src.core.parser import CppParser, ParseError
from src.core.graph import DependencyGraph

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
# Original Test Cases (updated for filepath parameter)
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
    assert len(parsed_data) == 3
    
    # 2. Build Graph (with filepath)
    graph.build_from_parsed_data(parsed_data, filepath="test.cpp")
    
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
    graph.build_from_parsed_data(parsed_data, filepath="test.cpp")
    
    cycles = graph.detect_cycles()
    assert len(cycles) > 0
    assert any("funcA" in c and "funcB" in c for c in cycles)

# --- Case C: Self-Recursion (A -> A) ---
def test_self_recursion(parser, graph):
    code = """
    void funcA() {
        funcA();
    }
    """
    parsed_data = parser.parse_source(code)
    graph.build_from_parsed_data(parsed_data, filepath="test.cpp")
    
    cycles = graph.detect_cycles()
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
    graph.build_from_parsed_data(parsed_data, filepath="test.cpp")
    
    orphans = graph.get_orphan_functions()
    assert "orphan" in orphans
    assert "parent" in orphans
    assert "child" not in orphans

# --- Case E: Invalid Syntax (Dirty C++) ---
def test_invalid_syntax_handling(parser, graph):
    code = """
    void validFunc() {
        callMe();
    }
    
    THIS IS GARBAGE CODE syntax error !!!
    
    void anotherValid() {
        validFunc();
    }
    """
    
    try:
        parsed_data = parser.parse_source(code)
    except ParseError:
        pytest.fail("Parser crashed on invalid syntax but should have been robust.")

    func_names = [f[0] for f in parsed_data]
    assert "validFunc" in func_names
    
    graph.build_from_parsed_data(parsed_data, filepath="dirty.cpp")


# ==========================================
# Phase 1 Tests: File-Aware Features
# ==========================================

# --- Case F: File-Tagged Nodes ---
def test_file_tagged_nodes(parser, graph):
    """Nodes should carry the file attribute after build."""
    code = """
    void myFunc() {}
    """
    parsed_data = parser.parse_source(code)
    graph.build_from_parsed_data(parsed_data, filepath="src/core.cpp")

    attrs = graph.graph.nodes["myFunc"]
    assert attrs["file"] == "src/core.cpp"


# --- Case G: File Subgraph Isolation ---
def test_file_subgraph(parser, graph):
    """get_file_subgraph should return only nodes belonging to the given file."""
    code_a = """
    void alphaFunc() { betaFunc(); }
    """
    code_b = """
    void betaFunc() {}
    void gammaFunc() {}
    """
    parsed_a = parser.parse_source(code_a)
    parsed_b = parser.parse_source(code_b)

    graph.build_from_parsed_data(parsed_a, filepath="file_a.cpp")
    graph.build_from_parsed_data(parsed_b, filepath="file_b.cpp")

    sub_a = graph.get_file_subgraph("file_a.cpp")
    sub_b = graph.get_file_subgraph("file_b.cpp")

    assert "alphaFunc" in sub_a.nodes()
    assert "betaFunc" not in sub_a.nodes()

    assert "betaFunc" in sub_b.nodes()
    assert "gammaFunc" in sub_b.nodes()
    assert "alphaFunc" not in sub_b.nodes()


# --- Case H: Cross-File Dependencies ---
def test_cross_file_dependencies(parser, graph):
    """get_cross_file_dependencies should find calls between different files."""
    code_main = """
    void main() { helperA(); }
    """
    code_helpers = """
    void helperA() {}
    """
    parsed_main = parser.parse_source(code_main)
    parsed_helpers = parser.parse_source(code_helpers)

    graph.build_from_parsed_data(parsed_main, filepath="main.cpp")
    graph.build_from_parsed_data(parsed_helpers, filepath="helpers.cpp")

    cross = graph.get_cross_file_dependencies()
    assert len(cross) > 0

    # Should contain main -> helperA across files
    found = any(
        caller == "main" and callee == "helperA"
        and cf == "main.cpp" and ef == "helpers.cpp"
        for caller, cf, callee, ef in cross
    )
    assert found, f"Expected cross-file dep main->helperA, got: {cross}"


# --- Case I: No Cross-File Dependencies in Single File ---
def test_no_cross_file_deps_single_file(parser, graph):
    """All calls within a single file should not appear as cross-file deps."""
    code = """
    void inner() {}
    void outer() { inner(); }
    """
    parsed = parser.parse_source(code)
    graph.build_from_parsed_data(parsed, filepath="single.cpp")

    cross = graph.get_cross_file_dependencies()
    assert len(cross) == 0


# --- Case J: Export IDE Graph to Disk ---
def test_export_ide_graph(parser, graph):
    """export_ide_graph should create a .md file with Mermaid content."""
    from src.tools.export import export_ide_graph
    import src.utils.services as services
    import src.utils.config as config

    # Force local mode for this test
    config.MCP_MODE = "local"

    code = """
    void render() { draw(); }
    void draw() {}
    """
    parsed = parser.parse_source(code)
    services.graph_service.build_from_parsed_data(parsed, filepath="gfx.cpp")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "test_graph.md")
        result = export_ide_graph(output_filename=out_file)

        assert "written" in result.lower() or "success" in result.lower() or "test_graph.md" in result
        assert os.path.exists(out_file)

        content = open(out_file, encoding="utf-8").read()
        assert "mermaid" in content
        assert "graph TD" in content
        assert "render" in content
        assert "draw" in content


# --- Case K: Empty Subgraph ---
def test_file_subgraph_empty(graph):
    """Querying a file with no functions should return an empty subgraph."""
    sub = graph.get_file_subgraph("nonexistent.cpp")
    assert len(sub.nodes()) == 0


# ==========================================
# Phase 2-4 Tests: Hybrid Architecture
# ==========================================

# --- Case L: analyze_codebase with raw_files ---
def test_analyze_codebase_raw_files():
    """analyze_codebase should accept raw_files and build the graph."""
    from src.tools.analysis import analyze_codebase
    from src.utils.helpers import _get_raw_files_project_id
    import src.utils.services as services

    raw = [
        {"filename": "main.cpp", "content": "void main() { helper(); }"},
        {"filename": "utils.cpp", "content": "void helper() {}"},
    ]
    result = analyze_codebase(raw_files=raw)

    assert "error" not in result.lower()
    # "2" appears either in "Analyzed 2 raw files" (cache miss) or "Tracking 2 functions" (cache hit)
    assert "2" in result

    # Look up the pool graph using the same deterministic target_id
    target_id = _get_raw_files_project_id(raw)
    nodes = services.graph_pool.get_graph(target_id).get_all_nodes()
    assert "main" in nodes
    assert "helper" in nodes


# --- Case M: analyze_codebase with directory_path (local) ---
def test_analyze_codebase_directory_path_local():
    """analyze_codebase with directory_path should work in local mode."""
    import hashlib
    from src.tools.analysis import analyze_codebase
    import src.utils.config as config
    import src.utils.services as services

    config.MCP_MODE = "local"

    with tempfile.TemporaryDirectory() as tmpdir:
        cpp_file = os.path.join(tmpdir, "test.cpp")
        with open(cpp_file, "w") as f:
            f.write("void foo() { bar(); }\nvoid bar() {}\n")

        result = analyze_codebase(directory_path=tmpdir)

        assert "error" not in result.lower()
        # "1" appears in "Analyzed local workspace..." or node count
        assert "1" in result

        # Compute deterministic target_id to look up the pool graph
        target_id = hashlib.sha256(tmpdir.encode()).hexdigest()[:8]
        nodes = services.graph_pool.get_graph(target_id).get_all_nodes()
        assert "foo" in nodes
        assert "bar" in nodes



# --- Case N: analyze_codebase rejects directory_path in cloud mode ---
def test_analyze_codebase_cloud_rejects_directory_path():
    """Cloud mode should reject directory_path."""
    from src.tools.analysis import analyze_codebase
    import src.utils.config as config

    config.MCP_MODE = "cloud"

    result = analyze_codebase(directory_path="/some/local/path")
    assert "error" in result.lower()
    assert "cloud" in result.lower()

    # Reset to local
    config.MCP_MODE = "local"


# --- Case O: analyze_codebase with no input ---
def test_analyze_codebase_no_input():
    """analyze_codebase with no arguments should return an error."""
    from src.tools.analysis import analyze_codebase

    result = analyze_codebase()
    assert "error" in result.lower()


# --- Case P: analyze_codebase patch_content without repo_url ---
def test_analyze_codebase_patch_without_repo():
    """patch_content without repo_url should fail."""
    from src.tools.analysis import analyze_codebase

    result = analyze_codebase(patch_content="diff --git ...")
    assert "error" in result.lower()
    assert "repo_url" in result.lower()


# --- Case Q: generate_mermaid_graph inline ---
def test_generate_mermaid_graph():
    """generate_mermaid_graph should return a Mermaid string, not write a file."""
    from src.tools.export import generate_mermaid_graph
    from src.tools.analysis import analyze_codebase

    # Populate graph
    raw = [{"filename": "a.cpp", "content": "void alpha() { beta(); }\nvoid beta() {}"}]
    analyze_codebase(raw_files=raw)

    result = generate_mermaid_graph()

    assert "mermaid" in result
    assert "graph TD" in result
    assert "alpha" in result
    assert "beta" in result


# --- Case R: generate_mermaid_graph with focus_node ---
def test_generate_mermaid_graph_with_focus():
    """generate_mermaid_graph with focus_node should limit output."""
    from src.tools.export import generate_mermaid_graph
    from src.tools.analysis import analyze_codebase

    raw = [
        {"filename": "a.cpp", "content": "void a() { b(); }\nvoid b() { c(); }\nvoid c() {}"},
    ]
    analyze_codebase(raw_files=raw)

    result = generate_mermaid_graph(focus_node="a", max_depth=1)

    assert "mermaid" in result
    assert "a" in result
    assert "b" in result


# --- Case S: export_ide_graph blocked in cloud mode ---
def test_export_ide_graph_blocked_in_cloud():
    """export_ide_graph should refuse in cloud mode."""
    from src.tools.export import export_ide_graph
    import src.utils.config as config

    config.MCP_MODE = "cloud"
    result = export_ide_graph(output_filename="dummy.md")
    assert "error" in result.lower()
    assert "local" in result.lower()

    # Reset
    config.MCP_MODE = "local"


def test_scan_directory_incremental_cache_handles_modify_and_delete():
    """_scan_directory should reuse cache and drop deleted-file nodes."""
    from src.utils.helpers import _scan_directory
    import src.utils.services as services

    original_graph_service = services.graph_service
    services.graph_service = DependencyGraph()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            a_cpp = workspace / "a.cpp"
            b_cpp = workspace / "b.cpp"

            a_cpp.write_text("void main() { helper(); }\n", encoding="utf-8")
            b_cpp.write_text("void helper() {}\n", encoding="utf-8")

            files_parsed_1, files_skipped_1, node_count_1 = _scan_directory(workspace)
            assert files_parsed_1 == 2
            assert files_skipped_1 == 0
            assert node_count_1 >= 2
            assert (workspace / ".legacygraph.json").exists()

            files_parsed_2, files_skipped_2, node_count_2 = _scan_directory(workspace)
            assert files_parsed_2 == 0
            assert files_skipped_2 == 0
            assert node_count_2 == node_count_1

            a_cpp.write_text("void main() { logger(); }\n", encoding="utf-8")
            new_a_mtime = a_cpp.stat().st_mtime + 2
            os.utime(a_cpp, (new_a_mtime, new_a_mtime))

            b_cpp.unlink()

            c_cpp = workspace / "c.cpp"
            c_cpp.write_text("void logger() {}\n", encoding="utf-8")

            files_parsed_3, files_skipped_3, node_count_3 = _scan_directory(workspace)
            assert files_parsed_3 == 2
            assert files_skipped_3 == 0
            assert node_count_3 == 2

            nodes = set(services.graph_service.get_all_nodes())
            assert "main" in nodes
            assert "logger" in nodes
            assert "helper" not in nodes
            assert "b.cpp" not in services.graph_service.file_mtimes
    finally:
        services.graph_service = original_graph_service
