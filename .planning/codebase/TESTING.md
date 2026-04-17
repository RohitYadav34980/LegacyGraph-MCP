# Testing — LegacyGraph-MCP

Testing strategy and verification tools.

## Test Framework
- **Pytest**: Primary test runner.
- **Plugins**: `pytest-cov` for coverage reporting.

## Test Suite Categories
- **Core Tests**: Unit tests for `CppParser` and `DependencyGraph` using synthetic C++ snippets.
- **Tool Tests**: Integration tests for MCP tools using raw file ingestion.
- **Mode Guards**: Verification that tools are correctly restricted by `MCP_MODE`.
- **End-to-End (E2E)**: `tools/verifier.py` - an autonomous script that validates the server's accuracy against a known legacy project.

## Running Tests
```bash
# General suite
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=src

# E2E Verifier
python tools/verifier.py
```

## Performance Benchmarking
- A specific benchmark profile is used to test scalability with large repos (>50k files).
- Multi-core parsing performance is measured in terms of `files/s` throughput.
