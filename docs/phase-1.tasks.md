# Task: Implement Phase 1 - Python Subprocess Execution

## Goal
Add an `execute_code` tool that allows the LLM to run Python code in a sandboxed subprocess with timeout protection.

## Implementation Steps

### Step 1: Add `_run_python` helper function to `tools.py`
- [x] Create async function to execute Python code in subprocess
- [x] Implement timeout handling with `asyncio.wait_for`
- [x] Strip environment variables for security
- [x] Truncate large outputs (10KB limit)
- [x] Capture both stdout and stderr
- [x] Use `sys.executable` for reliable Python path resolution

### Step 2: Create `CodeExecutionTool` class in `tools.py`
- [x] Subclass `AIFunction` from agent_framework
- [x] Add `timeout` parameter (default 30s)
- [x] Add `approval_mode` parameter (default "always_require")
- [x] Implement `_execute` async method
- [x] Add proper docstrings and type hints

### Step 3: Update `agent.py`
- [x] Import `CodeExecutionTool` from tools
- [x] Register tool in `ChatAgent` tools list
- [x] Update agent instructions to explain code execution capability

### Step 4: Add tests in `test_tools.py`
- [x] Test successful code execution
- [x] Test timeout handling
- [x] Test output truncation
- [x] Test stderr capture
- [x] Test error handling

### Step 5: Verify everything works
- [x] Run `just check` to verify code quality
- [x] Run `just test` to verify tests pass

### Step 6: Cleanup
- [x] Remove unrelated tools (get_release_status, list_pending_approvals, etc.)
- [x] Update `__init__.py` exports
- [x] Remove unrelated tests

## Acceptance Criteria
- [x] CodeExecutionTool can execute simple Python code
- [x] Timeout kills long-running code
- [x] Output is truncated for large responses
- [x] Errors are captured and returned
- [x] All tests pass (13/13)
- [x] Code passes lint/format/typecheck

## Status: ✅ COMPLETE

Phase 1 has been successfully implemented. The `CodeExecutionTool` is now available and working with:
- Sandboxed subprocess execution using `sys.executable`
- Configurable timeout (default 30s)
- Output truncation at 10KB
- Security via stripped environment variables
- Full test coverage (13 tests)
