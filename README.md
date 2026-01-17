# McKinsey LegacyX MCP Server

Legacy-MCP-Analyzer is a Model Context Protocol (MCP) Server designed to help AI agents understand and analyze legacy C++ codebases. It parses C++ code into a dependency graph and provides tools to query the code structure, enabling questions like "What functions call `calculate_risk()`?" or "Detect circular dependencies."

## Features

- **Robust Parsing:** Uses `tree-sitter` for fault-tolerant parsing of C++ code, handling syntax errors gracefully.
- **Dependency Analysis:** Builds a directed graph of function calls using `networkx`.
- **Cycle Detection:** Identifies circular dependencies in the codebase.
- **MCP Interface:** Exposes analysis tools via the Model Context Protocol.
- **Type Safe:** Fully typed Python codebase passing `mypy --strict`.

## Installation

This project uses [Poetry](https://python-poetry.org/) for dependency management.

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd Legacy-MCP-Analyzer
    ```

2.  **Install dependencies:**
    ```bash
    poetry install
    ```

## Usage

### Running the MCP Server

To run the MCP server:

```bash
poetry run python -m src.server
```

### Running Tests

To run the comprehensive test suite:

```bash
poetry run pytest tests/
```

## Architecture

The project is structured into three main layers:

1.  **Ingestion Layer (`src/parser.py`)**: Responsible for parsing C++ source code and extracting function definitions and calls using `tree-sitter`.
2.  **Graph Layer (`src/graph.py`)**: Manages the dependency graph, providing methods for topological sorting, cycle detection, and querying upstream/downstream dependencies.
3.  **Interface Layer (`src/server.py`)**: The MCP server implementation that exposes the graph analysis capabilities as tools to AI agents.

## Development

- **Linting:** `poetry run ruff check .`
- **Formatting:** `poetry run black .`
- **Type Checking:** `poetry run mypy .`
