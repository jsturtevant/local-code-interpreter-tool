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
just devui            # Launch DevUI web interface
```

### Available Commands

Run `just` to see all available commands

## Execution Environments

The code execution tool supports two environments:

### Python (default)
Fast subprocess execution for Python code with timeout and sandboxing.

```bash
just run              # Uses python environment
just interactive      # Interactive mode with python
```

### Hyperlight
VM-isolated sandbox using [hyperlight-nanvix](https://github.com/hyperlight-dev/hyperlight-nanvix) for untrusted code execution. Supports JavaScript, Python, C, and C++.

```bash
just run --hyperlight         # Demo mode with hyperlight
just interactive --hyperlight # Interactive mode with hyperlight
```

**Note:** Hyperlight requires:
- Linux with KVM support (`/dev/kvm` access)
- hyperlight-nanvix Python bindings installed (see [Building Hyperlight](#building-hyperlight))

#### Building Hyperlight

```bash
# Clone the hyperlight-nanvix repository
git clone https://github.com/hyperlight-dev/hyperlight-nanvix.git
cd hyperlight-nanvix
git checkout danbugs/python-host-sdk

# Build and install into your venv (requires Rust and maturin)
pip install maturin
maturin develop --features python
```

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

## DevUI Web Interface

The project includes a web-based interface for testing and debugging using [Agent Framework DevUI](https://github.com/microsoft/agent-framework/tree/main/python/packages/devui):

```bash
just devui                     # Launch DevUI on http://localhost:8090
just devui --port=8080         # Custom port
just devui --hyperlight        # Use hyperlight environment
just devui --no-browser        # Don't auto-open browser
```

DevUI provides:
- A web interface for testing the code interpreter agent
- OpenAI-compatible API endpoints
- Real-time conversation debugging

## Learn More

- [Microsoft Agent Framework Documentation](https://learn.microsoft.com/en-us/agent-framework/)
- [Agent Framework GitHub Repository](https://github.com/microsoft/agent-framework)
- [Python Samples](https://github.com/microsoft/agent-framework/tree/main/python/samples/getting_started)

## Azure OpenAI Infrastructure

For provisioning Azure OpenAI via Bicep and deployment instructions, see infra/README.md.
