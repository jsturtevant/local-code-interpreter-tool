# this file is outside src since azure functions expects the entrypoint at the root of the project

"""
Azure Functions Durable Agent Entrypoint

This module provides the Azure Functions entrypoint for the Local Code Interpreter
as a durable agent using the Microsoft Agent Framework.

Configuration (via local.settings.json or environment variables):
- AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint URL
- AZURE_OPENAI_DEPLOYMENT_NAME: Model deployment name (e.g., gpt-4o-mini, gpt-5.1-codex-mini)
- CODE_ENVIRONMENT: Execution environment - 'python' or 'hyperlight' (default: python)
- HYPERLIGHT_LANGUAGE: Language for hyperlight - 'javascript' or 'python' (default: javascript)
"""

import logging
import os

from azure.identity import DefaultAzureCredential
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIResponsesClient, AgentFunctionApp
from agent_framework.observability import enable_instrumentation

from local_code_interpreter.shared import get_instructions, RetryOnRateLimitMiddleware
from local_code_interpreter.tools import CodeExecutionTool, HYPERLIGHT_AVAILABLE

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable Agent Framework instrumentation (logs tool calls, LLM requests, etc.)
enable_instrumentation(enable_sensitive_data=True)

# Get configuration from environment
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
if not endpoint:
    raise ValueError("AZURE_OPENAI_ENDPOINT is not set.")

deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")

# Get execution environment configuration
environment = os.getenv("CODE_ENVIRONMENT", "python")
hyperlight_language = os.getenv("HYPERLIGHT_LANGUAGE", "javascript")

# Validate hyperlight availability
if environment == "hyperlight" and not HYPERLIGHT_AVAILABLE:
    logger.warning("hyperlight-nanvix not installed, falling back to python environment")
    environment = "python"

logger.info(f"Using Azure OpenAI endpoint: {endpoint}, deployment: {deployment_name}")
logger.info(f"Code execution environment: {environment}" + 
            (f" ({hyperlight_language})" if environment == "hyperlight" else ""))

# Create the agent using Azure OpenAI Responses client (supports more models)
client = AzureOpenAIResponsesClient(
    endpoint=endpoint,
    deployment_name=deployment_name,
    credential=DefaultAzureCredential(),
)

# Create code execution tool
code_tool = CodeExecutionTool(
    environment=environment,  # type: ignore[arg-type]
    timeout=30,
    hyperlight_language=hyperlight_language,  # type: ignore[arg-type]
    approval_mode="never_require",
)

# Get appropriate instructions for the environment
instructions = get_instructions(environment, hyperlight_language)  # type: ignore[arg-type]

agent = ChatAgent(
    name="CodeInterpreter",
    description="Local Code Interpreter Agent - Execute code in a sandboxed environment.",
    chat_client=client,
    instructions=instructions,
    tools=[code_tool],  # Known issue: this configuration can fail on the second agent call.
                         # See https://github.com/microsoft/agent-framework/issues/3187 for details.
    middleware=[
        RetryOnRateLimitMiddleware(
            max_retries=5,
            min_wait=1.0,
            max_wait=60.0,
        ),
    ],
)

# Register with Azure Functions (increase timeout to 45s for tool execution temporarily)
app = AgentFunctionApp(agents=[agent], max_poll_retries=45, poll_interval_seconds=1.0)
