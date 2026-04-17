# --- Builder Stage ---
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

ENV PATH="$POETRY_HOME/bin:$PATH"

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /build

# Copy only dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (without dev)
RUN poetry install --only main --no-root

# --- Runner Stage ---
FROM python:3.11-slim AS runner

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/user/app/.venv/bin:$PATH" \
    MCP_MODE=cloud \
    PORT=7860

# Install runtime dependencies (git for ingestion)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user/app

# Copy virtualenv from builder
COPY --from=builder --chown=user /build/.venv /home/user/app/.venv
# Copy source code
COPY --chown=user src /home/user/app/src
# Copy README (important for HF Spaces metadata)
COPY --chown=user README.md /home/user/app/

# Expose port (default for HF Spaces)
EXPOSE 7860

# Default command for cloud mode (SSE transport)
CMD ["python", "-m", "src", "--mode", "cloud", "--transport", "sse", "--port", "7860"]
