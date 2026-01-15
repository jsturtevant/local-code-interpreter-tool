"""Tests for shared module components."""

import pytest
from unittest.mock import AsyncMock

from local_code_interpreter.shared import (
    get_instructions,
    RetryOnRateLimitMiddleware,
    INTERPRETER_AGENT_INSTRUCTIONS_PYTHON,
    INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT_JS,
    INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT_PY,
)


class TestGetInstructions:
    """Tests for get_instructions() function."""

    def test_returns_python_instructions_for_python_environment(self):
        """Default python environment returns Python subprocess instructions."""
        result = get_instructions(environment="python")
        assert result == INTERPRETER_AGENT_INSTRUCTIONS_PYTHON
        assert "Python" in result
        assert "print()" in result

    def test_returns_python_instructions_by_default(self):
        """With no arguments, returns Python instructions."""
        result = get_instructions()
        assert result == INTERPRETER_AGENT_INSTRUCTIONS_PYTHON

    def test_returns_hyperlight_js_instructions(self):
        """Hyperlight with JavaScript language returns JS instructions."""
        result = get_instructions(environment="hyperlight", hyperlight_language="javascript")
        assert result == INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT_JS
        assert "JavaScript" in result
        assert "console.log()" in result

    def test_returns_hyperlight_python_instructions(self):
        """Hyperlight with Python language returns Python VM instructions."""
        result = get_instructions(environment="hyperlight", hyperlight_language="python")
        assert result == INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT_PY
        assert "Python" in result
        assert "VM-isolated sandbox" in result
        assert "print()" in result

    def test_hyperlight_defaults_to_javascript(self):
        """Hyperlight environment defaults to JavaScript language."""
        result = get_instructions(environment="hyperlight")
        assert result == INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT_JS

    def test_hyperlight_language_ignored_for_python_environment(self):
        """hyperlight_language parameter is ignored when environment is python."""
        result = get_instructions(environment="python", hyperlight_language="python")
        assert result == INTERPRETER_AGENT_INSTRUCTIONS_PYTHON


class TestRetryOnRateLimitMiddleware:
    """Tests for RetryOnRateLimitMiddleware class."""

    def test_initialization_with_default_parameters(self):
        """Middleware initializes with sensible defaults."""
        middleware = RetryOnRateLimitMiddleware()
        assert middleware.max_retries == 5
        assert middleware.min_wait == 1.0
        assert middleware.max_wait == 60.0

    def test_initialization_with_custom_parameters(self):
        """Middleware accepts custom retry configuration."""
        middleware = RetryOnRateLimitMiddleware(
            max_retries=3,
            min_wait=0.5,
            max_wait=30.0,
        )
        assert middleware.max_retries == 3
        assert middleware.min_wait == 0.5
        assert middleware.max_wait == 30.0

    @pytest.mark.asyncio
    async def test_passes_through_on_success(self):
        """Middleware calls next() and succeeds when no error occurs."""
        middleware = RetryOnRateLimitMiddleware()
        mock_context = object()  # Simple placeholder for ChatContext
        mock_next = AsyncMock()

        await middleware.process(mock_context, mock_next)

        mock_next.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_retries_on_429_error(self):
        """Middleware retries when 429 rate limit error occurs."""
        middleware = RetryOnRateLimitMiddleware(
            max_retries=2,
            min_wait=0.01,  # Very short wait for faster tests
            max_wait=0.02,
        )
        mock_context = object()

        # Create a mock that fails once with 429, then succeeds
        call_count = 0

        async def mock_next_with_retry(context):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("429 Too Many Requests")
            # Success on second call

        await middleware.process(mock_context, mock_next_with_retry)

        assert call_count == 2  # Initial call + 1 retry

    @pytest.mark.asyncio
    async def test_retries_on_too_many_requests_message(self):
        """Middleware retries when exception message starts with 'too many requests'.

        Note: The regex uses re.match() which only matches from the start of the string,
        so the message must begin with 'too many requests' or '429'.
        """
        middleware = RetryOnRateLimitMiddleware(
            max_retries=2,
            min_wait=0.01,
            max_wait=0.02,
        )
        mock_context = object()

        call_count = 0

        async def mock_next_with_retry(context):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Too Many Requests: please slow down")
            # Success on second call

        await middleware.process(mock_context, mock_next_with_retry)

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_does_not_retry_on_other_errors(self):
        """Middleware does not retry on non-rate-limit errors."""
        middleware = RetryOnRateLimitMiddleware(
            max_retries=3,
            min_wait=0.01,
            max_wait=0.02,
        )
        mock_context = object()

        call_count = 0

        async def mock_next_with_error(context):
            nonlocal call_count
            call_count += 1
            raise Exception("Some other error")

        with pytest.raises(Exception, match="Some other error"):
            await middleware.process(mock_context, mock_next_with_error)

        assert call_count == 1  # Should not retry

    @pytest.mark.asyncio
    async def test_gives_up_after_max_retries(self):
        """Middleware gives up after max_retries attempts."""
        middleware = RetryOnRateLimitMiddleware(
            max_retries=2,
            min_wait=0.01,
            max_wait=0.02,
        )
        mock_context = object()

        call_count = 0

        async def mock_next_always_429(context):
            nonlocal call_count
            call_count += 1
            raise Exception("429 Rate Limited")

        with pytest.raises(Exception, match="429"):
            await middleware.process(mock_context, mock_next_always_429)

        # max_retries=2 means 3 total attempts (initial + 2 retries)
        assert call_count == 3
