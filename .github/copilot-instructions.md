# Local Code Interpreter Tool - Copilot Instructions

## Project Overview

A local code interpreter tool built with the [Microsoft Agent Framework](https://github.com/microsoft/agent-framework). It provides sandboxed code execution capabilities for AI agents.

## Architecture

```
src/local_code_interpreter/
├── __init__.py       # Package initialization
├── __main__.py       # CLI entry point
├── tools.py          # CodeExecutionTool - the core execution logic
└── agent.py          # ChatAgent setup, CLI, and DevUI
```

### Key Components

- **CodeExecutionTool** (`tools.py`): The main tool class that executes code. Supports two environments:
  - `python`: Fast subprocess execution (default)
  - `hyperlight`: VM-isolated sandbox using hyperlight-nanvix (JavaScript or Python)

- **create_interpreter_agent** (`agent.py:185`): Factory function that creates a configured ChatAgent with the code execution tool.

**Key pattern**: Tools are defined once in `tools.py` and imported by the agent. When adding new capabilities, add the tool function to `tools.py` first, then register it in the agent's `tools=[]` list.

## Execution Environments

### Python Subprocess (default)
- Fast execution in isolated subprocess
- Output captured via stdout/stderr
- Configurable timeout (default 30s)
- Environment stripped for security

### Hyperlight VM Sandbox
- Uses [hyperlight-nanvix](https://github.com/hyperlight-dev/hyperlight-nanvix) for VM-level isolation
- Supports JavaScript (default) and Python
- Requires Linux with KVM support (`/dev/kvm`)
- Higher security for untrusted code execution

## Development Commands

This project uses [just](https://github.com/casey/just) as a task runner. All commands automatically use the virtual environment.

```bash
# Initial setup (creates venv and installs deps)
just setup
cp .env.example .env  # Configure API keys

# Run agent (auto-detects OpenAI vs Azure based on env vars)
just run          # Run with example queries
just interactive  # Interactive chat mode

# Code quality
just format       # Format with black
just lint         # Lint with ruff
just lint-fix     # Auto-fix lint issues
just typecheck    # Type check with mypy
just check        # Run all quality checks

# Testing
just test         # Run tests
just test-ci      # Tests with coverage reports

# Build & CI
just build        # Build package
just clean        # Clean artifacts
just ci           # Run full CI pipeline locally
just pre-commit   # Validate before committing

# Utilities
just              # Show all available commands
just info         # Show environment info
just tree         # Show project structure
```

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

Then register in the agent's `tools=[]` list in `agent.py`.

## Configuration

The agent auto-detects which backend to use based on environment variables:

- **OpenAI** (default): Set `OPENAI_API_KEY` in `.env`
- **Azure OpenAI**: Set `AZURE_OPENAI_ENDPOINT` in `.env`, then run `az login`

## Code Conventions

- All agents use `async/await` with `asyncio.run(main())`
- Agent instructions are stored in `INTERPRETER_AGENT_INSTRUCTIONS` constants
- Use `load_dotenv()` at module level before creating clients
- Tool return values should be human-readable strings
- Azure agent uses `AzureCliCredential()` - no API keys stored

## Docker & Kubernetes

```bash
# Docker
just docker-build              # Build image
just docker-build-hyperlight   # Build with Hyperlight support
just docker-run                # Run container

# Kubernetes (requires Azure setup)
just k8s-deploy                # Deploy to AKS
just k8s-deploy-hyperlight     # Deploy with Hyperlight
just k8s-status                # Check deployment
just k8s-logs                  # View logs
just k8s-port-forward          # Port forward to localhost:8090
```

## Debug Mode

Enable detailed logging of code execution:
```bash
DEBUG=true just run hyperlight
```

## Agents

You can find agents at https://github.com/github/awesome-copilot/tree/main/agents and should be installed in `.github/agents`