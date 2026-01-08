# Copyright (c) Microsoft. All rights reserved.

"""
Local Code Interpreter Agent

A local code interpreter agent using the Microsoft Agent Framework.
Supports both OpenAI and Azure OpenAI backends.

Configuration:
- For OpenAI: Set OPENAI_API_KEY in .env
- For Azure OpenAI: Set AZURE_OPENAI_ENDPOINT in .env and run `az login`
"""

import asyncio
import logging
import os
from typing import Awaitable, Callable

from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_message,
    stop_after_attempt,
    wait_exponential_jitter,
)
from agent_framework import AIFunction, ChatAgent, ChatContext, ChatMiddleware
from agent_framework.openai import OpenAIResponsesClient

from .tools import CodeExecutionTool, HyperlightLanguage, HYPERLIGHT_AVAILABLE

# Load environment variables from .env file
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)


def _is_azure_configured() -> bool:
    """Check if Azure OpenAI is configured."""
    return bool(os.getenv("AZURE_OPENAI_ENDPOINT"))


def _create_chat_client():
    """Create the appropriate chat client based on environment configuration."""
    if _is_azure_configured():
        from agent_framework.azure import AzureOpenAIResponsesClient

        # Check for API key first (local dev), then fall back to DefaultAzureCredential (Kubernetes)
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if api_key:
            return AzureOpenAIResponsesClient(api_key=api_key)
        else:
            from azure.identity import DefaultAzureCredential

            return AzureOpenAIResponsesClient(credential=DefaultAzureCredential())
    else:
        return OpenAIResponsesClient()


# =============================================================================
# Retry Middleware for Rate Limiting
# =============================================================================


class RetryOnRateLimitMiddleware(ChatMiddleware):
    """Chat middleware that retries on rate limit (429) errors with exponential backoff.

    Note: Agent Framework doesn't provide built-in retry middleware yet (as of preview).
    This uses tenacity for robust retry logic with exponential backoff and jitter.
    """

    def __init__(
        self,
        max_retries: int = 5,
        min_wait: float = 1.0,
        max_wait: float = 60.0,
    ):
        """Initialize the retry middleware.

        Args:
            max_retries: Maximum number of retry attempts.
            min_wait: Minimum wait time in seconds.
            max_wait: Maximum wait time in seconds.
        """
        self.max_retries = max_retries
        self.min_wait = min_wait
        self.max_wait = max_wait

    async def process(
        self,
        context: ChatContext,
        next: Callable[[ChatContext], Awaitable[None]],
    ) -> None:
        """Process the chat request with retry logic for rate limiting."""

        @retry(
            retry=retry_if_exception_message(match=r"(?i)(too many requests|429)"),
            stop=stop_after_attempt(self.max_retries + 1),
            wait=wait_exponential_jitter(initial=self.min_wait, max=self.max_wait),
            reraise=True,
        )
        async def _call_with_retry() -> None:
            await next(context)

        await _call_with_retry()


# =============================================================================
# Agent Configuration
# =============================================================================

INTERPRETER_AGENT_INSTRUCTIONS_PYTHON = """You are a Local Code Interpreter Assistant, helping users execute and test code.

Your capabilities include:
- Executing Python code in a sandboxed environment using the execute_code tool
- Testing code snippets and algorithms
- Running calculations and data processing

IMPORTANT: The execute_code tool captures stdout/stderr output. To see results:
- Always use print() to display values (e.g., print(2 + 2) not just 2 + 2)
- For expressions, wrap them in print() to see the output
- Without print(), calculations run silently with no visible result

When to use execute_code:
- When you need to perform calculations or verify mathematical results
- When you need to test a code snippet or algorithm
- When the user asks you to run or execute code
- When you need to process data or demonstrate functionality

Always be clear and concise. When reporting issues, include actionable recommendations.
If you need more information to help, ask clarifying questions.
"""

INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT_JS = """You are a Local Code Interpreter Assistant, helping users execute and test code.

Your capabilities include:
- Executing JavaScript code in a secure VM-isolated sandbox using the execute_code tool
- Testing code snippets and algorithms
- Running calculations and data processing

IMPORTANT: You are running in hyperlight mode which uses JavaScript. Always write JavaScript code, NOT Python.
- Use console.log() to display values (e.g., console.log(2 + 2) not just 2 + 2)
- For expressions, wrap them in console.log() to see the output
- Without console.log(), calculations run silently with no visible result

When to use execute_code:
- When you need to perform calculations or verify mathematical results
- When you need to test a code snippet or algorithm
- When the user asks you to run or execute code
- When you need to process data or demonstrate functionality

Always be clear and concise. When reporting issues, include actionable recommendations.
If you need more information to help, ask clarifying questions.
"""

INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT_PY = """You are a Local Code Interpreter Assistant, helping users execute and test code.

Your capabilities include:
- Executing Python code in a secure VM-isolated sandbox using the execute_code tool
- Testing code snippets and algorithms
- Running calculations and data processing

IMPORTANT: You are running in hyperlight mode with Python. The code executes in a VM-isolated sandbox.
- Use print() to display values (e.g., print(2 + 2) not just 2 + 2)
- For expressions, wrap them in print() to see the output
- Without print(), calculations run silently with no visible result

When to use execute_code:
- When you need to perform calculations or verify mathematical results
- When you need to test a code snippet or algorithm
- When the user asks you to run or execute code
- When you need to process data or demonstrate functionality

Always be clear and concise. When reporting issues, include actionable recommendations.
If you need more information to help, ask clarifying questions.
"""


def create_interpreter_agent(
    environment: str = "python",
    timeout: int = 30,
    hyperlight_language: HyperlightLanguage = "javascript",
    name: str = "code-interpreter",
    description: str | None = None,
) -> ChatAgent:
    """Create and configure the local code interpreter agent.

    Automatically uses Azure OpenAI if AZURE_OPENAI_ENDPOINT is set,
    otherwise uses OpenAI.

    Args:
        environment: Execution environment - 'python' or 'hyperlight'.
        timeout: Execution timeout in seconds (for python environment).
        hyperlight_language: Language for hyperlight - 'javascript' or 'python'.
        name: Agent name (used by DevUI).
        description: Agent description (used by DevUI).
    """
    if environment == "hyperlight" and not HYPERLIGHT_AVAILABLE:
        import warnings

        warnings.warn("hyperlight-nanvix is not installed. Falling back to python environment.")
        environment = "python"

    tools: list[AIFunction] = [
        CodeExecutionTool(
            environment=environment,  # type: ignore[arg-type]
            timeout=timeout,
            hyperlight_language=hyperlight_language,
            approval_mode="never_require",
        ),
    ]

    # Select instructions based on environment and language
    if environment == "hyperlight":
        instructions = (
            INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT_PY
            if hyperlight_language == "python"
            else INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT_JS
        )
    else:
        instructions = INTERPRETER_AGENT_INSTRUCTIONS_PYTHON

    backend = "Azure OpenAI" if _is_azure_configured() else "OpenAI"
    if description is None:
        if environment == "hyperlight":
            lang = "Python" if hyperlight_language == "python" else "JavaScript"
        else:
            lang = "Python"
        description = (
            f"Local Code Interpreter using {backend}. "
            f"Execute {lang} code in a sandboxed {environment} environment."
        )

    return ChatAgent(
        name=name,
        description=description,
        chat_client=_create_chat_client(),
        instructions=instructions,
        tools=tools,
        middleware=[
            RetryOnRateLimitMiddleware(
                max_retries=5,
                min_wait=1.0,
                max_wait=60.0,
            ),
        ],
    )


# =============================================================================
# Example Usage
# =============================================================================


async def run_interactive_session(
    environment: str = "python",
    hyperlight_language: HyperlightLanguage = "javascript",
) -> None:
    """Run an interactive chat session with the interpreter agent."""
    backend = "Azure OpenAI" if _is_azure_configured() else "OpenAI"
    if environment == "hyperlight":
        lang = "Python" if hyperlight_language == "python" else "JavaScript"
        env_info = f"hyperlight/{lang}"
    else:
        env_info = environment
    print("=" * 60)
    print(f"Local Code Interpreter Agent ({backend}, {env_info} environment)")
    print("Type 'quit' or 'exit' to end the session")
    print("=" * 60)
    print()

    agent = create_interpreter_agent(
        environment=environment,
        hyperlight_language=hyperlight_language,
    )

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                print("Goodbye!")
                break

            print("Agent: ", end="", flush=True)
            await run_streaming_with_retry(agent, user_input)
            print("\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


async def run_streaming_with_retry(
    agent: ChatAgent,
    query: str,
    max_retries: int = 5,
    min_wait: float = 2.0,
    max_wait: float = 60.0,
) -> None:
    """Run a streaming query with retry logic for rate limiting.

    The Agent Framework middleware doesn't handle streaming errors,
    so we wrap the entire streaming call with retry logic.
    """
    from agent_framework.exceptions import ServiceResponseException

    attempt = 0
    while True:
        attempt += 1
        try:
            async for chunk in agent.run_stream(query):
                if chunk.text:
                    print(chunk.text, end="", flush=True)
            break  # Success, exit retry loop
        except ServiceResponseException as e:
            error_msg = str(e).lower()
            if "too many requests" in error_msg or "429" in error_msg:
                if attempt > max_retries:
                    print(f"\n[Rate limit exceeded after {max_retries} retries]")
                    raise
                # Calculate wait time with exponential backoff + jitter
                import random

                wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
                wait_time += random.uniform(0, wait_time * 0.1)  # Add 10% jitter
                print(
                    f"\n[Rate limited, retrying in {wait_time:.1f}s (attempt {attempt}/{max_retries})...]"
                )
                await asyncio.sleep(wait_time)
            else:
                raise


async def run_example_queries(
    environment: str = "python",
    hyperlight_language: HyperlightLanguage = "javascript",
) -> None:
    """Run some example queries to demonstrate the agent's capabilities."""
    backend = "Azure OpenAI" if _is_azure_configured() else "OpenAI"
    if environment == "hyperlight":
        lang = "Python" if hyperlight_language == "python" else "JavaScript"
        env_info = f"hyperlight/{lang}"
    else:
        env_info = environment
    print("=" * 60)
    print(f"Local Code Interpreter Agent ({backend}, {env_info} environment)")
    print("=" * 60)
    print()

    agent = create_interpreter_agent(
        environment=environment,
        hyperlight_language=hyperlight_language,
    )

    example_queries = [
        "Calculate the sum of the first 100 prime numbers",
        "Write a function to check if a string is a palindrome, then test it",
        "What is 2^100?",
    ]

    for i, query in enumerate(example_queries):
        # Ask agent to show the code it runs
        verbose_query = f"{query}. Please show me the code you execute."
        print(f"User: {query}")
        print("Agent: ", end="", flush=True)
        await run_streaming_with_retry(agent, verbose_query)
        print("\n")


def _configure_logging(verbose: bool = False) -> None:
    """Configure logging and observability for the application."""
    from agent_framework.observability import enable_instrumentation

    # Enable Agent Framework's OpenTelemetry instrumentation
    if verbose:
        # Enable sensitive data logging for development
        enable_instrumentation(enable_sensitive_data=True)

    # Configure Python logging - only show warnings and errors by default
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s - %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)


def run_devui(
    environment: str = "python",
    hyperlight_language: HyperlightLanguage = "javascript",
    port: int = 8090,
    host: str = "127.0.0.1",
    auto_open: bool = True,
) -> None:
    """Launch the DevUI web interface for testing the agent.

    Args:
        environment: Execution environment - 'python' or 'hyperlight'.
        hyperlight_language: Language for hyperlight - 'javascript' or 'python'.
        port: Port to run the DevUI server on.
        host: Host to bind the server to (use 0.0.0.0 for Docker).
        auto_open: Whether to automatically open the browser.
    """
    from agent_framework.devui import serve

    agent = create_interpreter_agent(
        environment=environment,
        hyperlight_language=hyperlight_language,
    )

    backend = "Azure OpenAI" if _is_azure_configured() else "OpenAI"
    if environment == "hyperlight":
        lang = "Python" if hyperlight_language == "python" else "JavaScript"
        env_info = f"hyperlight/{lang}"
    else:
        env_info = environment
    logger.info("=" * 60)
    logger.info("Local Code Interpreter - DevUI")
    logger.info("=" * 60)
    logger.info(f"Backend: {backend}")
    logger.info(f"Environment: {env_info}")
    logger.info(f"Server: http://{host}:{port}")
    logger.info("=" * 60)

    serve(entities=[agent], port=port, host=host, auto_open=auto_open)


def cli() -> None:
    """Command-line interface entry point.
    
    Handles all argument parsing in one place and dispatches to the appropriate mode.
    This is a sync function because run_devui() runs its own event loop.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Local Code Interpreter Agent")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive chat mode")
    parser.add_argument("--devui", action="store_true", help="Launch DevUI web interface")
    parser.add_argument(
        "--port", type=int, default=8090, help="Port for DevUI server (default: 8090)"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host for DevUI server (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't auto-open browser for DevUI",
    )
    parser.add_argument(
        "--hyperlight",
        nargs="?",
        const="javascript",
        choices=["python", "js", "javascript"],
        metavar="LANG",
        help="Use hyperlight VM sandbox. Optional: python, js, javascript (default: javascript)",
    )

    args = parser.parse_args()

    # Determine environment and language
    if args.hyperlight:
        environment = "hyperlight"
        hyperlight_language: HyperlightLanguage = (
            "python" if args.hyperlight == "python" else "javascript"
        )
    else:
        environment = "python"
        hyperlight_language = "javascript"  # Not used, but needed for type

    # Configure logging and observability
    _configure_logging(verbose=args.verbose)

    # Dispatch to the appropriate mode
    if args.devui:
        # run_devui runs its own event loop (uvicorn)
        run_devui(
            environment=environment,
            hyperlight_language=hyperlight_language,
            port=args.port,
            host=args.host,
            auto_open=not args.no_browser,
        )
    elif args.interactive:
        asyncio.run(
            run_interactive_session(
                environment=environment,
                hyperlight_language=hyperlight_language,
            )
        )
    else:
        asyncio.run(
            run_example_queries(
                environment=environment,
                hyperlight_language=hyperlight_language,
            )
        )
