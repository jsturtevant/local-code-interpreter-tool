# Local Code Interpreter Tool

A local code interpreter tool built with the [Microsoft Agent Framework](https://github.com/microsoft/agent-framework).

## Quick Start

This project uses [just](https://github.com/casey/just) as a task runner.

### 1. Setup (creates venv and installs dependencies):
```bash
just setup
```

### 2. Configure your environment:
```bash
cp .env.example .env
# Edit .env with your OpenAI API key or Azure OpenAI configuration
```

### 3. Run the agent:
```bash
just run              # Run the agent in demo mode
just interactive      # Interactive chat mode
```

### Available Commands

Run `just` to see all available commands

## Configuration

### Option 1: OpenAI (api.openai.com)
Set in your `.env` file:
```
OPENAI_API_KEY="your-api-key"
OPENAI_RESPONSES_MODEL_ID="gpt-4o-mini"
```

### Option 2: Azure OpenAI
Set in your `.env` file:
```
AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME="your-deployment"
```
Then authenticate with `az login` before running.

## Learn More

- [Microsoft Agent Framework Documentation](https://learn.microsoft.com/en-us/agent-framework/)
- [Agent Framework GitHub Repository](https://github.com/microsoft/agent-framework)
- [Python Samples](https://github.com/microsoft/agent-framework/tree/main/python/samples/getting_started)

## Azure OpenAI Infrastructure

For provisioning Azure OpenAI via Bicep and deployment instructions, see infra/README.md.
