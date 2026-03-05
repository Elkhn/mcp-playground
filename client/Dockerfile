# Use Python 3.12 slim-bullseye
FROM python:3.12-slim-bullseye AS uv_base

# Environment variables
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-system \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/root/.local/bin:${PATH}"


# Install dependencies required for building and uv
RUN apt-get update -y && \
    apt-get install --no-install-recommends -y \
        curl \
        clang \
        git \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install uv (official installer)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Set working directory
WORKDIR /app

# Copy only dependency manifests to leverage Docker layer caching
COPY pyproject.toml .

# Install Python dependencies with uv
RUN uv sync --no-dev

# Copy actual application code
COPY . .