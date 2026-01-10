# Microsoft Foundry Infrastructure (Bicep)

Deploys **Microsoft Foundry** - the unified Azure platform for AI agents, models, and enterprise AI operations. This creates the **new Foundry project structure** that opens in the [Microsoft Foundry portal](https://ai.azure.com).

## Quick Start

Deploy Microsoft Foundry with a project and model:

```bash
# Set your parameters
rg="local-code-interpreter-rg"
loc="eastus2"  # Claude models available in: eastus2, swedencentral
model="gpt-5.1-codex-mini"  # See model options below
baseName="code-interp-$(whoami)"

# Create resource group if needed
az group exists -n "$rg" || az group create -n "$rg" -l "$loc"

# Deploy Microsoft Foundry
az deployment group create \
  --resource-group "$rg" \
  --template-file infra/azure-openai.bicep \
  --parameters \
    baseName="$baseName" \
    modelName="$model" \
    deploymentName="$model" \
    location="$loc"

# Capture outputs and add to .env
endpoint=$(az deployment group show -g "$rg" -n azure-openai --query properties.outputs.endpoint.value -o tsv)
projectUrl=$(az deployment group show -g "$rg" -n azure-openai --query properties.outputs.projectPortalUrl.value -o tsv)

echo "AZURE_OPENAI_ENDPOINT=$endpoint" >> .env
echo "AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME=$model" >> .env
echo "# Open your project: $projectUrl"
```

## What Gets Deployed

- **AI Foundry account** - Parent resource for managing AI services
- **AI Foundry project** - Your workspace for building AI agents
- **OpenAI model deployment** - A deployed model (e.g., gpt-4o) ready to use

## Cleanup

```bash
# Delete the resource group
az group delete -n "$rg" --yes --no-wait

# Or purge soft-deleted Foundry resources (to reuse the name)
foundryName="${baseName}-foundry"
az cognitiveservices account purge --name "$foundryName" --resource-group "$rg" --location "$loc"
```

## Outputs

- `foundryPortalUrl`: Direct link to your Foundry account in the portal
- `projectPortalUrl`: Direct link to your project in the **new Foundry portal** ⭐
- `endpoint`: OpenAI-compatible API endpoint
- `foundryApiEndpoint`: New unified Foundry API endpoint (for multi-model support)
- `outputDeploymentName`: The deployment name to use in API calls
- `foundryId`: Resource ID of the Microsoft Foundry account
- `projectId`: Resource ID of the Foundry project
- `foundryName`: Name of the Foundry account
- `outputProjectName`: Name of the project

## Resources

- [Microsoft Foundry Documentation](https://learn.microsoft.com/azure/ai-foundry/what-is-azure-ai-foundry)
- [Bicep Examples](https://github.com/azure-ai-foundry/foundry-samples/tree/main/infrastructure/infrastructure-setup-bicep)

