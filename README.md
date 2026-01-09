# Local Code Interpreter Tool

A local code interpreter tool built with the [Microsoft Agent Framework](https://github.com/microsoft/agent-framework).

## Quick Start

This project uses [just](https://github.com/casey/just) as a task runner.

### 0.5 (Optional) Deploy Azure OpenAI:
Skip if using OpenAI directly or you already have an Azure OpenAI endpoint. Requires az cli and for you to be logged in.
```bash
just azure-foundry-deploy
just azure-foundry-grant-access
```

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
just run hyperlight         # Demo mode with hyperlight
just interactive hyperlight # Interactive mode with hyperlight
```

**Note:** Hyperlight requires:
- Linux with KVM support (`/dev/kvm` access)
- hyperlight-nanvix Python bindings installed (see [Building Hyperlight](#building-hyperlight))

#### Building Hyperlight

Hyperlight is automatically built and installed when you run `just setup`. This requires Rust and maturin to be installed on your system.

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

Build and run locally with Docker:

```bash
just docker-build              # Build the container image
just docker-run                # Run with .env file for Azure auth
just docker-up                 # Build and run in one command
```

### Kubernetes (AKS with Workload Identity)

Deploy to Azure Kubernetes Service with Azure OpenAI authentication via Workload Identity:

#### Prerequisites
- AKS cluster with OIDC issuer and workload identity enabled
- Azure Container Registry (ACR) attached to the cluster
- Azure OpenAI resource deployed
- `envsubst` installed

#### Quick Deploy (existing cluster)

```bash
# 0. (If needed) Enable workload identity on existing cluster
just azure-aks-enable-workload-identity

# 1. Get cluster credentials
just azure-aks-get-credentials

# 2. Create managed identity and federated credential
just azure-identity-create
export MANAGED_IDENTITY_CLIENT_ID=$(just azure-identity-show)
just azure-identity-federate

# 3. Assign Azure OpenAI access (requires specific access, might need to do manually in Portal)
export AZURE_OPENAI_RESOURCE=$(just azure-foundry-show)  # or specify your resource name
just azure-role-assign

# 4. Set environment variables for deployment
export IMAGE_REGISTRY_NAME="your-acr"
export IMAGE_REGISTRY_DOMAIN="azurecr.io"
export AZURE_OPENAI_ENDPOINT="https://${AZURE_OPENAI_RESOURCE}.openai.azure.com/"
export AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME="gpt-4o"
# MANAGED_IDENTITY_CLIENT_ID already set from step 2

# 5. Build and push container image
just docker-build
just docker-push

# 6. Preview the deployment (optional)
just k8s-dry-run

# 7. Deploy to Kubernetes
just k8s-deploy

# 8. Port forward to access locally
just k8s-port-forward
```

#### Deploying with Hyperlight

To enable Hyperlight VM-isolated code execution instead of Python subprocess:

**Step 1: Build the image with Hyperlight support**

The Docker image must be built with the `WITH_HYPERLIGHT=true` build arg to include the hyperlight-nanvix library:

```bash
# Build with Hyperlight support (takes longer, includes Rust build)
just docker-build-hyperlight

# Push to registry
just docker-push
```

**Step 2: Deploy with Hyperlight enabled**

```bash
# Option 1: Use the convenience command
just k8s-deploy-hyperlight

# Option 2: Set the environment variable explicitly
export ENABLE_HYPERLIGHT=true
just k8s-deploy
```

**Note:** Hyperlight requires:
- Docker image built with `WITH_HYPERLIGHT=true` (step 1 above)
- Hyperlight device plugin installed on the cluster (see Full Setup below)
- Nodes with KVM support (the `kvmpool` node pool)
- The deployment uses `hyperlight.dev/hypervisor: "1"` resource limit via the device plugin

#### Full Setup (new cluster)

```bash
# Create AKS cluster with workload identity
just azure-aks-create

# Create Azure Container Registry
just azure-create-acr

# Attach ACR to AKS (allows pulling images without imagePullSecrets)
just azure-aks-attach-acr

# Add KVM-enabled node pool for Hyperlight
just azure-aks-deploy-kvm-pool

# Deploy Hyperlight device plugin
just azure-aks-deploy-device-plugin

# Verify device plugin is running
just azure-aks-plugin-status

# Then follow the Quick Deploy steps above
```

#### Useful Commands

```bash
# Kubernetes
just k8s-status            # View deployment status
just k8s-logs              # Tail pod logs
just k8s-port-forward      # Port forward to localhost:8090
just k8s-delete            # Remove all resources
just k8s-deploy-hyperlight # Deploy with Hyperlight enabled

# Azure/AKS
just acr-login                     # Log in to Azure Container Registry
just azure-aks-deploy-kvm-pool     # Add KVM-enabled node pool
just azure-aks-deploy-device-plugin # Deploy Hyperlight device plugin
just azure-aks-plugin-status       # Check device plugin status
```

### Hyperlight on Kubernetes

The deployment uses Hyperlight for secure code execution. Requirements:
- Hyperlight device plugin installed on the cluster
- Nodes with KVM support (`/dev/kvm`)

The pod spec includes:
- `hyperlight.dev/hypervisor: "1"` - Requests hypervisor access via device plugin

## Learn More

- [Microsoft Agent Framework Documentation](https://learn.microsoft.com/en-us/agent-framework/)
- [Agent Framework GitHub Repository](https://github.com/microsoft/agent-framework)
- [Python Samples](https://github.com/microsoft/agent-framework/tree/main/python/samples/getting_started)

## Azure OpenAI Infrastructure

For provisioning Azure OpenAI via Bicep and deployment instructions, see infra/README.md.
