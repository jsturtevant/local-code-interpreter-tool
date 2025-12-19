"""Local Code Interpreter Tool - Built with Microsoft Agent Framework"""

__version__ = "0.1.0"

from .agent import (
    create_interpreter_agent,
    INTERPRETER_AGENT_INSTRUCTIONS_PYTHON,
    INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT,
)
from .tools import CodeExecutionTool, HYPERLIGHT_AVAILABLE

__all__ = [
    "create_interpreter_agent",
    "INTERPRETER_AGENT_INSTRUCTIONS_PYTHON",
    "INTERPRETER_AGENT_INSTRUCTIONS_HYPERLIGHT",
    "CodeExecutionTool",
    "HYPERLIGHT_AVAILABLE",
]
