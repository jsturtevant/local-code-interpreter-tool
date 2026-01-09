# Feature: Azure Foundry Claude Opus Support

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files etc.

## Feature Description

Add support for using Claude Opus models hosted on Azure AI Foundry as an alternative backend for the local code interpreter agent. This extends the current OpenAI/Azure OpenAI support to include Anthropic Claude models accessible through the Microsoft Agent Framework's `agent-framework-anthropic` package.

## User Story

As a developer using Azure AI Foundry
I want to use Claude Opus models for code interpretation
So that I can leverage Anthropic's frontier AI capabilities with Azure's enterprise security and compliance

## Problem Statement

The local code interpreter currently only supports OpenAI and Azure OpenAI backends. Users who have access to Claude models deployed in Azure AI Foundry cannot use them with this tool, limiting their flexibility in choosing the best model for their use cases.

## Solution Statement

Extend the agent configuration to detect and use Azure Foundry Claude deployments when configured. The implementation will:
1. Add a new `agent-framework-anthropic` dependency
2. Create an `AnthropicClient`-based chat client factory for Azure Foundry Claude
3. Update the environment detection logic to support Claude configuration
4. Maintain backward compatibility with existing OpenAI/Azure OpenAI configurations

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Low-Medium
**Primary Systems Affected**: `agent.py` (client creation and configuration)
**Dependencies**: 
- `agent-framework-anthropic` (new Python package)
- `anthropic>=0.74.0` (for Azure Foundry support via `AsyncAnthropicFoundry`)
- `azure-identity` (already present for Azure credential support)

**Key Insight**: Azure Foundry Claude requires `AZURE_FOUNDRY_RESOURCE` (resource name) and `AZURE_FOUNDRY_MODEL_NAME` env vars. Uses Entra ID authentication via `az login`. The `AZURE_FOUNDRY_MODEL_NAME` env var works for both GPT and Claude models.

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- [src/local_code_interpreter/agent.py](src/local_code_interpreter/agent.py) (lines 1-60) - Why: Contains `_is_azure_configured()` and `_create_chat_client()` functions that need to be extended
- [src/local_code_interpreter/agent.py](src/local_code_interpreter/agent.py) (lines 185-250) - Why: Contains `create_interpreter_agent()` factory function pattern to follow
- [.env.example](.env.example) - Why: Configuration template that needs new Claude environment variables
- [CLAUDE.md](CLAUDE.md) (lines 100-140) - Why: Configuration documentation that needs updating
- [requirements.txt](requirements.txt) - Why: Dependencies file to update
- [tests/test_tools.py](tests/test_tools.py) - Why: Test pattern examples for the project

### New Files to Create

- None - all changes are modifications to existing files

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Microsoft Agent Framework - Anthropic Agents (Python)](https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-types/anthropic-agent?pivots=programming-language-python)
  - Specific section: Using Anthropic on Foundry
  - Why: Shows exact pattern for creating Azure Foundry Claude client with `AsyncAnthropicFoundry`

- [Deploy and use Claude models in Microsoft Foundry](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/how-to/use-foundry-models-claude)
  - Specific section: Use the Messages API to work with Claude models
  - Why: Shows authentication patterns (API key and Microsoft Entra ID)

- [Foundry Models from partners - Anthropic section](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/models-from-partners#anthropic)
  - Specific section: Anthropic models table
  - Why: Lists available Claude models and their capabilities (claude-opus-4-5, claude-sonnet-4-5, claude-haiku-4-5, claude-opus-4-1)

### Patterns to Follow

**Environment Detection Pattern** (from `agent.py` lines 36-40):
```python
def _is_azure_configured() -> bool:
    """Check if Azure OpenAI is configured."""
    return bool(os.getenv("AZURE_OPENAI_ENDPOINT"))
```

**Client Creation Pattern** (from `agent.py` lines 43-55):
```python
def _create_chat_client():
    """Create the appropriate chat client based on environment configuration."""
    if _is_azure_configured():
        from agent_framework.azure import AzureOpenAIResponsesClient
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if api_key:
            return AzureOpenAIResponsesClient(api_key=api_key)
        else:
            from azure.identity import DefaultAzureCredential
            return AzureOpenAIResponsesClient(credential=DefaultAzureCredential())
    else:
        return OpenAIResponsesClient()
```

**Agent Factory Pattern** (from `agent.py` lines 185-245):
```python
def create_interpreter_agent(
    environment: str = "python",
    timeout: int = 30,
    hyperlight_language: HyperlightLanguage = "javascript",
    name: str = "code-interpreter",
    description: str | None = None,
) -> ChatAgent:
    """Create and configure the local code interpreter agent."""
    # ... configuration logic
    return ChatAgent(
        name=name,
        description=description,
        chat_client=_create_chat_client(),
        instructions=instructions,
        tools=tools,
        middleware=[...],
    )
```

**Environment Variable Pattern** (from `.env.example`):
```env
# Option X: Description
ENV_VAR_NAME=value
```

---

## IMPLEMENTATION PLAN

### Phase 1: Dependencies and Configuration

Add the required `agent-framework-anthropic` package dependency and define the new environment variables for Azure Foundry Claude configuration.

**Tasks:**
- Update `requirements.txt` with new dependencies
- Update `.env.example` with Claude configuration variables
- Update `CLAUDE.md` documentation with new configuration option

### Phase 2: Core Implementation

Extend the client detection and creation logic in `agent.py` to support Azure Foundry Claude as a third backend option.

**Tasks:**
- Add detection function for Azure Foundry Claude configuration
- Create client factory for Anthropic Azure Foundry
- Update `_create_chat_client()` to use new detection priority
- Update backend description strings throughout the file

### Phase 3: Testing & Validation

Verify the implementation works with mocked and real Azure Foundry Claude deployments.

**Tasks:**
- Manual testing with Azure Foundry Claude deployment
- Verify backward compatibility with OpenAI/Azure OpenAI
- Run existing test suite to ensure no regressions

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### 1. UPDATE requirements.txt

- **IMPLEMENT**: Add `agent-framework-anthropic` package for Anthropic support
- **PATTERN**: Follow existing package format in [requirements.txt](requirements.txt)
- **IMPORTS**: None (package manager file)
- **GOTCHA**: Use `--pre` flag may be needed during pip install as package may be in preview
- **VALIDATE**: `pip install agent-framework-anthropic --pre && python -c "from agent_framework.anthropic import AnthropicClient; print('OK')"`

Add after the existing dependencies:

```txt
# Anthropic support for Azure Foundry Claude
agent-framework-anthropic
anthropic>=0.74.0
```

### 2. UPDATE .env.example

- **IMPLEMENT**: Add new Azure Foundry Claude configuration section
- **PATTERN**: Follow existing section format in [.env.example](.env.example)
- **IMPORTS**: None (configuration file)
- **GOTCHA**: Uses separate env vars from Azure OpenAI - different API endpoint
- **VALIDATE**: Visual inspection of file format

Add new section for Azure Foundry Claude:

```env
# =============================================================================
# Option 3: Azure AI Foundry Claude (Anthropic)
# =============================================================================
# Use `az login` to authenticate with Microsoft Entra ID

# Available models: claude-opus-4-5, gpt-4o, etc.

# =============================================================================
# name of your foundry resournce
AZURE_FOUNDRY_RESOURCE=<your-resource-name>
AZURE_FOUNDRY_MODEL_NAME=claude-opus-4-5
```

### 3. UPDATE agent.py - Add detection function

- **IMPLEMENT**: Add `_is_azure_foundry_claude_configured()` function
- **PATTERN**: MIRROR `_is_azure_configured()` function at [agent.py](src/local_code_interpreter/agent.py#L36)
- **IMPORTS**: None (uses existing `os` import)
- **GOTCHA**: Check for `AZURE_FOUNDRY_RESOURCE` AND model name contains "claude"
- **VALIDATE**: `python -c "from local_code_interpreter.agent import _is_azure_foundry_claude_configured; print(_is_azure_foundry_claude_configured())"`

Add after `_is_azure_configured()` function:

```python
def _is_azure_foundry_claude_configured() -> bool:
    """Check if Azure Foundry Claude is configured.
    
    Returns True if AZURE_FOUNDRY_RESOURCE is set and model name contains 'claude'.
    """
    resource = os.getenv("AZURE_FOUNDRY_RESOURCE")
    model_name = os.getenv("AZURE_FOUNDRY_MODEL_NAME", "")
    return bool(resource) and "claude" in model_name.lower()
```

### 4. UPDATE agent.py - Add Claude client factory

- **IMPLEMENT**: Create `_create_anthropic_client()` function that returns an AnthropicClient
- **PATTERN**: MIRROR `_create_chat_client()` function at [agent.py](src/local_code_interpreter/agent.py#L43)
- **IMPORTS**: Add `from agent_framework.anthropic import AnthropicClient` and `from anthropic import AnthropicFoundry`
- **GOTCHA**: Use `AZURE_FOUNDRY_RESOURCE` to construct base URL; Entra ID auth only
- **VALIDATE**: `python -c "from local_code_interpreter.agent import _create_anthropic_client; print(type(_create_anthropic_client()))"`

Add after `_create_chat_client()` function:

```python
def _create_anthropic_client():
    """Create an Anthropic client for Azure Foundry Claude.
    
    Uses AZURE_FOUNDRY_RESOURCE to construct the base URL.
    Authenticates via Microsoft Entra ID (az login).
    """
    from agent_framework.anthropic import AnthropicClient
    from anthropic import AnthropicFoundry
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    
    resource = os.getenv("AZURE_FOUNDRY_RESOURCE")
    if not resource:
        raise ValueError("AZURE_FOUNDRY_RESOURCE environment variable not set")
    
    base_url = f"https://{resource}.services.ai.azure.com/anthropic"
    
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default"
    )
    
    return AnthropicClient(
        anthropic_client=AnthropicFoundry(
            azure_ad_token_provider=token_provider,
            base_url=base_url
        )
    )
```

### 5. UPDATE agent.py - Modify create_interpreter_agent for Claude

- **IMPLEMENT**: Update `create_interpreter_agent()` to use AnthropicClient when Claude is configured
- **PATTERN**: Follow existing factory pattern at [agent.py](src/local_code_interpreter/agent.py#L185)
- **IMPORTS**: None (uses functions defined above)
- **GOTCHA**: AnthropicClient uses `create_agent()` method, not `ChatAgent` class. The agent creation pattern is different - need to use the Anthropic-specific agent creation method
- **VALIDATE**: `python -c "from local_code_interpreter.agent import create_interpreter_agent; print(create_interpreter_agent)"`

The key insight is that `AnthropicClient.create_agent()` returns a `BaseAgent`, not requiring a separate `ChatAgent` instantiation. We need to restructure to support both patterns.

Update the function to detect Claude config first and use appropriate agent creation:

```python
def create_interpreter_agent(
    environment: str = "python",
    timeout: int = 30,
    hyperlight_language: HyperlightLanguage = "javascript",
    name: str = "code-interpreter",
    description: str | None = None,
) -> ChatAgent:
    """Create and configure the local code interpreter agent.

    Automatically uses Azure Foundry Claude if AZURE_FOUNDRY_RESOURCE is set,
    else uses Azure OpenAI if AZURE_OPENAI_ENDPOINT is set,
    otherwise uses OpenAI.
    """
    # ... (keep existing environment/hyperlight handling logic)
    
    # Determine backend type
    if _is_azure_foundry_claude_configured():
        backend = "Azure Foundry Claude"
    elif _is_azure_configured():
        backend = "Azure OpenAI"
    else:
        backend = "OpenAI"
    
    # ... (keep existing tools and instructions logic)
    
    if _is_azure_foundry_claude_configured():
        # Use Anthropic client for Claude models
        deployment_name = os.getenv("AZURE_FOUNDRY_MODEL_NAME")
        client = _create_anthropic_client()
        return client.create_agent(
            name=name,
            instructions=instructions,
            tools=tools,
            model_id=deployment_name,
        )
    else:
        # Use OpenAI-compatible client
        return ChatAgent(
            name=name,
            description=description,
            chat_client=_create_chat_client(),
            instructions=instructions,
            tools=tools,
            middleware=[
                RetryOnRateLimitMiddleware(
                    max_retries=5,
                    min_wait=1.0,
                    max_wait=60.0,
                ),
            ],
        )
```

### 6. UPDATE agent.py - Update backend display strings

- **IMPLEMENT**: Update all places that display "Azure OpenAI" or "OpenAI" backend to include "Azure Foundry Claude"
- **PATTERN**: Search for `_is_azure_configured()` usage and add Claude detection
- **IMPORTS**: None
- **GOTCHA**: Multiple locations: `run_interactive_session()`, `run_example_queries()`, `run_devui()`
- **VALIDATE**: `grep -n "Azure OpenAI\|OpenAI" src/local_code_interpreter/agent.py`

Update the backend detection helper to be reusable:

```python
def _get_backend_name() -> str:
    """Get the name of the configured backend."""
    if _is_azure_foundry_claude_configured():
        return "Azure Foundry Claude"
    elif _is_azure_configured():
        return "Azure OpenAI"
    else:
        return "OpenAI"
```

Then use `_get_backend_name()` in:
- `create_interpreter_agent()` (line ~230)
- `run_interactive_session()` (line ~265)
- `run_example_queries()` (line ~350)
- `run_devui()` (line ~420)

### 7. UPDATE CLAUDE.md - Add configuration section

- **IMPLEMENT**: Add Azure Foundry Claude configuration documentation
- **PATTERN**: Follow existing Azure OpenAI section format at [CLAUDE.md](CLAUDE.md#L110)
- **IMPORTS**: None (documentation file)
- **GOTCHA**: This is a separate configuration from Azure OpenAI
- **VALIDATE**: Visual inspection of documentation format

Add new section for Azure Foundry Claude:

```markdown
### Azure AI Foundry Claude

```env
# Resource name (not full URL)
AZURE_FOUNDRY_RESOURCE="your-resource-name"

# Model name - use a Claude model (detected by name containing "claude")
AZURE_FOUNDRY_MODEL_NAME="claude-opus-4-5"
```

Authenticate with `az login` before running. Uses Microsoft Entra ID.

> **Note**: Claude is auto-detected when `AZURE_FOUNDRY_MODEL_NAME` contains "claude". Requires Enterprise or MCA-E Azure subscription. Available models: `claude-opus-4-5`, `claude-sonnet-4-5`, `claude-haiku-4-5`, `claude-opus-4-1`. Regions: East US2, Sweden Central.
```

---

## TESTING STRATEGY

### Unit Tests

The existing test suite should continue to pass. Add the following tests if time permits:

1. **Test `_is_azure_foundry_claude_configured()`**:
   - Returns `False` when `AZURE_FOUNDRY_RESOURCE` is not set
   - Returns `False` when model name doesn't contain "claude"
   - Returns `True` when `AZURE_FOUNDRY_RESOURCE` is set AND model name contains "claude"

2. **Test `_get_backend_name()`**:
   - Returns correct backend name based on env configuration

### Integration Tests

Manual testing with an actual Azure Foundry Claude deployment:

1. Set up Claude deployment in Azure AI Foundry (East US2 or Sweden Central)
2. Configure environment variables
3. Run `just run` and verify agent connects successfully
4. Run `just interactive` and test code execution queries

### Edge Cases

- [ ] Missing `AZURE_FOUNDRY_RESOURCE` should fall back to Azure OpenAI or OpenAI
- [ ] `AZURE_FOUNDRY_RESOURCE` set with Claude model name should use Anthropic client
- [ ] `AZURE_FOUNDRY_RESOURCE` set with GPT model name should NOT use Anthropic client
- [ ] Missing `AZURE_FOUNDRY_MODEL_NAME` should raise helpful error
- [ ] Entra ID auth via `az login` should work

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Format code
just format

# Lint code
just lint

# Type check
just typecheck
```

### Level 2: Unit Tests

```bash
# Run all tests
just test
```

### Level 3: Integration Tests

```bash
# Verify imports work
python -c "from local_code_interpreter.agent import _is_azure_foundry_claude_configured, _get_backend_name; print('Imports OK')"

# Verify backward compatibility (should show OpenAI)
unset AZURE_FOUNDRY_RESOURCE
unset AZURE_OPENAI_ENDPOINT
python -c "from local_code_interpreter.agent import _get_backend_name; assert _get_backend_name() == 'OpenAI'"

# Verify Azure OpenAI detection
export AZURE_OPENAI_ENDPOINT="https://test.openai.azure.com"
python -c "from local_code_interpreter.agent import _get_backend_name; assert _get_backend_name() == 'Azure OpenAI'"

# Verify Claude detection when AZURE_FOUNDRY_RESOURCE is set
export AZURE_FOUNDRY_RESOURCE="myresource"
export AZURE_FOUNDRY_MODEL_NAME="claude-opus-4-5"
python -c "from local_code_interpreter.agent import _get_backend_name; assert _get_backend_name() == 'Azure Foundry Claude'"
unset AZURE_FOUNDRY_RESOURCE
unset AZURE_FOUNDRY_MODEL_NAME
unset AZURE_OPENAI_ENDPOINT
```

### Level 4: Manual Validation

With real Azure Foundry Claude deployment configured:

```bash
# Test example queries
just run

# Test interactive mode
just interactive

# Test DevUI
just devui
```

### Level 5: Full CI Pipeline

```bash
just check  # Runs format, lint, typecheck, test
```

---

## ACCEPTANCE CRITERIA

- [x] Feature implements Claude Opus model support via Azure AI Foundry
- [ ] All validation commands pass with zero errors
- [ ] Backward compatibility maintained for OpenAI and Azure OpenAI
- [ ] Detection: Claude used when `AZURE_FOUNDRY_RESOURCE` is set AND model name contains "claude"
- [ ] Base URL constructed from `AZURE_FOUNDRY_RESOURCE`
- [ ] Authentication via Microsoft Entra ID (`az login`)
- [ ] Documentation updated in `.env.example` and `CLAUDE.md`
- [ ] No regressions in existing functionality

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms feature works
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability

---

## NOTES

### Design Decisions

1. **Shared Model Name Env Var**: `AZURE_FOUNDRY_MODEL_NAME` works for both Azure OpenAI (GPT) and Azure Foundry Claude models. Azure Foundry Claude also requires `AZURE_FOUNDRY_RESOURCE` because it uses a different API endpoint (`services.ai.azure.com/anthropic`) than Azure OpenAI (`openai.azure.com`).

2. **Priority Order**: When `AZURE_FOUNDRY_RESOURCE` is set, the Anthropic client takes priority. Otherwise falls back to Azure OpenAI if configured, then OpenAI.

3. **Agent Creation Pattern**: The Anthropic SDK uses a different pattern (`AnthropicClient.create_agent()`) compared to OpenAI (`ChatAgent` with `chat_client`). The implementation handles both patterns transparently.

4. **Entra ID Only**: Uses Microsoft Entra ID authentication via `get_bearer_token_provider(DefaultAzureCredential())`. Run `az login` before use.

### Known Limitations

1. **Region Availability**: Claude models in Azure Foundry are only available in East US2 and Sweden Central regions.

2. **Subscription Requirements**: Only Enterprise and MCA-E Azure subscriptions are eligible for Claude model usage.

3. **Preview Status**: Claude models in Azure Foundry are in preview as of January 2026.

### Alternative Approaches Considered

1. **Separate Agent File**: Could have created a separate `claude_agent.py` file, but this would duplicate significant code and make the codebase harder to maintain.

2. **Plugin Architecture**: Could have implemented a plugin system for backends, but this adds complexity for only 3 supported backends.

### Confidence Score: 9/10

The implementation is straightforward with the simplified single-env-var approach. Main risks:
- `agent-framework-anthropic` package may still be in preview with potential breaking changes
- The `AnthropicClient.create_agent()` return type compatibility with existing `ChatAgent` usage needs verification
- Rate limiting middleware compatibility with Anthropic agents needs testing
- Resource name extraction regex should handle edge cases in endpoint URLs
