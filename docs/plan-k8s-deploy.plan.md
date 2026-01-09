# Plan: Dockerize and Deploy to Kubernetes with Azure OpenAI Workload Identity

Package the local-code-interpreter-tool as a Docker container with Hyperlight support, create Kubernetes manifests with Azure Load Balancer for external access, and configure Azure OpenAI authentication using AKS Workload Identity.

## Steps

### 1. Create Dockerfile ✅ COMPLETED

Create `Dockerfile` at project root with multi-stage build:
- Use `python:3.12-slim` base image
- Install dependencies from `requirements.txt`, then install the package
- Set `ENTRYPOINT` to `python -m local_code_interpreter --devui --port 8090`
- Add optional `--hyperlight` flag via environment variable

### 2. Create .dockerignore ✅ COMPLETED

Create `.dockerignore` at project root to exclude:
- `htmlcov/`, `__pycache__/`, `.git/`, `*.egg-info/`
- `vendor/hyperlight-nanvix/target/`, `tests/`, `docs/`

### 3. Create Kubernetes Manifests ✅ COMPLETED

Create `k8s/` directory with:

| File | Purpose |
|------|---------|
| `namespace.yaml` | Dedicated namespace (`local-code-interpreter`) |
| `configmap.yaml` | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME` |
| `serviceaccount.yaml` | ServiceAccount with Workload Identity annotations |
| `deployment.yaml` | Deployment with Hyperlight pod spec and Workload Identity |
| `service.yaml` | ClusterIP service on port 8090 (use `just k8s-port-forward` for local access) |

#### Deployment Pod Spec (Hyperlight)

```yaml
spec:
  automountServiceAccountToken: true  # Required for workload identity
  serviceAccountName: local-code-interpreter
  securityContext:
    runAsNonRoot: true
    runAsUser: 65534
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      resources:
        limits:
          hyperlight.dev/hypervisor: "1"
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
```

#### Workload Identity Labels/Annotations

- Pod label: `azure.workload.identity/use: "true"`
- ServiceAccount annotations:
  - `azure.workload.identity/client-id: <MANAGED_IDENTITY_CLIENT_ID>`

### 4. Update agent.py ✅ COMPLETED

Modify `src/local_code_interpreter/agent.py` line ~47:

```python
# Before
from azure.identity import AzureCliCredential
return AzureOpenAIResponsesClient(credential=AzureCliCredential())

# After
from azure.identity import DefaultAzureCredential
return AzureOpenAIResponsesClient(credential=DefaultAzureCredential())
```

This supports Workload Identity, Managed Identity, and CLI fallback automatically.

### 5. Update justfile ✅ COMPLETED

Add new commands with configurable `IMAGE_REGISTRY` (defaults to ACR pattern):

```just
# Configuration
IMAGE_REGISTRY := env_var_or_default("IMAGE_REGISTRY", "myacr.azurecr.io")
IMAGE_NAME := "local-code-interpreter"
IMAGE_TAG := env_var_or_default("IMAGE_TAG", "latest")
IMAGE := IMAGE_REGISTRY + "/" + IMAGE_NAME + ":" + IMAGE_TAG

# Azure configuration
AZURE_SUBSCRIPTION := env_var_or_default("AZURE_SUBSCRIPTION", "")
AZURE_RESOURCE_GROUP := env_var_or_default("AZURE_RESOURCE_GROUP", "")
AZURE_LOCATION := env_var_or_default("AZURE_LOCATION", "eastus")
AZURE_OPENAI_RESOURCE := env_var_or_default("AZURE_OPENAI_RESOURCE", "")
MANAGED_IDENTITY_CLIENT_ID := env_var_or_default("MANAGED_IDENTITY_CLIENT_ID", "")
AKS_CLUSTER := env_var_or_default("AKS_CLUSTER", "")
K8S_NAMESPACE := "local-code-interpreter"
K8S_SERVICE_ACCOUNT := "local-code-interpreter"

# Docker
docker-build:
    docker build -t {{IMAGE}} .

docker-push:
    docker push {{IMAGE}}

# Kubernetes
k8s-deploy:
    kubectl apply -f k8s/

k8s-delete:
    kubectl delete -f k8s/

# AKS Cluster Setup
azure-aks-create:
    az aks create \
        --name {{AKS_CLUSTER}} \
        --resource-group {{AZURE_RESOURCE_GROUP}} \
        --location {{AZURE_LOCATION}} \
        --enable-oidc-issuer \
        --enable-workload-identity \
        --generate-ssh-keys

azure-aks-enable-workload-identity:
    az aks update \
        --name {{AKS_CLUSTER}} \
        --resource-group {{AZURE_RESOURCE_GROUP}} \
        --enable-oidc-issuer \
        --enable-workload-identity

azure-aks-get-credentials:
    az aks get-credentials \
        --name {{AKS_CLUSTER}} \
        --resource-group {{AZURE_RESOURCE_GROUP}}

# Azure Workload Identity Setup
azure-identity-create:
    az identity create \
        --name local-code-interpreter \
        --resource-group {{AZURE_RESOURCE_GROUP}} \
        --location {{AZURE_LOCATION}}

azure-identity-federate:
    #!/usr/bin/env bash
    AKS_OIDC_ISSUER=$(az aks show \
        --name {{AKS_CLUSTER}} \
        --resource-group {{AZURE_RESOURCE_GROUP}} \
        --query "oidcIssuerProfile.issuerUrl" -o tsv)
    
    az identity federated-credential create \
        --name kubernetes-federated \
        --identity-name local-code-interpreter \
        --resource-group {{AZURE_RESOURCE_GROUP}} \
        --issuer "$AKS_OIDC_ISSUER" \
        --subject "system:serviceaccount:{{K8S_NAMESPACE}}:{{K8S_SERVICE_ACCOUNT}}" \
        --audiences "api://AzureADTokenExchange"

azure-identity-show:
    az identity show \
        --name local-code-interpreter \
        --resource-group {{AZURE_RESOURCE_GROUP}} \
        --query clientId -o tsv

# Azure Role Assignment
azure-role-assign:
    az role assignment create \
        --assignee {{MANAGED_IDENTITY_CLIENT_ID}} \
        --role "Cognitive Services OpenAI User" \
        --scope /subscriptions/{{AZURE_SUBSCRIPTION}}/resourceGroups/{{AZURE_RESOURCE_GROUP}}/providers/Microsoft.CognitiveServices/accounts/{{AZURE_OPENAI_RESOURCE}}
```

### 6. Update README.md ✅ COMPLETED

Add deployment section covering:
- Docker build command
- AKS Workload Identity setup
- Role assignment explanation
- Kubernetes deployment steps

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `IMAGE_REGISTRY` | Container registry URL | `myacr.azurecr.io` |
| `IMAGE_TAG` | Image tag | `latest` |
| `AZURE_SUBSCRIPTION` | Azure subscription ID | (required) |
| `AZURE_RESOURCE_GROUP` | Resource group name | (required) |
| `AZURE_LOCATION` | Azure region | `eastus` |
| `AZURE_OPENAI_RESOURCE` | Azure OpenAI resource name | (required) |
| `AKS_CLUSTER` | AKS cluster name | (required) |
| `MANAGED_IDENTITY_CLIENT_ID` | User-assigned managed identity client ID | (required) |

### AKS Workload Identity Setup

Full setup from scratch:
```bash
# 1. Create AKS cluster with workload identity enabled (or update existing)
just azure-aks-create
# OR for existing cluster:
just azure-aks-enable-workload-identity

# 2. Get cluster credentials
just azure-aks-get-credentials

# 3. Create user-assigned managed identity
just azure-identity-create

# 4. Get the client ID (set as MANAGED_IDENTITY_CLIENT_ID)
just azure-identity-show

# 5. Create federated credential linking to AKS
just azure-identity-federate

# 6. Assign role to access Azure OpenAI
just azure-role-assign

# 7. Build and push container image
just docker-build
just docker-push

# 8. Deploy to Kubernetes
just k8s-deploy
```

## Files to Create/Modify

| Action | File |
|--------|------|
| Create | `Dockerfile` |
| Create | `.dockerignore` |
| Create | `k8s/namespace.yaml` |
| Create | `k8s/configmap.yaml` |
| Create | `k8s/serviceaccount.yaml` |
| Create | `k8s/deployment.yaml` |
| Create | `k8s/service.yaml` |
| Modify | `src/local_code_interpreter/agent.py` |
| Modify | `justfile` |
| Modify | `README.md` |
