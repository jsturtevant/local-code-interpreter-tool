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
import os
from typing import Awaitable, Callable

from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_message,
    stop_after_attempt,
    wait_exponential_jitter,
)
from agent_framework import ChatAgent, ChatContext, ChatMiddleware
from agent_framework.openai import OpenAIResponsesClient

from .tools import CodeExecutionTool

# Load environment variables from .env file
load_dotenv()


def _is_azure_configured() -> bool:
    """Check if Azure OpenAI is configured."""
    return bool(os.getenv("AZURE_OPENAI_ENDPOINT"))


def _create_chat_client():
    """Create the appropriate chat client based on environment configuration."""
    if _is_azure_configured():
        from agent_framework.azure import AzureOpenAIResponsesClient
        from azure.identity import AzureCliCredential

        return AzureOpenAIResponsesClient(credential=AzureCliCredential())
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

INTERPRETER_AGENT_INSTRUCTIONS = """You are a Local Code Interpreter Assistant, helping users execute and test code.

Your capabilities include:
- Executing Python code in a sandboxed environment using the execute_code tool
- Testing code snippets and algorithms
- Running calculations and data processing
- Providing time information for coordination

When to use the execute_code tool:
- When you need to perform calculations or verify mathematical results
- When you need to test a code snippet or algorithm
- When the user asks you to run or execute code
- When you need to process data or demonstrate Python functionality

Always be clear and concise. When reporting issues, include actionable recommendations.
If you need more information to help, ask clarifying questions.
"""


def create_interpreter_agent() -> ChatAgent:
    """Create and configure the local code interpreter agent.

    Automatically uses Azure OpenAI if AZURE_OPENAI_ENDPOINT is set,
    otherwise uses OpenAI.
    """
    return ChatAgent(
        chat_client=_create_chat_client(),
        instructions=INTERPRETER_AGENT_INSTRUCTIONS,
        tools=[
            CodeExecutionTool(timeout=30, approval_mode="never_require"),
        ],
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


async def run_interactive_session() -> None:
    """Run an interactive chat session with the interpreter agent."""
    backend = "Azure OpenAI" if _is_azure_configured() else "OpenAI"
    print("=" * 60)
    print(f"Local Code Interpreter Agent ({backend})")
    print("Type 'quit' or 'exit' to end the session")
    print("=" * 60)
    print()

    agent = create_interpreter_agent()

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


async def run_example_queries() -> None:
    """Run some example queries to demonstrate the agent's capabilities."""
    backend = "Azure OpenAI" if _is_azure_configured() else "OpenAI"
    print("=" * 60)
    print(f"Local Code Interpreter Agent ({backend})")
    print("=" * 60)
    print()

    agent = create_interpreter_agent()

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


async def main() -> None:
    """Main entry point."""
    import sys

    if "--interactive" in sys.argv:
        await run_interactive_session()
    else:
        await run_example_queries()


if __name__ == "__main__":
    asyncio.run(main())
