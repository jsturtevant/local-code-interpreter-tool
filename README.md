# Local Code Interpreter Tool

A local code interpreter tool built with the [Microsoft Agent Framework](https://github.com/microsoft/agent-framework). It supports safe, sandboxed execution of code locally or in Kubernetes (AKS) using Hyperlight VM isolation.

## Quick Start

This project uses [just](https://github.com/casey/just) as a task runner.

### 0.5 (Optional) Deploy Azure OpenAI:
Skip if using OpenAI directly or you already have an Azure OpenAI endpoint. Requires az cli and for you to be logged in.
```bash
just azure-foundry-deploy

## This step may be blocked on the CLI in some enviroments.  
## Use the portal to assign "Azure AI User" to your account on the Foundry resource
## ex. code-interp-<username>-foundry
just azure-foundry-grant-access
## make sure to re-login with azure cli to get new permissions
```

### 1. Setup (creates venv and installs dependencies):
```bash
just setup
```

### 2. Configure your environment:
```bash
cp .env.example .env
# Edit .env with your OpenAI API key or Azure AI Foundry (Azure OpenAI) configuration
```

### 3. Run the agent:
```bash
just run              # Run the agent in demo mode
just interactive      # Interactive chat mode
just devui            # Launch DevUI web interface
```

### Available Commands

Run `just` to see all available commands.

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
just run hyperlight         # Demo mode with hyperlight
just interactive hyperlight # Interactive mode with hyperlight
```

**Note:** Hyperlight requires:
- Linux with KVM support (`/dev/kvm` access)
- hyperlight-nanvix Python bindings installed (see [Building Hyperlight](#building-hyperlight))

#### Building Hyperlight

Hyperlight Python bindings are automatically built and installed during `just setup`. Ensure Rust toolchain and `maturin` are available on your system.

## Configuration

### Option 1: OpenAI (api.openai.com)
Set in your `.env` file:
```
OPENAI_API_KEY="your-api-key"
OPENAI_RESPONSES_MODEL_ID="gpt-4o-mini"
```

### Option 2: Azure AI Foundry (OpenAI or Claude models)
Set in your `.env` file:
```
AZURE_FOUNDRY_RESOURCE="your-resource-name"
AZURE_FOUNDRY_MODEL_NAME="gpt-5.1-codex-mini"
# Optional: AZURE_FOUNDRY_API_KEY for local dev, otherwise use `az login`
```
Claude models are auto-detected when the model name contains "claude".

## DevUI Web Interface

The project includes a web-based interface for testing and debugging using [Agent Framework DevUI](https://github.com/microsoft/agent-framework/tree/main/python/packages/devui):

```bash
just devui                       # Launch DevUI on http://localhost:8090
just devui hyperlight            # Use hyperlight environment
just devui hyperlight javascript # Use hyperlight with JavaScript code execution
```

DevUI provides:
- A web interface for testing the code interpreter agent
- OpenAI-compatible API endpoints
- Real-time conversation debugging

## Docker & Kubernetes Deployment

### Docker

Use Docker for local testing when you prefer a containerized runtime. Provide credentials via `.env`:
- OpenAI: set `OPENAI_API_KEY`
- Azure AI Foundry: set `AZURE_FOUNDRY_API_KEY`

```bash
just docker-build              # Build the container image
just docker-run                # Run with .env for OpenAI/Azure credentials
just docker-up                 # Build and run in one command
```

### Kubernetes (AKS with Workload Identity)

Deploy to Azure Kubernetes Service with Azure OpenAI authentication via Workload Identity and Hyperlight for secure VM-isolated code execution.

The deployment uses Hyperlight for secure VM-isolated code execution:
- Hyperlight device plugin exposes `/dev/kvm` to pods
- Pods run on KVM-enabled nodes (`kvmpool`)
- Resource limit `hyperlight.dev/hypervisor: "1"` grants hypervisor access

#### Prerequisites
- Azure CLI installed and logged in (`az login`)
- `kubectl` installed
- `envsubst` installed

#### Deploy to AKS

```bash
# 1. Create AKS cluster with workload identity
just azure-aks-create
just azure-aks-get-credentials

# 2. Create Azure Container Registry and attach to AKS
just azure-create-acr
just azure-aks-attach-acr

# 3. Add KVM-enabled node pool and deploy Hyperlight device plugin
just azure-aks-deploy-kvm-pool
just azure-aks-deploy-device-plugin
just azure-aks-plugin-status  # Verify device plugin is running

# 4. Create managed identity and federated credential
just azure-identity-create
export MANAGED_IDENTITY_CLIENT_ID=$(just azure-identity-show)
just azure-identity-federate

# 5. Assign Azure AI Foundry access to managed identity
## Note: This step may be blocked by conditional access policies.
## If it fails, manually assign "Cognitive Services OpenAI User" role to 
## the "local-code-interpreter" managed identity on your Azure AI Foundry resource.
export AZURE_FOUNDRY_RESOURCE=$(just azure-foundry-show)
just azure-role-assign

# 6. Set environment variables for deployment
export IMAGE_REGISTRY_NAME="your-acr"  # e.g., hyperlightacr
export IMAGE_REGISTRY_DOMAIN="azurecr.io"
export AZURE_FOUNDRY_MODEL_NAME="gpt-5.1-codex-mini"
# MANAGED_IDENTITY_CLIENT_ID already set from step 4

# 7. Build and push container image with Hyperlight support
just acr-login
just docker-build-hyperlight
just docker-push

# 8. Deploy to Kubernetes with Hyperlight
just k8s-deploy-hyperlight

# 9. Port forward to access locally
just k8s-port-forward
# Access DevUI at http://localhost:8090
```

#### Hyperlight Language Options

Hyperlight supports both JavaScript (default) and Python:

```bash
# Deploy with JavaScript (default)
just k8s-deploy-hyperlight

# Deploy with Python
just k8s-deploy-hyperlight python
```

#### Useful Commands

```bash
# Kubernetes
just k8s-status            # View deployment status
just k8s-logs              # Tail pod logs
just k8s-port-forward      # Port forward to localhost:8090
just k8s-delete            # Remove all resources

# Azure/AKS
just acr-login                      # Log in to Azure Container Registry
just azure-aks-plugin-status        # Check device plugin status
just azure-aks-get-credentials      # Get kubectl credentials
```

## Troubleshooting
- Azure permissions: If CLI deployment fails, assign the “Azure AI User” role to your account on the Foundry resource in the portal, then run `az login` again.
- AKS device plugin: Use `just azure-aks-plugin-status` to confirm Hyperlight device plugin is ready and nodes in `kvmpool` advertise KVM.
- Claude/Anthropic models: Deploying Claude models (claude-opus-4-5, claude-sonnet-4-5, etc.) via `just azure-foundry-deploy` requires Azure quota for Anthropic models, which may not be available in all subscriptions. Claude support has not been fully tested due to quota limitations.

## Learn More

- [Microsoft Agent Framework Documentation](https://learn.microsoft.com/en-us/agent-framework/)
- [Agent Framework GitHub Repository](https://github.com/microsoft/agent-framework)
- [Python Samples](https://github.com/microsoft/agent-framework/tree/main/python/samples/getting_started)

## Azure OpenAI Infrastructure

For provisioning Azure AI Foundry (Azure OpenAI) via Bicep and deployment instructions, see infra/README.md.
