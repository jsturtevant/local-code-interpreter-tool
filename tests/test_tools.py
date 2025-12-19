"""Tests for Local Code Interpreter Tools"""

import pytest

from local_code_interpreter.tools import (
    CodeExecutionTool,
    HYPERLIGHT_AVAILABLE,
    _run_python,
)


class TestRunPython:
    """Tests for _run_python backend function."""

    @pytest.mark.asyncio
    async def test_executes_simple_code(self):
        result = await _run_python("print('hello world')", timeout=5)
        assert "hello world" in result

    @pytest.mark.asyncio
    async def test_captures_stdout(self):
        result = await _run_python("print('stdout test')", timeout=5)
        assert "stdout test" in result

    @pytest.mark.asyncio
    async def test_captures_stderr(self):
        result = await _run_python("import sys; sys.stderr.write('stderr test')", timeout=5)
        assert "stderr test" in result

    @pytest.mark.asyncio
    async def test_timeout_kills_process(self):
        result = await _run_python("import time; time.sleep(10)", timeout=1)
        assert "timed out" in result.lower()
        assert "1s" in result

    @pytest.mark.asyncio
    async def test_handles_syntax_error(self):
        result = await _run_python("this is not valid python!", timeout=5)
        assert "SyntaxError" in result or "Error" in result

    @pytest.mark.asyncio
    async def test_handles_runtime_error(self):
        result = await _run_python("raise ValueError('test error')", timeout=5)
        assert "ValueError" in result or "test error" in result

    @pytest.mark.asyncio
    async def test_truncates_large_output(self):
        result = await _run_python("print('x' * 20000)", timeout=5)
        assert len(result) <= 10100  # 10KB + truncation message
        assert "truncated" in result.lower()


class TestCodeExecutionToolPython:
    """Tests for CodeExecutionTool with python environment."""

    def test_creates_with_default_settings(self):
        tool = CodeExecutionTool()
        assert tool.name == "execute_code"
        assert tool.environment == "python"
        assert tool.timeout == 30
        assert tool.approval_mode == "always_require"

    def test_creates_with_custom_timeout(self):
        tool = CodeExecutionTool(timeout=60)
        assert tool.timeout == 60

    def test_creates_with_never_require_approval(self):
        tool = CodeExecutionTool(approval_mode="never_require")
        assert tool.approval_mode == "never_require"

    def test_has_description(self):
        tool = CodeExecutionTool()
        assert "Python" in tool.description

    @pytest.mark.asyncio
    async def test_execute_simple_code(self):
        tool = CodeExecutionTool(timeout=5, approval_mode="never_require")
        result = await tool._execute(code="print(2 + 2)")
        assert "4" in result

    @pytest.mark.asyncio
    async def test_execute_respects_timeout(self):
        tool = CodeExecutionTool(timeout=1, approval_mode="never_require")
        result = await tool._execute(code="import time; time.sleep(10)")
        assert "timed out" in result.lower()


class TestCodeExecutionToolHyperlight:
    """Tests for CodeExecutionTool with hyperlight environment."""

    def test_hyperlight_available(self):
        """Verify hyperlight-nanvix module is installed."""
        assert HYPERLIGHT_AVAILABLE is True

    def test_creates_with_hyperlight_environment(self):
        tool = CodeExecutionTool(environment="hyperlight")
        assert tool.name == "execute_code"
        assert tool.environment == "hyperlight"
        assert tool.approval_mode == "always_require"

    def test_creates_with_custom_directories(self):
        tool = CodeExecutionTool(
            environment="hyperlight",
            log_directory="/tmp/hyperlight-logs",
            tmp_directory="/tmp/hyperlight-tmp",
        )
        assert tool.log_directory == "/tmp/hyperlight-logs"
        assert tool.tmp_directory == "/tmp/hyperlight-tmp"

    def test_has_hyperlight_description(self):
        tool = CodeExecutionTool(environment="hyperlight")
        assert "sandbox" in tool.description.lower() or "hyperlight" in tool.description.lower()

    @pytest.mark.asyncio
    async def test_hyperlight_execute_returns_result(self):
        """Test that execute returns the expected output."""
        tool = CodeExecutionTool(environment="hyperlight", approval_mode="never_require")
        result = await tool._execute(code='print("hello")')
        assert "hello" in result

    @pytest.mark.asyncio
    async def test_hyperlight_execute_simple_code(self):
        """Test that hyperlight executes Python and returns output."""
        tool = CodeExecutionTool(environment="hyperlight", approval_mode="never_require")
        result = await tool._execute(code="print(2 + 2)")
        assert "4" in result
