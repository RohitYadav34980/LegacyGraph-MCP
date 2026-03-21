# Contributing to LegacyGraph-MCP

Thank you for your interest in contributing! This guide covers the development standards, workflow, and conventions used in this project.

---

## 🚀 Getting Started

### 1. Fork & Clone
```bash
git clone https://github.com/YOUR_USERNAME/LegacyGraph-MCP.git
cd LegacyGraph-MCP
```

### 2. Install Dependencies
```bash
pip install poetry
poetry install
```

### 3. Verify Setup
```bash
python -m pytest tests/ -v    # All 20 tests should pass
python tools/verifier.py      # 100% accuracy expected
```

---

## 📁 Project Structure

Before contributing, understand where your code belongs:

| Directory | Purpose | When to modify |
|---|---|---|
| `src/core/` | Graph model, C++ parser | Adding new analysis algorithms |
| `src/tools/` | MCP tool functions | Adding new tools or modifying tool behavior |
| `src/utils/` | Config, logging, services, helpers | Infrastructure changes |
| `src/server.py` | MCP registration, server card | Adding/removing tool registrations |
| `tests/` | Pytest test suite | **Always** — every change needs tests |

### Dependency Direction (enforced)
```
tools/ → utils/ → core/
```
Never import from `tools/` in `core/` or `utils/`. Never import from `utils/` in `core/`.

---

## 🧑‍💻 Development Standards

### Type Safety
- **Strict `mypy`** is enforced (`strict = true` in `pyproject.toml`)
- All functions must have complete type annotations
- Use `Optional[T]` and `Union[T1, T2]` for nullable/variant types

### Docstrings
Follow **Google-style** docstrings:
```python
def get_callers(function_name: str) -> str:
    """
    List upstream functions that call the given function.

    Args:
        function_name: Exact name of the function.

    Returns:
        Comma-separated list of caller function names.

    Raises:
        GraphError: If the function is not found in the graph.
    """
```

### Code Style
- **Formatter:** Black (`line-length = 88`)
- **Linter:** Ruff (`target-version = "py311"`)
- Run before committing:
```bash
poetry run black src/ tests/
poetry run ruff check src/ tests/
poetry run mypy src/
```

---

## 🧪 Testing

### Running Tests
```bash
# Full suite
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# End-to-end verifier
python tools/verifier.py
```

### Writing Tests
- Add tests to `tests/test_core.py` (or create new test files for new modules)
- Use pytest fixtures for shared setup (`parser`, `graph`)
- Cover edge cases: empty input, invalid syntax, mode guards, error paths
- Tests must be self-contained — never depend on external network or disk state

### Test Categories
| Category | Examples |
|---|---|
| Unit | Parser extraction, graph operations |
| Integration | `analyze_codebase` with raw files |
| Mode Guards | Cloud mode rejects `directory_path` |
| Error Handling | Missing functions, empty graphs |

---

## 🔀 Git Workflow

### Branch Naming
```
feature/add-template-parsing
fix/resolve-parser-timeout
docs/update-architecture
refactor/extract-tool-functions
```

### Commit Protocol
Follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Usage |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code change that neither fixes a bug nor adds a feature |
| `test:` | Adding or correcting tests |
| `chore:` | Build process, CI, dependency updates |

**Examples:**
```
feat: add C++ template parameter parsing
fix: resolve timeout on large repos (>500 files)
refactor: extract tool functions into src/tools/ package
docs: update ARCHITECTURE.md with data flow diagrams
test: add edge case for empty call graph
```

---

## 📋 Pull Request Checklist

Before submitting a PR, verify:

- [ ] All existing tests pass (`python -m pytest tests/ -v`)
- [ ] New tests added for your changes
- [ ] Type checking passes (`mypy src/`)
- [ ] Code formatted (`black src/ tests/`)
- [ ] Linting passes (`ruff check src/ tests/`)
- [ ] Documentation updated if public API changed
- [ ] Conventional commit messages used
- [ ] PR description explains *what* and *why*

---

## 🏷️ Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** — Breaking API changes (tool signatures, config format)
- **MINOR** — New tools, new features, backward-compatible
- **PATCH** — Bug fixes, documentation updates

Version is defined in `pyproject.toml` under `[tool.poetry] version`.

---

## ❓ Questions?

Open a [GitHub Issue](https://github.com/RohitYadav34980/LegacyGraph-MCP/issues) or start a Discussion.
