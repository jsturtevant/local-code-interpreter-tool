# Copyright (c) Microsoft. All rights reserved.

"""
Local Code Interpreter Tools

Shared tool functions for code interpreter agents.
These can be used with any agent configuration (OpenAI, Azure OpenAI, etc.)
"""

import asyncio
import sys
from typing import Annotated, Literal

from agent_framework import AIFunction
from pydantic import Field


# =============================================================================
# Code Execution Backend
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
            pass  # Process is truly stuck
        return f"Error: Execution timed out after {timeout}s"


class CodeExecutionTool(AIFunction):
    """A tool for executing Python code in a sandboxed environment.

    This tool runs Python code in an isolated subprocess with:
    - Stripped environment variables (no access to secrets)
    - Configurable timeout protection
    - Output truncation for large responses

    Examples:
        .. code-block:: python

            from local_code_interpreter.tools import CodeExecutionTool

            # Create with default settings (30s timeout, requires approval)
            code_tool = CodeExecutionTool()

            # Create with custom timeout
            code_tool = CodeExecutionTool(timeout=60)

            # Create without approval requirement (use with caution!)
            code_tool = CodeExecutionTool(approval_mode="never_require")
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
            approval_mode: Whether approval is required before execution.
                Defaults to "always_require" for safety.
        """
        self.timeout = timeout

        super().__init__(
            name="execute_code",
            description=(
                "Execute Python code in an isolated subprocess and return the output. "
                "Use this tool when you need to run calculations, test code snippets, "
                "or verify logic. The code runs with no environment variables but has "
                "filesystem access. Use for trusted operations only."
            ),
            approval_mode=approval_mode,
            func=self._execute,
            **kwargs,
        )

    async def _execute(
        self,
        code: Annotated[str, Field(description="Python code to execute")],
    ) -> str:
        """Execute the provided Python code.

        Args:
            code: Python code to execute.

        Returns:
            The execution output (stdout + stderr).
        """
        return await _run_python(code, self.timeout)
