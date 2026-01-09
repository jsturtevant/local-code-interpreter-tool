---
name: execute-code
description: Execute JavaScript or Python code in a secure Hyperlight VM sandbox with full isolation. Use this when users request running code, performing calculations, testing algorithms, or demonstrating code behavior with actual output.
---

# Execute Code Skill

Execute JavaScript or Python code in a secure Hyperlight VM sandbox with full isolation.

This skill is **standalone and shareable** - it can be copied to any `.claude/skills/` directory and works independently of the original repository.

## Requirements

- Linux with KVM support (`/dev/kvm`)
- Python 3.8+
- Git (for cloning hyperlight-nanvix)
- Rust toolchain (installed automatically by setup script)

## When to Use

Use this skill when:
- The user asks to run, execute, or test code
- You need to verify calculations or algorithm correctness
- You want to demonstrate code behavior with actual output

## Standalone Installation

To use this skill in a new project or share it with others:

### 1. Copy the Skill
```bash
# Copy the entire execute-code directory to your project
cp -r /path/to/execute-code ~/.claude/skills/
# Or for project-specific use:
cp -r /path/to/execute-code /your/project/.claude/skills/
```

### 2. Run Setup
```bash
cd ~/.claude/skills/execute-code
./scripts/setup.sh
```

The setup script will:
- Create a virtual environment in `.venv`
- Install Rust nightly toolchain (if not present)
- Clone and build `hyperlight-nanvix` from source
- Configure everything for standalone use

### 3. Activate and Use
```bash
source .venv/bin/activate
python3 scripts/run.py --lang javascript --code 'console.log("Hello!");'
```

## Quick Start

### JavaScript
```bash
python3 scripts/run.py --lang javascript --code 'console.log(2 + 2);'
```

### Python
```bash
python3 scripts/run.py --lang python --code 'print(2 + 2)'
```

## Usage Notes

- **JavaScript**: Use `console.log()` to see output
- **Python**: Use `print()` to see output
- Code runs in VM-isolated sandbox (hyperlight-nanvix)
- The skill is self-contained with its own virtual environment

## Examples

### Calculate Fibonacci
```bash
python3 scripts/run.py --lang javascript --code '
const fib = n => n <= 1 ? n : fib(n-1) + fib(n-2);
for (let i = 0; i < 10; i++) console.log("fib(" + i + ") =", fib(i));
'
```

### Prime Numbers
```bash
python3 scripts/run.py --lang python --code '
primes = [n for n in range(2, 50) if all(n % i for i in range(2, int(n**0.5)+1))]
print(f"Primes under 50: {primes}")
'
```

### Execute from File
```bash
python3 scripts/run.py --lang python --file my_script.py
```

## Manual Installation (Alternative)

If you prefer to install dependencies manually:

```bash
# 1. Install Rust nightly
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup install nightly

# 2. Clone and build hyperlight-nanvix
git clone https://github.com/hyperlight-dev/hyperlight-nanvix.git
cd hyperlight-nanvix
pip install maturin
maturin develop --features python
```

## Directory Structure

When installed standalone, the skill has this structure:

```
execute-code/
├── SKILL.md           # This file
├── REFERENCE.md       # Detailed API reference
├── scripts/
│   ├── run.py         # Main execution script
│   └── setup.sh       # Automated setup script
├── .venv/             # Virtual environment (created by setup)
└── vendor/            # hyperlight-nanvix source (created by setup)
    └── hyperlight-nanvix/
```

## See Also

- `REFERENCE.md` - Detailed API and configuration options
- `scripts/run.py` - The self-contained execution script
- `scripts/setup.sh` - Automated setup for standalone use
