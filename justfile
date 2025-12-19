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
    {{venv}} pip install -e .
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

# Update dependencies
update:
    @{{check-venv}}
    {{venv}} pip install --upgrade -r requirements.txt

# =============================================================================
# Running the Agent
# =============================================================================

# Run the full agent
run:
    @{{check-venv}}
    {{venv}} python -m local_code_interpreter.agent

# Run in interactive chat mode
interactive:
    @{{check-venv}}
    {{venv}} python -m local_code_interpreter.agent --interactive

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

# Run security scan (bandit + safety)
security:
    @{{check-venv}}
    {{venv}} pip install bandit safety
    {{venv}} bandit -r src/ -ll --skip B101
    {{venv}} safety check -r requirements.txt

# =============================================================================
# Azure Infrastructure
# =============================================================================

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

