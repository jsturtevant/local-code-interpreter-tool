# Local Code Interpreter Tool - Agent Context

## Overview

This is a local code interpreter tool built with the [Microsoft Agent Framework](https://github.com/microsoft/agent-framework). It provides AI-powered assistance for executing code, testing snippets, and running calculations in sandboxed environments.

## Architecture

```
src/local_code_interpreter/
├── __init__.py      # Package initialization
├── __main__.py      # Entry point for `python -m local_code_interpreter`
├── agent.py         # Main agent implementation with OpenAI/Azure OpenAI support
└── tools.py         # Code execution tools (Python subprocess and Hyperlight VM)
```

### Key Components

- **ChatAgent**: Main agent class from Microsoft Agent Framework that handles conversation and tool invocation
- **CodeExecutionTool**: Custom AIFunction that executes code in sandboxed environments
- **RetryOnRateLimitMiddleware**: Middleware that handles rate limiting with exponential backoff

### Execution Environments

1. **Python subprocess** (default): Fast execution with timeout protection
2. **Hyperlight VM sandbox**: High-security VM-isolated execution using [hyperlight-nanvix](https://github.com/hyperlight-dev/hyperlight-nanvix), supports JavaScript and Python

## Development Commands

This project uses [just](https://github.com/casey/just) as a task runner. All commands automatically use the virtual environment.

```bash
# Initial setup (creates venv and installs deps)
just setup

# Run agent modes
just run              # Demo mode with example queries
just interactive      # Interactive chat mode
just devui            # Web-based DevUI interface

# Code quality
just format           # Format with black
just lint             # Lint with ruff
just lint-fix         # Auto-fix lint issues
just typecheck        # Type check with mypy
just check            # Run all quality checks

# Testing
just test             # Run tests
just test-ci          # Tests with coverage and XML output

# Build
just build            # Build package
just clean            # Clean artifacts
```

## Configuration

The agent auto-detects which backend to use based on environment variables:

| Backend | Required Environment Variables |
|---------|-------------------------------|
| OpenAI | `OPENAI_API_KEY` |
| Azure OpenAI | `AZURE_OPENAI_ENDPOINT` + `az login` or `AZURE_OPENAI_API_KEY` |

Copy `.env.example` to `.env` and configure appropriately.

## Adding New Tools

Tools use Pydantic `Annotated` types for parameter descriptions:

```python
# In tools.py
from typing import Annotated
from pydantic import Field

def my_new_tool(
    param: Annotated[str, Field(description="What this parameter does")],
) -> str:
    """Docstring becomes the tool description shown to the LLM."""
    return "result string"
```

Then register in the agent's `tools=[]` list.

## Code Conventions

- Async/await pattern with `asyncio.run(main())` for entry points
- Agent instructions stored in `INTERPRETER_AGENT_INSTRUCTIONS_*` module-level constants
- Use `load_dotenv()` at module level before creating clients
- Tool return values should be human-readable strings
- Use type hints throughout (Python 3.12+ syntax)

## Project Dependencies

- **Python 3.12+** required
- **just** task runner
- **Rust nightly** (for hyperlight-nanvix)

### Key Python packages

- `agent-framework`: Microsoft Agent Framework
- `agent-framework-devui`: Web-based testing interface
- `azure-identity`: Azure authentication
- `pydantic`: Type validation and descriptions
- `tenacity`: Retry logic

### Dev dependencies

- `pytest`, `pytest-asyncio`, `pytest-cov`: Testing
- `black`: Code formatting
- `ruff`: Linting
- `mypy`: Type checking
- `bandit`: Security scanning

## Docker & Kubernetes

The project supports containerized deployment:

```bash
just docker-build              # Build container
just docker-run                # Run locally
just k8s-deploy                # Deploy to Kubernetes with workload identity
```

See the README.md for detailed Azure/Kubernetes deployment instructions.

## Test Structure

Tests are located in `tests/` and use pytest with pytest-asyncio for async tests:

```
tests/
├── __init__.py
└── test_tools.py    # Tests for CodeExecutionTool and execution backends
```

Run tests with: `just test`
