"""Local Code Interpreter Tool - Built with Microsoft Agent Framework"""

__version__ = "0.1.0"

from .agent import create_interpreter_agent, INTERPRETER_AGENT_INSTRUCTIONS
from .tools import CodeExecutionTool

__all__ = [
    "create_interpreter_agent",
    "INTERPRETER_AGENT_INSTRUCTIONS",
    "CodeExecutionTool",
]
