# Generic Code Execution Tool - Implementation Plan

## Overview

Add an `execute_code` tool to the Local Code Interpreter Tool that allows the LLM to run code with configurable execution environments. Implementation is split into two phases.

## Environments

| Environment | Implementation | Security | Use Case | Phase |
|-------------|----------------|----------|----------|-------|
| `python` | async subprocess with timeout, temp dir, stripped env vars | Medium | Quick scripts, development | 1 |
| `docker` | User-provided image with resource limits, no network | High | Untrusted code, production | 2 |

---

## Phase 1: Python Subprocess Execution

### 1.1 Add async execution backend to `tools.py`

```python
async def _run_python(code: str, timeout: int) -> str:
    """Execute Python code in a sandboxed subprocess."""
    proc = await asyncio.create_subprocess_exec(
        "python", "-c", code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={},  # Stripped environment
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = (stdout + stderr).decode()
        return output[:10000]  # Truncate large output
    except asyncio.TimeoutError:
        proc.kill()
        return f"Error: Execution timed out after {timeout}s"
```

### 1.2 Create `CodeExecutionTool` class

Follow the Agent Framework's `BaseTool` / `AIFunction` pattern to create a configurable tool class:

Use https://github.com/microsoft/agent-framework/blob/b0a7a1fcb8c6830ed8194320715cd5278faf46b1/python/packages/core/agent_framework/_tools.py as an example on how to create.

```python
from agent_framework import AIFunction

class CodeExecutionTool(AIFunction):
    """A tool for executing code in a sandboxed environment.
    
    Examples:
        .. code-block:: python
        
            from local_code_interpreter.tools import CodeExecutionTool
            
            # Create with default settings (30s timeout)
            code_tool = CodeExecutionTool()
            
            # Create with custom timeout
            code_tool = CodeExecutionTool(timeout=60)
    """
    
    def __init__(
        self,
        *,
        timeout: int = 30,
        approval_mode: Literal["always_require", "never_require"] = "always_require",
        **kwargs,
    ) -> None:
        """Initialize the CodeExecutionTool.
        
        Keyword Args:
            timeout: Execution timeout in seconds. Defaults to 30.
            approval_mode: Whether approval is required. Defaults to "always_require".
        """
        self.timeout = timeout
        
        super().__init__(
            name="execute_code",
            description=(
                "Execute Python code in a sandboxed environment and return the output. "
                "Use this tool when you need to run calculations, test code snippets, "
                "or verify logic. The code runs in an isolated subprocess with no "
                "network access and limited permissions."
            ),
            approval_mode=approval_mode,
            func=self._execute,
            **kwargs,
        )
    
    async def _execute(
        self,
        code: Annotated[str, Field(description="Python code to execute")],
    ) -> str:
        return await _run_python(code, self.timeout)
```

Usage in agent:
```python
tools=[CodeExecutionTool(timeout=30)]
```

The `approval_mode="always_require"` default ensures human confirmation before executing any LLM-generated code.

### 1.3 Update `agent.py`

- Import and register the `execute_code` tool
- Add instructions explaining when to use code execution

### 1.4 Add tests

- Test successful execution
- Test timeout handling
- Test output truncation
- Test error capture (stderr)

### Phase 1 Files to Modify

- `src/local_code_interpreter/tools.py`
- `src/local_code_interpreter/agent.py`
- `tests/test_tools.py`

---

## Phase 2: Docker Container Execution

### 2.1 Add Docker execution backend

```python
async def _run_docker(code: str, image: str, timeout: int) -> str:
    """Execute code in a Docker container with resource limits."""
    # Implementation using docker-py or subprocess with docker CLI
```

### 2.2 Extend `CodeExecutionTool` with environment switching

```python
class CodeExecutionTool(AIFunction):
    """A tool for executing code in a sandboxed environment.
    
    Examples:
        .. code-block:: python
        
            from local_code_interpreter.tools import CodeExecutionTool
            
            # Python subprocess (default)
            code_tool = CodeExecutionTool()
            
            # Docker container
            code_tool = CodeExecutionTool(
                environment="docker",
                image="python:3.12-slim",
                timeout=60,
            )
            
            # Node.js in Docker
            node_tool = CodeExecutionTool(
                environment="docker",
                image="node:20-slim",
            )
    """
    
    def __init__(
        self,
        *,
        environment: Literal["python", "docker"] = "python",
        image: str = "python:3.12-slim",
        timeout: int = 30,
        approval_mode: Literal["always_require", "never_require"] = "always_require",
        **kwargs,
    ) -> None:
        """Initialize the CodeExecutionTool.
        
        Keyword Args:
            environment: 'python' (subprocess) or 'docker' (container). Defaults to 'python'.
            image: Docker image for container execution. Defaults to 'python:3.12-slim'.
            timeout: Execution timeout in seconds. Defaults to 30.
            approval_mode: Whether approval is required. Defaults to "always_require".
        """
        self.environment = environment
        self.image = image
        self.timeout = timeout
        
        super().__init__(
            name="execute_code",
            description=(
                "Execute code in a sandboxed environment and return the output. "
                "Use this tool when you need to run calculations, test code snippets, "
                "or verify logic."
            ),
            approval_mode=approval_mode,
            func=self._execute,
            **kwargs,
        )
    
    async def _execute(
        self,
        code: Annotated[str, Field(description="Code to execute")],
    ) -> str:
        if self.environment == "docker":
            return await _run_docker(code, self.image, self.timeout)
        return await _run_python(code, self.timeout)
```

Usage in agent:
```python
tools=[CodeExecutionTool(environment="docker", image="node:20-slim")]
```

### 2.3 Update `requirements.txt`

- Add `docker` package for container support (optional dependency)

### Phase 2 Files to Modify

- `src/local_code_interpreter/tools.py`
- `requirements.txt`

---

## Design Decisions

### Tool vs Middleware

Two approaches were evaluated for implementing code execution:

| Approach | Description |
|----------|-------------|
| **Tool** | Register `execute_python` as a callable tool the LLM invokes explicitly |
| **Middleware** | Intercept LLM responses, detect code blocks, execute automatically |

### Why Tool Was Chosen

| Factor | Tool ✅ | Middleware ❌ |
|--------|---------|---------------|
| **Audit trail** | Every execution logged as tool call with input/output | Silent execution, harder to trace |
| **LLM control** | Model decides when to execute vs show examples | Must rely on delimiter heuristics (`tool_code` vs `python`) |
| **Loop handling** | Agent Framework handles result→LLM loop automatically | Must manually re-invoke LLM with execution results |
| **Security** | Explicit opt-in per execution | Implicit execution of any detected code |
| **Simplicity** | Single function, follows existing patterns | Custom processor class, response interception logic |

### Middleware Pattern

Some frameworks like Google ADK use a middleware approach (via `BaseLlmResponseProcessor`) where code execution is handled by:
1. Parsing LLM output for code block delimiters
2. Extracting and executing code
3. Constructing a new message with results
4. Re-invoking the LLM to continue the conversation

This pattern works well in those frameworks but doesn't align with the Agent Framework's architecture, which handles steps 3-4 automatically when using tools. The tool-based approach is the idiomatic pattern for the Agent Framework.

### When Middleware Makes Sense

- Legacy models without tool calling support (rare today)
- Automatic execution without LLM deciding (less safe)
- Framework-level code execution across all agents

### Why `AIFunction` Subclass for Configuration

The Agent Framework uses class-based tools (e.g., `HostedCodeInterpreterTool`, `HostedWebSearchTool`) that extend `BaseTool` or `AIFunction`. This pattern:

- Matches the framework's existing tool architecture
- Provides clear constructor-based configuration 
- Supports serialization via `SerializationMixin`
- Enables IDE autocompletion and type hints for configuration options

| Approach | When to Use |
|----------|-------------|
| `AIFunction` subclass | Configurable tools with multiple settings (like `CodeExecutionTool`) |
| `@ai_function` decorator | Simple stateless functions (like `get_weather`) |
| `**kwargs` injection | Dynamic per-request context (user_id, auth tokens) |

### Why `approval_mode="always_require"`

Code execution is a high-risk operation. The Agent Framework's approval workflow pauses before executing and requires human confirmation. This provides:

- Human-in-the-loop safety for arbitrary code
- Audit trail of what was approved
- Ability to reject suspicious code before execution

## Security Considerations

- Python mode: stripped environment variables, temp directory, process timeout
- Docker mode: no network, memory/CPU limits, read-only filesystem where possible
- Both: capture stdout/stderr, truncate large outputs
