# Local Code Interpreter Tool - Task Runner
# Run `just` to see available commands

# Virtual environment activation prefix
venv := ". .venv/bin/activate &&"

# Check that venv exists
check-venv := "test -d .venv || (echo '❌ Virtual environment not found. Run: just setup' && exit 1)"

# Default recipe - show available commands
default:
    @just --list

# =============================================================================
# Development Environment
# =============================================================================

# Create and set up virtual environment
setup:
    python3 -m venv .venv
    {{venv}} pip install --upgrade pip
    {{venv}} pip install -r requirements.txt
    {{venv}} pip install -r requirements-dev.txt
    {{venv}} pip install -e .
    just install-nanvix
    @echo "✅ Virtual environment ready. Run: source .venv/bin/activate"

# Install dependencies only (requires venv to exist)
install:
    @{{check-venv}}
    {{venv}} pip install -r requirements.txt

# Install in development mode with editable install
install-dev:
    @{{check-venv}}
    {{venv}} pip install -e .
    {{venv}} pip install -r requirements-dev.txt

# Install hyperlight-nanvix Python bindings (requires Rust nightly toolchain)
install-nanvix:
    @{{check-venv}}
    @echo "📦 Installing hyperlight-nanvix Python bindings..."
    @if ! command -v rustup &> /dev/null && [ ! -x "${CARGO_HOME:-$HOME/.cargo}/bin/rustup" ]; then \
        echo "❌ rustup not found. Please install Rust: https://rustup.rs"; \
        exit 1; \
    fi
    @echo "🔧 Installing Rust nightly toolchain..."
    "${CARGO_HOME:-$HOME/.cargo}/bin/rustup" install nightly
    @if [ ! -d "vendor/hyperlight-nanvix" ]; then \
        echo "📥 Cloning hyperlight-nanvix..."; \
        mkdir -p vendor; \
        git clone https://github.com/hyperlight-dev/hyperlight-nanvix.git vendor/hyperlight-nanvix; \
    else \
        echo "📥 Updating hyperlight-nanvix..."; \
        cd vendor/hyperlight-nanvix && git pull; \
    fi
    {{venv}} pip install maturin
    {{venv}} cd vendor/hyperlight-nanvix && VIRTUAL_ENV="$(cd ../.. && pwd)/.venv" maturin develop --features python
    @echo "✅ hyperlight-nanvix installed successfully"

# Update dependencies
update:
    @{{check-venv}}
    {{venv}} pip install --upgrade -r requirements.txt

# =============================================================================
# Running the Agent
# =============================================================================

# Run the agent with example queries
# Usage: just run [environment] [language]
#   just run                    - Python subprocess (default)
#   just run python             - Python subprocess
#   just run hyperlight         - Hyperlight with JavaScript (default)
#   just run hyperlight js      - Hyperlight with JavaScript
#   just run hyperlight python  - Hyperlight with Python
run env="python" lang="":
    @{{check-venv}}
    @if [ "{{env}}" = "hyperlight" ]; then \
        {{venv}} python -m local_code_interpreter --hyperlight {{lang}}; \
    else \
        {{venv}} python -m local_code_interpreter; \
    fi

# Run in interactive chat mode
# Usage: just interactive [environment] [language]
#   just interactive                    - Python subprocess (default)
#   just interactive python             - Python subprocess
#   just interactive hyperlight         - Hyperlight with JavaScript (default)
#   just interactive hyperlight js      - Hyperlight with JavaScript
#   just interactive hyperlight python  - Hyperlight with Python
interactive env="python" lang="":
    @{{check-venv}}
    @if [ "{{env}}" = "hyperlight" ]; then \
        {{venv}} python -m local_code_interpreter --interactive --hyperlight {{lang}}; \
    else \
        {{venv}} python -m local_code_interpreter --interactive; \
    fi

# Launch the DevUI web interface for testing
# Usage: just devui [environment] [language]
#   just devui                    - Python subprocess (default)
#   just devui python             - Python subprocess
#   just devui hyperlight         - Hyperlight with JavaScript (default)
#   just devui hyperlight js      - Hyperlight with JavaScript
#   just devui hyperlight python  - Hyperlight with Python
devui env="python" lang="":
    @{{check-venv}}
    @if [ "{{env}}" = "hyperlight" ]; then \
        {{venv}} python -m local_code_interpreter --devui --hyperlight {{lang}}; \
    else \
        {{venv}} python -m local_code_interpreter --devui; \
    fi

# =============================================================================
# Code Quality
# =============================================================================

# Format code with black
format:
    @{{check-venv}}
    {{venv}} black src/ tests/

# Check formatting without modifying files
format-check:
    @{{check-venv}}
    {{venv}} black --check src/ tests/

# Lint code with ruff
lint:
    @{{check-venv}}
    {{venv}} ruff check src/ tests/

# Fix linting issues automatically
lint-fix:
    @{{check-venv}}
    {{venv}} ruff check --fix src/ tests/

# Type check with mypy
typecheck:
    @{{check-venv}}
    {{venv}} mypy src/

# Run all code quality checks
check: format lint typecheck
    @echo "✅ All code quality checks passed"

# =============================================================================
# Testing
# =============================================================================

# Run all tests
test:
    @{{check-venv}}
    {{venv}} pytest tests/ -v

# Run tests and generate reports (for CI)
test-ci:
    @{{check-venv}}
    {{venv}} pytest tests/ -v --cov=src/local_code_interpreter --cov-report=xml --cov-report=html --junitxml=test-results.xml

# =============================================================================
# Docker
# =============================================================================

# Docker image configuration
IMAGE_REGISTRY := env_var_or_default("IMAGE_REGISTRY", "hyperlightacrjs")
IMAGE_NAME := "local-code-interpreter"
IMAGE_TAG := env_var_or_default("IMAGE_TAG", "latest")
IMAGE := IMAGE_REGISTRY + "/" + IMAGE_NAME + ":" + IMAGE_TAG

# Build Docker image
docker-build:
    docker build -t {{IMAGE}} .

# Build Docker image with Hyperlight support (includes hyperlight-nanvix)
docker-build-hyperlight:
    docker build --build-arg WITH_HYPERLIGHT=true -t {{IMAGE}} .

# Run Docker container locally (uses env vars from .env for Azure auth)
# Usage: just docker-run [env] [lang]
#   just docker-run                    - Python subprocess (default)
#   just docker-run hyperlight         - Hyperlight with JavaScript
#   just docker-run hyperlight python  - Hyperlight with Python
docker-run env="python" lang="javascript":
    @if [ "{{env}}" = "hyperlight" ]; then \
        docker run --rm -p 8090:8090 --env-file .env {{IMAGE}} --hyperlight {{lang}}; \
    else \
        docker run --rm -p 8090:8090 --env-file .env {{IMAGE}}; \
    fi

# Build and run Docker container
docker-up: docker-build docker-run

# Build and run Docker container with Hyperlight JavaScript
docker-up-hyperlight: docker-build-hyperlight
    just docker-run hyperlight javascript

# Build and run Docker container with Hyperlight Python
docker-up-hyperlight-python: docker-build-hyperlight
    just docker-run hyperlight python

# Push Docker image to registry
docker-push:
    docker push {{IMAGE}}

# =============================================================================
# Kubernetes
# =============================================================================

# Kubernetes configuration
K8S_NAMESPACE := "local-code-interpreter"
K8S_SERVICE_ACCOUNT := "local-code-interpreter"

# Required env vars for k8s-deploy (set these or export before running):
# - IMAGE_REGISTRY: Container registry (e.g., myacr.azurecr.io)
# - IMAGE_TAG: Image tag (default: latest)
# - MANAGED_IDENTITY_CLIENT_ID: Azure managed identity client ID
# - AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint URL
# - AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME: Model deployment name

# Deploy to Kubernetes using kustomize + envsubst for variable substitution
# Usage: just k8s-deploy [env] [lang]
#   just k8s-deploy                    - No hyperlight (subprocess execution)
#   just k8s-deploy hyperlight         - Hyperlight with JavaScript
#   just k8s-deploy hyperlight python  - Hyperlight with Python
k8s-deploy env="" lang="javascript":
    #!/usr/bin/env bash
    set -euo pipefail
    
    # Set defaults for optional vars
    export IMAGE_TAG="${IMAGE_TAG:-latest}"
    export AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME="${AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME:-gpt-4o}"
    
    # Set mode description
    if [ "{{env}}" = "hyperlight" ]; then
        MODE_DESC="Hyperlight {{lang}}"
    else
        MODE_DESC="Python subprocess"
    fi
    
    # Validate required env vars
    required_vars=("IMAGE_REGISTRY" "MANAGED_IDENTITY_CLIENT_ID" "AZURE_OPENAI_ENDPOINT")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            echo "❌ Required environment variable $var is not set"
            echo "   Set it with: export $var=<value>"
            exit 1
        fi
    done
    
    echo "🚀 Deploying with:"
    echo "   IMAGE: ${IMAGE_REGISTRY}/local-code-interpreter:${IMAGE_TAG}"
    echo "   AZURE_OPENAI_ENDPOINT: ${AZURE_OPENAI_ENDPOINT}"
    echo "   MANAGED_IDENTITY_CLIENT_ID: ${MANAGED_IDENTITY_CLIENT_ID}"
    echo "   MODE: ${MODE_DESC}"
    echo ""
    
    # Build with kustomize, substitute env vars, optionally add hyperlight args, apply
    if [ "{{env}}" = "hyperlight" ]; then
        kubectl kustomize k8s/ | envsubst | \
            sed 's/imagePullPolicy: Always/imagePullPolicy: Always\n        args:\n        - "--hyperlight"\n        - "{{lang}}"/' | \
            kubectl apply -f -
    else
        kubectl kustomize k8s/ | envsubst | kubectl apply -f -
    fi
    
    echo ""
    echo "✅ Deployment complete! Run 'just k8s-status' to check status."

# Delete Kubernetes resources
k8s-delete:
    kubectl kustomize k8s/ | envsubst | kubectl delete -f - --ignore-not-found

# Preview what will be deployed (dry-run with variable substitution)
# Usage: just k8s-dry-run [env] [lang]
k8s-dry-run env="" lang="javascript":
    #!/usr/bin/env bash
    export IMAGE_TAG="${IMAGE_TAG:-latest}"
    export AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME="${AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME:-gpt-4o}"
    if [ "{{env}}" = "hyperlight" ]; then
        kubectl kustomize k8s/ | envsubst | \
            sed 's/imagePullPolicy: Always/imagePullPolicy: Always\n        args:\n        - "--hyperlight"\n        - "{{lang}}"/'
    else
        kubectl kustomize k8s/ | envsubst
    fi

# Get deployment status
k8s-status:
    @echo "📊 Deployment Status:"
    kubectl get all -n {{K8S_NAMESPACE}}

# Port forward service to localhost for local testing
k8s-port-forward:
    kubectl port-forward -n {{K8S_NAMESPACE}} svc/local-code-interpreter 8090:8090

# View pod logs
k8s-logs:
    kubectl logs -n {{K8S_NAMESPACE}} -l app.kubernetes.io/name=local-code-interpreter -f

# View pod logs (tail last N lines)
k8s-logs-tail lines="100":
    kubectl logs -n {{K8S_NAMESPACE}} -l app.kubernetes.io/name=local-code-interpreter --tail={{lines}}

# View debug logs (script input/output only)
k8s-logs-debug lines="200":
    kubectl logs -n {{K8S_NAMESPACE}} -l app.kubernetes.io/name=local-code-interpreter --tail={{lines}} | grep -E "INPUT SCRIPT|EXECUTION RESULT|====|    "

# =============================================================================
# AKS Cluster Setup
# =============================================================================

# Azure configuration for AKS
AZURE_SUBSCRIPTION := env_var_or_default("AZURE_SUBSCRIPTION", "")
AZURE_RESOURCE_GROUP := env_var_or_default("AZURE_RESOURCE_GROUP", "local-code-interpreter-rg")
AZURE_LOCATION := env_var_or_default("AZURE_LOCATION", "eastus")
AKS_CLUSTER := env_var_or_default("AKS_CLUSTER", "local-code-interpreter-aks")
AZURE_OPENAI_RESOURCE := env_var_or_default("AZURE_OPENAI_RESOURCE", "")
MANAGED_IDENTITY_CLIENT_ID := env_var_or_default("MANAGED_IDENTITY_CLIENT_ID", "")

# Create AKS cluster with workload identity enabled
azure-aks-create:
    az aks create \
        --name {{AKS_CLUSTER}} \
        --resource-group {{AZURE_RESOURCE_GROUP}} \
        --location {{AZURE_LOCATION}} \
        --enable-oidc-issuer \
        --enable-workload-identity \
        --generate-ssh-keys

# Enable workload identity on existing AKS cluster
azure-aks-enable-workload-identity:
    az aks update \
        --name {{AKS_CLUSTER}} \
        --resource-group {{AZURE_RESOURCE_GROUP}} \
        --enable-oidc-issuer \
        --enable-workload-identity

# Get AKS cluster credentials
azure-aks-get-credentials:
    az aks get-credentials \
        --name {{AKS_CLUSTER}} \
        --resource-group {{AZURE_RESOURCE_GROUP}}

# Attach ACR to AKS cluster (allows pulling images without imagePullSecrets)
azure-aks-attach-acr acr:
    az aks update \
        --name {{AKS_CLUSTER}} \
        --resource-group {{AZURE_RESOURCE_GROUP}} \
        --attach-acr {{acr}}

# =============================================================================
# Azure Workload Identity Setup
# =============================================================================

# Create user-assigned managed identity
azure-identity-create:
    az identity create \
        --name local-code-interpreter \
        --resource-group {{AZURE_RESOURCE_GROUP}} \
        --location {{AZURE_LOCATION}}

# Create federated credential linking managed identity to Kubernetes ServiceAccount
azure-identity-federate:
    #!/usr/bin/env bash
    set -euo pipefail
    AKS_OIDC_ISSUER=$(az aks show \
        --name {{AKS_CLUSTER}} \
        --resource-group {{AZURE_RESOURCE_GROUP}} \
        --query "oidcIssuerProfile.issuerUrl" -o tsv)
    echo "🔗 Creating federated credential with issuer: $AKS_OIDC_ISSUER"
    az identity federated-credential create \
        --name kubernetes-federated \
        --identity-name local-code-interpreter \
        --resource-group {{AZURE_RESOURCE_GROUP}} \
        --issuer "$AKS_OIDC_ISSUER" \
        --subject "system:serviceaccount:{{K8S_NAMESPACE}}:{{K8S_SERVICE_ACCOUNT}}" \
        --audiences "api://AzureADTokenExchange"
    echo "✅ Federated credential created!"

# Show managed identity client ID
azure-identity-show:
    @az identity show \
        --name local-code-interpreter \
        --resource-group {{AZURE_RESOURCE_GROUP}} \
        --query clientId -o tsv

# Assign Azure OpenAI User role to managed identity
azure-role-assign:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "{{MANAGED_IDENTITY_CLIENT_ID}}" ]; then \
        echo "❌ MANAGED_IDENTITY_CLIENT_ID not set. Run: just azure-identity-show"; \
        exit 1; \
    fi
    if [ -z "{{AZURE_OPENAI_RESOURCE}}" ]; then \
        echo "❌ AZURE_OPENAI_RESOURCE not set"; \
        exit 1; \
    fi
    subscriptionId=$(az account show --query id -o tsv)
    echo "🔐 Assigning Cognitive Services OpenAI User role..."
    az role assignment create \
        --assignee {{MANAGED_IDENTITY_CLIENT_ID}} \
        --role "Cognitive Services OpenAI User" \
        --scope "/subscriptions/$subscriptionId/resourceGroups/{{AZURE_RESOURCE_GROUP}}/providers/Microsoft.CognitiveServices/accounts/{{AZURE_OPENAI_RESOURCE}}"
    echo "✅ Role assigned!"

# =============================================================================
# Build & Package
# =============================================================================

# Build the package
build: setup
    {{venv}} python -m pip install build
    {{venv}} python -m build

# Clean build artifacts
clean:
    rm -rf build/ dist/ *.egg-info src/*.egg-info
    rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
    rm -rf htmlcov/ .coverage coverage.xml test-results.xml
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    @echo "✅ Cleaned all build artifacts"

# =============================================================================
# CI/CD Helpers
# =============================================================================

# Run full CI pipeline locally
ci: install-dev format-check lint typecheck test-ci security build
    @echo "✅ CI pipeline completed successfully"

# Run security scan (bandit)
security:
    @{{check-venv}}
    {{venv}} pip install bandit
    {{venv}} bandit -r src/ -ll --skip B101

# =============================================================================
# Azure Infrastructure
# =============================================================================

# Show Azure OpenAI resource name in a resource group
azure-foundry-show rg="local-code-interpreter-rg":
    @az cognitiveservices account list -g "{{rg}}" --query "[?kind=='AIServices'].name | [0]" -o tsv

# Deploy Azure AI Foundry resources (hub, project, and model)
azure-foundry-deploy rg="local-code-interpreter-rg" loc="eastus" model="gpt-4o":
    #!/usr/bin/env bash
    set -euo pipefail
    baseName="code-interp-$(whoami)"
    echo "🚀 Deploying Azure AI Foundry: {{model}} in {{loc}}"
    if ! az group exists -n "{{rg}}" --output tsv | grep -q true; then \
      echo "Creating resource group {{rg}}..."; \
      az group create -n "{{rg}}" -l "{{loc}}"; \
    fi
    az deployment group create \
      --resource-group "{{rg}}" \
      --template-file infra/azure-openai.bicep \
      --parameters \
        baseName="$baseName" \
        modelName="{{model}}" \
        location="{{loc}}"
    endpoint=$(az deployment group show -g "{{rg}}" -n azure-openai --query properties.outputs.endpoint.value -o tsv)
    foundryName=$(az deployment group show -g "{{rg}}" -n azure-openai --query properties.outputs.foundryName.value -o tsv)
    echo "✅ Deployment complete!"
    echo ""
    echo "Add to your .env file:"
    echo "AZURE_OPENAI_ENDPOINT=$endpoint"
    echo "AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME={{model}}"
    echo ""
    echo "⚠️  Don't forget to run: just azure-foundry-grant-access {{rg}}"

# Grant current user access to Azure AI Foundry resources
azure-foundry-grant-access rg="local-code-interpreter-rg":
    #!/usr/bin/env bash
    set -euo pipefail
    email=$(az account show --query user.name -o tsv)
    subscriptionId=$(az account show --query id -o tsv)
    foundryName=$(az cognitiveservices account list -g "{{rg}}" --query "[?kind=='AIServices'].name | [0]" -o tsv)
    if [ -z "$foundryName" ]; then \
      echo "❌ No AI Services account found in resource group {{rg}}"; \
      exit 1; \
    fi
    echo "🔐 Granting Azure AI User role to $email..."
    az role assignment create \
      --role "Azure AI User" \
      --assignee "$email" \
      --scope "/subscriptions/$subscriptionId/resourceGroups/{{rg}}/providers/Microsoft.CognitiveServices/accounts/$foundryName"

# List soft-deleted Cognitive Services accounts
azure-foundry-list-deleted:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "🔍 Listing soft-deleted Cognitive Services accounts..."
    az cognitiveservices account list-deleted -o table

# Purge soft-deleted Cognitive Services account
azure-foundry-purge-deleted name loc="eastus" rg="local-code-interpreter-rg":
    #!/usr/bin/env bash
    set -euo pipefail
    echo "🗑️  Purging soft-deleted account '{{name}}' in {{loc}}..."
    az cognitiveservices account purge \
      --name "{{name}}" \
      --location "{{loc}}" \
      -g "{{rg}}"
    echo "✅ Account purged successfully!"

# List Azure OpenAI deployments and rate limits
azure-foundry-deployments rg="local-code-interpreter-rg":
    #!/usr/bin/env bash
    set -euo pipefail
    foundryName=$(az cognitiveservices account list -g "{{rg}}" --query "[?kind=='AIServices'].name | [0]" -o tsv)
    if [ -z "$foundryName" ]; then \
      echo "❌ No AI Services account found in resource group {{rg}}"; \
      exit 1; \
    fi
    echo "📊 Deployments for $foundryName in {{rg}}:"
    echo ""
    az cognitiveservices account deployment list \
      --name "$foundryName" \
      --resource-group "{{rg}}" \
      --query "[].{Name:name, Model:properties.model.name, Version:properties.model.version, TPM:properties.rateLimits[?key=='token'].count|[0], RPM:properties.rateLimits[?key=='request'].count|[0]}" \
      -o table
    echo ""
    echo "💡 To increase TPM, run: just azure-foundry-set-capacity <deployment> <tpm> {{rg}}"

# Update deployment capacity (TPM in thousands, e.g. 30 = 30K TPM)
azure-foundry-set-capacity deployment tpm rg="local-code-interpreter-rg":
    #!/usr/bin/env bash
    set -euo pipefail
    foundryName=$(az cognitiveservices account list -g "{{rg}}" --query "[?kind=='AIServices'].name | [0]" -o tsv)
    if [ -z "$foundryName" ]; then \
      echo "❌ No AI Services account found in resource group {{rg}}"; \
      exit 1; \
    fi
    # Get current deployment details
    deployment=$(az cognitiveservices account deployment show \
      --name "$foundryName" \
      --resource-group "{{rg}}" \
      --deployment-name "{{deployment}}" \
      -o json)
    modelName=$(echo "$deployment" | jq -r '.properties.model.name')
    modelVersion=$(echo "$deployment" | jq -r '.properties.model.version')
    modelFormat=$(echo "$deployment" | jq -r '.properties.model.format')
    skuName=$(echo "$deployment" | jq -r '.sku.name')
    echo "🔧 Updating {{deployment}} capacity to {{tpm}}K TPM..."
    az cognitiveservices account deployment create \
      --name "$foundryName" \
      --resource-group "{{rg}}" \
      --deployment-name "{{deployment}}" \
      --model-name "$modelName" \
      --model-version "$modelVersion" \
      --model-format "$modelFormat" \
      --sku-name "$skuName" \
      --sku-capacity "{{tpm}}"
    echo "✅ Capacity updated! Run 'just azure-foundry-deployments {{rg}}' to verify."

