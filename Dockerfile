# Local Code Interpreter Tool
# Multi-stage build for Python application with optional Hyperlight support
#
# Build with Hyperlight support:
#   docker build --build-arg WITH_HYPERLIGHT=true -t local-code-interpreter:hyperlight .
#
# Build without Hyperlight (default, faster):
#   docker build -t local-code-interpreter:latest .

# =============================================================================
# Stage 1: Build hyperlight-nanvix (only when WITH_HYPERLIGHT=true)
# =============================================================================
FROM python:3.12-slim AS hyperlight-builder

ARG WITH_HYPERLIGHT=false

# Install build dependencies only if building hyperlight
RUN if [ "$WITH_HYPERLIGHT" = "true" ]; then \
        apt-get update && apt-get install -y --no-install-recommends \
            curl \
            build-essential \
            pkg-config \
            libssl-dev \
        && rm -rf /var/lib/apt/lists/* \
        && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
        && . $HOME/.cargo/env \
        && pip install maturin; \
    fi

# Copy hyperlight-nanvix source
COPY vendor/hyperlight-nanvix /hyperlight-nanvix

# Build hyperlight-nanvix wheel if WITH_HYPERLIGHT is true
WORKDIR /hyperlight-nanvix
RUN if [ "$WITH_HYPERLIGHT" = "true" ]; then \
        . $HOME/.cargo/env && \
        maturin build --release --out /wheels && \
        cargo build --release --bin hyperlight-nanvix && \
        ./target/release/hyperlight-nanvix --setup-registry; \
    else \
        mkdir -p /wheels; \
    fi

# =============================================================================
# Stage 2: Runtime image
# =============================================================================
FROM python:3.12-slim AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user with writable home directory for cache
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser

WORKDIR /app

# Install dependencies first (for better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install hyperlight-nanvix wheel if it was built
COPY --from=hyperlight-builder /wheels /wheels
RUN if [ "$(ls -A /wheels/*.whl 2>/dev/null)" ]; then \
        pip install --no-cache-dir /wheels/*.whl; \
    fi && rm -rf /wheels

# Copy pre-warmed cache from builder (kernel.elf, qjs, python3)
COPY --from=hyperlight-builder /root/.cache/nanvix-registry /home/appuser/.cache/nanvix-registry

# Copy application source
COPY setup.py pyproject.toml ./
COPY src/ ./src/

# Install the application
RUN pip install --no-cache-dir -e .

# Create cache directory for Hyperlight with proper permissions
RUN mkdir -p /home/appuser/.cache && chown -R appuser:appuser /home/appuser

# Switch to non-root user
USER appuser

# Expose DevUI port
EXPOSE 8090

# Environment variable to enable Hyperlight executor (set to "true" to enable)
ENV ENABLE_HYPERLIGHT=""

# Default entrypoint runs DevUI server bound to 0.0.0.0 for container access
# Use shell form to allow environment variable expansion
ENTRYPOINT ["/bin/sh", "-c", "python -m local_code_interpreter --devui --port=8090 --host=0.0.0.0 --no-browser ${ENABLE_HYPERLIGHT:+--hyperlight}"]
