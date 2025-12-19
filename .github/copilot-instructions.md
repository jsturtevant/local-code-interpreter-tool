# Local Code Interpreter Tool - Copilot Instructions

## Project Overview

This is a local code interpreter tool built with the [Microsoft Agent Framework](https://github.com/microsoft/agent-framework). It provides AI-powered assistance for executing code, testing snippets, and running calculations.

## Architecture

```
src/local_code_interpreter/
├── tools.py          # Shared tool functions (all agents import from here)
└── agent.py          # Interpreter agent (auto-detects OpenAI vs Azure OpenAI)
```

**Key pattern**: Tools are defined once in `tools.py` and imported by the agent. When adding new capabilities, add the tool function to `tools.py` first, then register it in the agent's `tools=[]` list.

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

just test-ci      # Tests with XML output for CI

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

Then register in the agent:
```python
from .tools import my_new_tool

ChatAgent(
    tools=[..., my_new_tool],
)
```

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

## Git Worktrees

This project uses Git worktrees. The `main/` directory is the main worktree:
```bash
git worktree add -b feature-name ../local-code-interpreter-tool/feature-name
git worktree list
```

## Agents

You can find agents at https://github.com/github/awesome-copilot/tree/main/agents and should be installed in `.github/agents`