# Local Code Interpreter Tool - Claude Code Guide

## Project Overview

A local code interpreter tool built with the [Microsoft Agent Framework](https://github.com/microsoft/agent-framework). It provides sandboxed code execution capabilities for AI agents.

## Claude Code Skill

This project includes a `/execute-code` skill for running code in a secure Hyperlight VM sandbox.

### Quick Execute (JavaScript)
```bash
. .venv/bin/activate && python3 -c "
import asyncio
from local_code_interpreter.tools import CodeExecutionTool

async def run():
    tool = CodeExecutionTool(environment='hyperlight', hyperlight_language='javascript', approval_mode='never_require')
    return await tool._execute('console.log(2 + 2);')

print(asyncio.run(run()))
"
```

### Quick Execute (Python)
```bash
. .venv/bin/activate && python3 -c "
import asyncio
from local_code_interpreter.tools import CodeExecutionTool

async def run():
    tool = CodeExecutionTool(environment='hyperlight', hyperlight_language='python', approval_mode='never_require')
    return await tool._execute('print(sum(range(1, 101)))')

print(asyncio.run(run()))
"
```

## Quick Start

```bash
# 1. Setup (creates venv and installs dependencies including hyperlight-nanvix)
just setup

# 2. Configure environment
cp .env.example .env
# Edit .env with your OpenAI API key or Azure OpenAI configuration

# 3. Run
just run                      # Demo mode with Python subprocess
just run hyperlight           # Demo mode with Hyperlight VM sandbox (JavaScript)
just run hyperlight python    # Demo mode with Hyperlight VM sandbox (Python)
just interactive              # Interactive chat mode
just interactive hyperlight   # Interactive with Hyperlight
just devui                    # Web interface on http://localhost:8090
```

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

```bash
# Code quality
just format       # Format with black
just lint         # Lint with ruff
just lint-fix     # Auto-fix lint issues
just typecheck    # Type check with mypy
just check        # Run all quality checks

# Testing
just test         # Run tests
just test-ci      # Tests with coverage reports

# Build
just build        # Build package
just clean        # Clean artifacts
```

## Configuration

Priority order: Anthropic > Azure OpenAI > OpenAI

### Anthropic (Recommended for Claude Code users)
```env
ANTHROPIC_API_KEY="your-api-key"
ANTHROPIC_MODEL_ID="claude-sonnet-4-20250514"
```

### OpenAI
```env
OPENAI_API_KEY="your-api-key"
OPENAI_RESPONSES_MODEL_ID="gpt-4o-mini"
```

### Azure OpenAI
```env
AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME="gpt-4o"
# Optional: AZURE_OPENAI_API_KEY for local dev, otherwise use `az login`
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

## Testing Hyperlight Directly

```python
from hyperlight_nanvix import NanvixSandbox, SandboxConfig
import asyncio

async def test():
    config = SandboxConfig(log_directory='/tmp', tmp_directory='/tmp')
    sandbox = NanvixSandbox(config)

    # Write test code to file
    with open('/tmp/test.js', 'w') as f:
        f.write('console.log("Hello from Hyperlight!");')

    result = await sandbox.run('/tmp/test.js')
    print(f"Success: {result.success}")

asyncio.run(test())
```

## Debug Mode

Enable detailed logging of code execution:
```bash
DEBUG=true just run hyperlight
```
