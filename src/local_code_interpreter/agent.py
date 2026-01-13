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

from dotenv import load_dotenv
from agent_framework import AIFunction, ChatAgent
from agent_framework.openai import OpenAIResponsesClient

from .shared import (
    RetryOnRateLimitMiddleware,
    get_instructions,
)
from .tools import CodeExecutionTool, HyperlightLanguage, HYPERLIGHT_AVAILABLE

# Load environment variables from .env file
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)


def _is_azure_foundry_configured() -> bool:
    """Check if Azure AI Foundry is configured."""
    return bool(os.getenv("AZURE_FOUNDRY_RESOURCE"))


def _is_azure_foundry_claude_configured() -> bool:
    """Check if Azure Foundry Claude is configured.

    Returns True if AZURE_FOUNDRY_RESOURCE is set and model name contains 'claude'.
    """
    resource = os.getenv("AZURE_FOUNDRY_RESOURCE")
    model_name = os.getenv("AZURE_FOUNDRY_MODEL_NAME", "")
    return bool(resource) and "claude" in model_name.lower()


def _get_backend_name() -> str:
    """Get the name of the configured backend."""
    if _is_azure_foundry_claude_configured():
        return "Azure Foundry Claude"
    elif _is_azure_foundry_configured():
        return "Azure Foundry OpenAI"
    else:
        return "OpenAI"


def _create_chat_client():
    """Create the appropriate chat client based on environment configuration."""
    if _is_azure_foundry_configured():
        from agent_framework.azure import AzureOpenAIResponsesClient

        resource = os.getenv("AZURE_FOUNDRY_RESOURCE")
        foundry_endpoint = f"https://{resource}.openai.azure.com"
        model_name = os.getenv("AZURE_FOUNDRY_MODEL_NAME", "gpt-5.1-codex-mini")

        # Check for API key first (local dev), then fall back to DefaultAzureCredential
        api_key = os.getenv("AZURE_FOUNDRY_API_KEY")
        if api_key:
            return AzureOpenAIResponsesClient(
                api_key=api_key,
                endpoint=foundry_endpoint,
                deployment_name=model_name,
            )
        else:
            from azure.identity import DefaultAzureCredential

            return AzureOpenAIResponsesClient(
                credential=DefaultAzureCredential(),
                endpoint=foundry_endpoint,
                deployment_name=model_name,
            )
    else:
        return OpenAIResponsesClient()


def _create_anthropic_client():
    """Create an Anthropic client for Azure Foundry Claude.

    Uses AZURE_FOUNDRY_RESOURCE to construct the base URL.
    Authenticates via API key or Microsoft Entra ID (az login).
    """
    from agent_framework.anthropic import AnthropicClient
    from anthropic import AnthropicFoundry

    resource = os.getenv("AZURE_FOUNDRY_RESOURCE")
    if not resource:
        raise ValueError("AZURE_FOUNDRY_RESOURCE environment variable not set")

    base_url = f"https://{resource}.services.ai.azure.com/anthropic"

    # Check for API key first (local dev), then fall back to Entra ID
    api_key = os.getenv("AZURE_FOUNDRY_API_KEY")
    if api_key:
        return AnthropicClient(
            anthropic_client=AnthropicFoundry(
                api_key=api_key,
                base_url=base_url,
            )
        )
    else:
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider

        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default",
        )

        return AnthropicClient(
            anthropic_client=AnthropicFoundry(
                azure_ad_token_provider=token_provider,
                base_url=base_url,
            )
        )


# =============================================================================
# Agent Configuration
# =============================================================================


def create_interpreter_agent(
    environment: str = "python",
    timeout: int = 30,
    hyperlight_language: HyperlightLanguage = "javascript",
    name: str = "code-interpreter",
    description: str | None = None,
) -> ChatAgent:
    """Create and configure the local code interpreter agent.

    Automatically uses Azure Foundry Claude if AZURE_FOUNDRY_RESOURCE is set,
    else uses Azure OpenAI if AZURE_OPENAI_ENDPOINT is set,
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
    instructions = get_instructions(environment, hyperlight_language)

    backend = _get_backend_name()
    if description is None:
        if environment == "hyperlight":
            lang = "Python" if hyperlight_language == "python" else "JavaScript"
        else:
            lang = "Python"
        description = (
            f"Local Code Interpreter using {backend}. "
            f"Execute {lang} code in a sandboxed {environment} environment."
        )

    if _is_azure_foundry_claude_configured():
        # Use Anthropic client for Claude models
        client = _create_anthropic_client()
        model_name = os.getenv("AZURE_FOUNDRY_MODEL_NAME", "gpt-5.1-codex-mini")
        return client.create_agent(  # type: ignore[no-any-return]
            name=name,
            description=description,
            model=model_name,
            instructions=instructions,
            tools=tools,
        )
    else:
        # Use OpenAI-compatible client
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
    backend = _get_backend_name()
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
    backend = _get_backend_name()
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
    """Configure logging and observability for the application.

    Debug mode can be enabled via environment variable: DEBUG=true
    """
    from agent_framework.observability import enable_instrumentation

    # Check environment variable for debug mode
    debug = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")

    # Enable Agent Framework's OpenTelemetry instrumentation
    if verbose or debug:
        # Enable sensitive data logging for development
        enable_instrumentation(enable_sensitive_data=True)

    # Configure Python logging - only show warnings and errors by default
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(levelname)s - %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # Enable debug for our module when DEBUG env is set
    if debug:
        logging.getLogger("local_code_interpreter").setLevel(logging.DEBUG)

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

    backend = _get_backend_name()
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
