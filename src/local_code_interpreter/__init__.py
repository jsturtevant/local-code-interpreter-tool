"""Local Code Interpreter Tool - Built with Microsoft Agent Framework"""

__version__ = "0.1.0"

from .agent import (
    create_interpreter_agent,
    INTERPRETER_AGENT_INSTRUCTIONS_PYTHON,
    INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT_JS,
    INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT_PY,
)
from .tools import CodeExecutionTool, HyperlightLanguage, HYPERLIGHT_AVAILABLE

__all__ = [
    "create_interpreter_agent",
    "INTERPRETER_AGENT_INSTRUCTIONS_PYTHON",
    "INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT_JS",
    "INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT_PY",
    "CodeExecutionTool",
    "HyperlightLanguage",
    "HYPERLIGHT_AVAILABLE",
]
