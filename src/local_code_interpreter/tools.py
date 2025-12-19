# Copyright (c) Microsoft. All rights reserved.

"""
Local Code Interpreter Tools

Shared tool functions for code interpreter agents.
These can be used with any agent configuration (OpenAI, Azure OpenAI, etc.)
"""

import asyncio
import logging
import os
import sys
import tempfile
import uuid
from typing import Annotated, Literal, Optional

from agent_framework import AIFunction
from pydantic import Field

# Set up logging - only log errors, let Agent Framework handle tracing
logger = logging.getLogger(__name__)

# Try to import hyperlight-nanvix (optional dependency)
try:
    from hyperlight_nanvix import (  # type: ignore[import-untyped]
        NanvixSandbox,
        SandboxConfig,
        WorkloadResult,
    )

    HYPERLIGHT_AVAILABLE = True
except ImportError:
    HYPERLIGHT_AVAILABLE = False
    NanvixSandbox = None  # type: ignore[assignment]
    SandboxConfig = None  # type: ignore[assignment]
    WorkloadResult = None  # type: ignore[assignment]


# =============================================================================
# Execution Backends
# =============================================================================

MAX_OUTPUT_SIZE = 10000  # 10KB truncation limit


async def _run_python(code: str, timeout: int) -> str:
    """Execute Python code in a sandboxed subprocess.

    Args:
        code: Python code to execute.
        timeout: Execution timeout in seconds.

    Returns:
        The combined stdout and stderr output, truncated if necessary.
    """
    # Use sys.executable to get the absolute path to the Python interpreter
    # This avoids needing PATH in the environment
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={},  # Stripped environment for security
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = (stdout + stderr).decode()
        if len(output) > MAX_OUTPUT_SIZE:
            return output[:MAX_OUTPUT_SIZE] + "\n... [output truncated]"
        return output
    except asyncio.TimeoutError:
        proc.kill()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            pass
        return f"Error: Execution timed out after {timeout}s"


async def _run_hyperlight(
    code: str,
    language: str,
    sandbox: "NanvixSandbox",
    tmp_directory: str,
) -> str:
    """Execute code in a hyperlight-nanvix VM sandbox."""
    ext_map = {
        "javascript": ".js",
        "js": ".js",
        "python": ".py",
        "py": ".py",
        "c": ".c",
        "cpp": ".cpp",
        "c++": ".cpp",
    }

    ext = ext_map.get(language.lower())
    if ext is None:
        return f"Error: Unsupported language '{language}'. Supported: javascript, python, c, cpp"

    workload_dir = os.path.join(tmp_directory, "hyperlight-workloads")
    os.makedirs(workload_dir, exist_ok=True)

    filename = f"workload_{uuid.uuid4().hex[:8]}{ext}"
    workload_path = os.path.join(workload_dir, filename)

    try:
        with open(workload_path, "w") as f:
            f.write(code)

        result: WorkloadResult = await sandbox.run(workload_path)

        if result.success:
            # Try to get actual output
            output: str | None = None
            if hasattr(result, "stdout") and result.stdout:
                output = str(result.stdout)
            elif hasattr(result, "output") and result.output:
                output = str(result.output)

            if output:
                return output
            else:
                return "Execution completed successfully."
        else:
            error_msg: str = str(
                getattr(result, "error", None) or getattr(result, "stderr", None) or "Unknown error"
            )
            logger.error(f"Hyperlight execution failed: {error_msg}")
            return f"Execution failed: {error_msg}"

    except Exception as e:
        logger.exception(f"Exception during hyperlight sandbox execution: {e}")
        return f"Error during sandbox execution: {e}"

    finally:
        try:
            if os.path.exists(workload_path):
                os.remove(workload_path)
        except OSError:
            pass


# =============================================================================
# Code Execution Tool
# =============================================================================


class CodeExecutionTool(AIFunction):
    """A tool for executing code in a sandboxed environment.

    This tool supports multiple execution environments:
    - 'python': Run Python code in an isolated subprocess (fast, medium security)
    - 'hyperlight': Run code in a VM-isolated Nanvix sandbox (slower, high security)

    Examples:
        .. code-block:: python

            from local_code_interpreter.tools import CodeExecutionTool

            # Python subprocess (default) - fast, for trusted code
            code_tool = CodeExecutionTool()

            # Python with custom timeout
            code_tool = CodeExecutionTool(timeout=60)

            # Hyperlight VM sandbox - secure, for untrusted code
            code_tool = CodeExecutionTool(
                environment="hyperlight",
                log_directory="/tmp/hyperlight-logs",
            )

            # Hyperlight supports multiple languages (javascript, python, c, cpp)
            code_tool = CodeExecutionTool(environment="hyperlight")
    """

    def __init__(
        self,
        *,
        environment: Literal["python", "hyperlight"] = "python",
        timeout: int = 30,
        log_directory: Optional[str] = None,
        tmp_directory: Optional[str] = None,
        approval_mode: Literal["always_require", "never_require"] = "always_require",
        **kwargs,
    ) -> None:
        """Initialize the CodeExecutionTool.

        Keyword Args:
            environment: 'python' (subprocess) or 'hyperlight' (VM sandbox).
            timeout: Execution timeout in seconds (python env only). Defaults to 30.
            log_directory: Directory for sandbox logs (hyperlight env only).
            tmp_directory: Directory for temporary files (hyperlight env only).
            approval_mode: Whether approval is required. Defaults to "always_require".

        Raises:
            ImportError: If environment='hyperlight' but hyperlight-nanvix not installed.
        """
        self.environment = environment
        self.timeout = timeout
        self.log_directory = log_directory or tempfile.gettempdir()
        self.tmp_directory = tmp_directory or tempfile.gettempdir()
        self._sandbox: Optional["NanvixSandbox"] = None

        if environment == "hyperlight" and not HYPERLIGHT_AVAILABLE:
            raise ImportError(
                "hyperlight-nanvix is not installed. "
                "Install from: cd hyperlight-nanvix && maturin develop --features python"
            )

        if environment == "hyperlight":
            description = (
                "Execute code in a secure hyperlight-nanvix sandbox with VM-level "
                "isolation. Supports JavaScript, Python, C, and C++ workloads. "
                "Specify the 'language' parameter for non-Python code."
            )
        else:
            description = (
                "Execute Python code in an isolated subprocess and return the output. "
                "Use for calculations, testing code snippets, or verifying logic."
            )

        super().__init__(
            name="execute_code",
            description=description,
            approval_mode=approval_mode,
            func=self._execute,
            **kwargs,
        )

    def _get_sandbox(self) -> "NanvixSandbox":
        """Get or create the hyperlight sandbox instance."""
        if self._sandbox is None:
            try:
                config = SandboxConfig(
                    log_directory=self.log_directory,
                    tmp_directory=self.tmp_directory,
                )
                self._sandbox = NanvixSandbox(config)
            except Exception as e:
                logger.exception(f"Failed to create NanvixSandbox: {e}")
                raise
        return self._sandbox

    async def _execute(
        self,
        code: Annotated[str, Field(description="The code to execute")],
        language: Annotated[
            str,
            Field(description="Programming language: 'python', 'javascript', 'c', or 'cpp'"),
        ] = "python",
    ) -> str:
        """Execute the provided code.

        Args:
            code: The source code to execute.
            language: Programming language (hyperlight supports js/python/c/cpp).

        Returns:
            The execution output or result message.
        """
        if self.environment == "hyperlight":
            sandbox = self._get_sandbox()
            return await _run_hyperlight(code, language, sandbox, self.tmp_directory)
        else:
            if language.lower() not in ("python", "py"):
                return (
                    f"Error: Python environment only supports Python code. "
                    f"Use environment='hyperlight' for {language} support."
                )
            return await _run_python(code, self.timeout)

    async def clear_cache(self) -> str:
        """Clear the hyperlight sandbox binary cache."""
        if self.environment != "hyperlight":
            return "Cache clearing only applicable for hyperlight environment."

        try:
            sandbox = self._get_sandbox()
            await sandbox.clear_cache()
            return "Cache cleared successfully."
        except Exception as e:
            return f"Failed to clear cache: {e}"
