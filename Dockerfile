# Local Code Interpreter Tool
# Multi-stage build for Python application with optional Hyperlight support

FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first (for better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY setup.py pyproject.toml ./
COPY src/ ./src/

# Install the application
RUN pip install --no-cache-dir -e .

# Use existing nobody user (UID 65534) for security
USER nobody

# Expose DevUI port
EXPOSE 8090

# Default entrypoint runs DevUI server bound to 0.0.0.0 for container access
ENTRYPOINT ["python", "-m", "local_code_interpreter", "--devui", "--port=8090", "--host=0.0.0.0", "--no-browser"]

# Override CMD to add --hyperlight when needed
CMD []
