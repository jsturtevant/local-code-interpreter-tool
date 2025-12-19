# Task: Integrate hyperlight-nanvix Python SDK for Sandboxed Code Execution

## Status: ✅ COMPLETED

## Overview

Extend `CodeExecutionTool` with a `hyperlight` environment option that uses hyperlight-nanvix for VM-isolated code execution. Follows the Phase 2 pattern from the configurable code execution plan.

**Source:** [PR #20 - Add Python host SDK](https://github.com/hyperlight-dev/hyperlight-nanvix/pull/20)
- Branch: `danbugs/python-host-sdk`
- Repo: `hyperlight-dev/hyperlight-nanvix`

## Design

Single `CodeExecutionTool` with `environment` parameter (matching Phase 2 plan):

```python
# Python subprocess (default) - fast, for trusted code
CodeExecutionTool()

# Hyperlight VM sandbox - secure, for untrusted code
CodeExecutionTool(environment="hyperlight")

# Hyperlight with custom directories
CodeExecutionTool(
    environment="hyperlight",
    log_directory="/tmp/hyperlight-logs",
    tmp_directory="/tmp/hyperlight-tmp",
)
```

| Environment | Implementation | Security | Languages |
|-------------|----------------|----------|-----------|
| `python` | async subprocess with timeout, stripped env vars | Medium | Python only |
| `hyperlight` | Hyperlight VMM + Nanvix microkernel | High | JavaScript, Python, C, C++ |

## Implementation Summary

### Phase 1: Clone and Build hyperlight-nanvix

- [x] Clone hyperlight-nanvix to sibling directory
- [x] Checkout PR branch (`danbugs/python-host-sdk`)
- [x] Install maturin and build Python bindings

### Phase 2: Extend CodeExecutionTool

- [x] Add `_run_hyperlight()` backend function
- [x] Add `environment` parameter to `CodeExecutionTool`
- [x] Add `log_directory` and `tmp_directory` options
- [x] Dynamic description based on environment
- [x] Language parameter support for hyperlight

### Phase 3: Update Agent

- [x] Simplified `create_interpreter_agent(environment="python"|"hyperlight")`
- [x] Updated agent instructions

### Phase 4: Testing

- [x] 20 tests pass (7 python env, 6 hyperlight env, 7 backend)
- [x] Code quality checks pass

## Usage

```python
from local_code_interpreter import create_interpreter_agent, CodeExecutionTool

# Create agent with python environment (default)
agent = create_interpreter_agent()

# Create agent with hyperlight environment
agent = create_interpreter_agent(environment="hyperlight")

# Use tool directly
tool = CodeExecutionTool(environment="hyperlight", approval_mode="never_require")
result = await tool._execute(code='console.log("hello")', language="javascript")
```

## Files Modified

- [src/local_code_interpreter/tools.py](src/local_code_interpreter/tools.py) - Consolidated CodeExecutionTool
- [src/local_code_interpreter/agent.py](src/local_code_interpreter/agent.py) - Simplified agent creation
- [src/local_code_interpreter/__init__.py](src/local_code_interpreter/__init__.py) - Updated exports
- [tests/test_tools.py](tests/test_tools.py) - Updated tests

## API Reference (from PR #20)

### Python SDK Usage

```python
import asyncio
from hyperlight_nanvix import NanvixSandbox, SandboxConfig

async def main():
    config = SandboxConfig(
        log_directory="/tmp/hyperlight-nanvix",
        tmp_directory="/tmp/hyperlight-nanvix"
    )
    sandbox = NanvixSandbox(config)
    
    result = await sandbox.run('guest-examples/hello.js')
    if result.success:
        print('Execution completed')
    else:
        print(f'Error: {result.error}')

asyncio.run(main())
```

### WorkloadResult

```python
class WorkloadResult:
    success: bool
    error: Optional[str]
```

### SandboxConfig

```python
class SandboxConfig:
    log_directory: Optional[str]
    tmp_directory: Optional[str]
```

## Build Commands (from hyperlight-nanvix)

```bash
# One-time setup
pipx install maturin
pipx ensurepath

# Build Python bindings
python3 -m venv .venv && source .venv/bin/activate
maturin develop --features python

# Run example
python examples/python_sdk_example.py
```

## Notes

- hyperlight-nanvix uses Hyperlight VMM for lightweight VM isolation
- Supports JavaScript, Python, C, and C++ workloads
- The Python bindings use PyO3 with async support via pyo3-asyncio
- Requires Linux with KVM support for VM execution
