@description('Base name for the Microsoft Foundry resources')
param baseName string

@description('Azure region to deploy to (e.g., eastus2, swedencentral)')
param location string = resourceGroup().location

@description('Tags to apply to resources')
param tags object = {}

@description('Model name to deploy (e.g., o1, gpt-4o, gpt-4o-mini, claude-3-5-sonnet)')
param modelName string

@description('Logical deployment name for the model (used by API calls)')
param deploymentName string = modelName

@description('Desired capacity in thousands of tokens per minute (e.g., 30 = 30K TPM)')
param capacity int = 30

@description('Model format/provider (OpenAI, Anthropic, etc.)')
param modelFormat string = 'OpenAI'

@description('Name of the Foundry project')
param projectName string = '${baseName}-project'

@description('SKU name for deployment (Standard, GlobalStandard, or ProvisionedManaged)')
param deploymentSkuName string = 'GlobalStandard'

// Microsoft Foundry account (AI Services variant that supports projects)
resource foundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: '${baseName}-foundry'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  properties: {
    // Required to work in AI Foundry portal
    allowProjectManagement: true
    // Defines developer API endpoint subdomain
    customSubDomainName: '${baseName}-foundry'
    // Disable local auth (use Azure AD only)
    disableLocalAuth: true
  }
  tags: tags
}

// Foundry project (groups inputs/outputs for one use case)
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: foundry
  name: projectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

// Model deployment (at account level, accessible by all projects)
resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: foundry
  name: deploymentName
  sku: {
    name: deploymentSkuName
    capacity: capacity
  }
  properties: {
    model: {
      format: modelFormat
      name: modelName
    }
  }
}

@description('The Microsoft Foundry portal URL')
output foundryPortalUrl string = 'https://ai.azure.com/resource${foundry.id}'

@description('The project portal URL')
output projectPortalUrl string = 'https://ai.azure.com/resource${foundry.id}/project/${project.name}'

@description('The endpoint URL (OpenAI-compatible API)')
output endpoint string = foundry.properties.endpoint

@description('The Foundry API endpoint (new unified API)')
output foundryApiEndpoint string = foundry.properties.endpoints.AIServices

@description('The deployment name to use in API calls')
output outputDeploymentName string = deployment.name

@description('The Foundry resource ID')
output foundryId string = foundry.id

@description('The Foundry resource name')
output foundryName string = foundry.name

@description('The project resource ID')
output projectId string = project.id

@description('The project name')
output outputProjectName string = project.name
