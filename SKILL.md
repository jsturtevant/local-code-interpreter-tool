---
name: local-code-interpreter
description: Execute code in a sandboxed environment for calculations, testing snippets, and verifying logic. Use this when users request running code, performing calculations, testing algorithms, data processing, or demonstrating functionality. Supports Python (subprocess) and Hyperlight VM-isolated execution for JavaScript and Python.
license: Complete terms in LICENSE.txt
---

# Local Code Interpreter Skill

A code execution skill that runs code in sandboxed environments using the Microsoft Agent Framework.

## When to Use

Use this skill when users want to:
- Perform calculations or verify mathematical results
- Test code snippets or algorithms
- Run or execute code
- Process data or demonstrate functionality

## Execution Environments

- **Python subprocess**: Fast execution with timeout protection (default)
- **Hyperlight VM sandbox**: High-security VM-isolated execution supporting JavaScript and Python

## Important Notes

- Always use `print()` (Python) or `console.log()` (JavaScript) to display output
- Code runs in isolated environments with no network access
- Outputs are truncated at 10KB for safety
