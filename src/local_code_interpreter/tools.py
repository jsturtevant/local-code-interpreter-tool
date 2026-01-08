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

# Type alias for hyperlight language options
HyperlightLanguage = Literal["javascript", "python"]

# Set up logging - only log errors, let Agent Framework handle tracing
logger = logging.getLogger(__name__)


def _format_debug_output(label: str, content: str, max_preview: int = 1000) -> str:
    """Format content for readable debug logging."""
    truncated = len(content) > max_preview
    preview = content[:max_preview] if truncated else content
    truncation_note = f"\n    ... [truncated, {len(content)} total chars]" if truncated else ""
    
    # Indent each line for readability
    indented = "\n".join(f"    {line}" for line in preview.splitlines())
    
    return f"\n{'=' * 60}\n{label}\n{'=' * 60}\n{indented}{truncation_note}\n{'=' * 60}"


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
    logger.debug(f"Executing Python code:\n{code}")

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
        stdout_str = stdout.decode()
        stderr_str = stderr.decode()
        logger.debug(f"stdout: {stdout_str!r}")
        logger.debug(f"stderr: {stderr_str!r}")
        output = stdout_str + stderr_str
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
    sandbox: "NanvixSandbox",
    tmp_directory: str,
    language: HyperlightLanguage = "javascript",
) -> str:
    """Execute code in a hyperlight-nanvix VM sandbox.

    Args:
        code: The code to execute.
        sandbox: The NanvixSandbox instance.
        tmp_directory: Directory for temporary files.
        language: The language of the code - 'javascript' or 'python'.

    Returns:
        The execution output or error message.
    """
    workload_dir = os.path.join(tmp_directory, "hyperlight-workloads")
    os.makedirs(workload_dir, exist_ok=True)

    # Use appropriate file extension based on language
    extension = "py" if language == "python" else "js"
    filename = f"workload_{uuid.uuid4().hex[:8]}.{extension}"
    workload_path = os.path.join(workload_dir, filename)
    stdout_capture_path = os.path.join(tmp_directory, f"stdout_{uuid.uuid4().hex[:8]}.txt")

    try:
        with open(workload_path, "w") as f:
            f.write(code)

        # Capture stdout at fd level since hyperlight writes directly to fd 1
        original_stdout_fd = os.dup(1)
        try:
            with open(stdout_capture_path, "w") as capture_file:
                os.dup2(capture_file.fileno(), 1)
                sys.stdout.flush()
                try:
                    result: WorkloadResult = await sandbox.run(workload_path)
                finally:
                    sys.stdout.flush()
                    os.dup2(original_stdout_fd, 1)

            with open(stdout_capture_path, "r") as f:
                captured_stdout = f.read().strip()
        finally:
            os.close(original_stdout_fd)
            if os.path.exists(stdout_capture_path):
                try:
                    os.remove(stdout_capture_path)
                except OSError:
                    pass

        if result.success:
            return captured_stdout if captured_stdout else "Execution completed successfully."
        else:
            error_msg = result.error or "Unknown error"
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

    For hyperlight environment, you can choose the language:
    - 'javascript': Execute JavaScript code (default for hyperlight)
    - 'python': Execute Python code in the hyperlight VM sandbox

    Examples:
        .. code-block:: python

            from local_code_interpreter.tools import CodeExecutionTool

            # Python subprocess (default) - fast, for trusted code
            code_tool = CodeExecutionTool()

            # Python with custom timeout
            code_tool = CodeExecutionTool(timeout=60)

            # Hyperlight VM sandbox with JavaScript (default)
            code_tool = CodeExecutionTool(
                environment="hyperlight",
                log_directory="/tmp/hyperlight-logs",
            )

            # Hyperlight VM sandbox with Python
            code_tool = CodeExecutionTool(
                environment="hyperlight",
                hyperlight_language="python",
            )
    """

    def __init__(
        self,
        *,
        environment: Literal["python", "hyperlight"] = "python",
        timeout: int = 30,
        log_directory: Optional[str] = None,
        tmp_directory: Optional[str] = None,
        hyperlight_language: HyperlightLanguage = "javascript",
        approval_mode: Literal["always_require", "never_require"] = "always_require",
        **kwargs,
    ) -> None:
        """Initialize the CodeExecutionTool.

        Keyword Args:
            environment: 'python' (subprocess) or 'hyperlight' (VM sandbox).
            timeout: Execution timeout in seconds (python env only). Defaults to 30.
            log_directory: Directory for sandbox logs (hyperlight env only).
            tmp_directory: Directory for temporary files (hyperlight env only).
            hyperlight_language: Language for hyperlight env - 'javascript' or 'python'.
                Defaults to 'javascript'. Only used when environment='hyperlight'.
            approval_mode: Whether approval is required. Defaults to "always_require".

        Raises:
            ImportError: If environment='hyperlight' but hyperlight-nanvix not installed.
        """
        self.environment = environment
        self.timeout = timeout
        self.log_directory = log_directory or tempfile.gettempdir()
        self.tmp_directory = tmp_directory or tempfile.gettempdir()
        self.hyperlight_language = hyperlight_language
        self._sandbox: Optional["NanvixSandbox"] = None

        if environment == "hyperlight" and not HYPERLIGHT_AVAILABLE:
            raise ImportError(
                "hyperlight-nanvix is not installed. "
                "Install from: cd hyperlight-nanvix && maturin develop --features python"
            )

        if environment == "hyperlight":
            lang_name = "Python" if hyperlight_language == "python" else "JavaScript"
            description = (
                f"Execute {lang_name} code in a secure hyperlight-nanvix sandbox "
                "with VM-level isolation."
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
    ) -> str:
        """Execute the provided code.

        Args:
            code: The source code to execute.

        Returns:
            The execution output or result message.
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(_format_debug_output("INPUT SCRIPT", code))

        try:
            if self.environment == "hyperlight":
                sandbox = self._get_sandbox()
                result = await _run_hyperlight(
                    code, sandbox, self.tmp_directory, self.hyperlight_language
                )
            else:
                result = await _run_python(code, self.timeout)

            # Ensure we always return a non-empty string
            if not result:
                result = "(No output)"

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(_format_debug_output("EXECUTION RESULT", result))

            return result
        except Exception as e:
            error_msg = f"Error executing code: {e}"
            logger.exception(error_msg)
            return error_msg

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
