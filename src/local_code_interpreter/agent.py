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

from dotenv import load_dotenv
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIResponsesClient

from .tools import (
    get_release_status,
    list_pending_approvals,
    get_deployment_logs,
    trigger_rollback,
    get_current_time,
)

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
# Agent Configuration
# =============================================================================

INTERPRETER_AGENT_INSTRUCTIONS = """You are a Local Code Interpreter Assistant, helping users execute and test code.

Your capabilities include:
- Executing Python code in a sandboxed environment
- Testing code snippets and algorithms
- Running calculations and data processing
- Providing time information for coordination

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
            get_release_status,
            list_pending_approvals,
            get_deployment_logs,
            trigger_rollback,
            get_current_time,
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
            async for chunk in agent.run_stream(user_input):
                if chunk.text:
                    print(chunk.text, end="", flush=True)
            print("\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


async def run_example_queries() -> None:
    """Run some example queries to demonstrate the agent's capabilities."""
    backend = "Azure OpenAI" if _is_azure_configured() else "OpenAI"
    print("=" * 60)
    print(f"Local Code Interpreter Agent ({backend})")
    print("=" * 60)
    print()

    agent = create_interpreter_agent()

    example_queries = [
        "What is the status of release v1.2.3?",
        "Are there any pending approvals I need to handle?",
        "Show me the recent deployment logs for production",
    ]

    for query in example_queries:
        print(f"User: {query}")
        result = await agent.run(query)
        print(f"Agent: {result}\n")


async def main() -> None:
    """Main entry point."""
    import sys
    
    if "--interactive" in sys.argv:
        await run_interactive_session()
    else:
        await run_example_queries()


if __name__ == "__main__":
    asyncio.run(main())
