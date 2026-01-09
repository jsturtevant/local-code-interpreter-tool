# Execute Code Skill

Execute JavaScript or Python code in a secure Hyperlight VM sandbox with full isolation.

## Requirements

- Linux with KVM support (`/dev/kvm`)
- Python 3.8+
- `hyperlight-nanvix` package

## When to Use

Use this skill when:
- The user asks to run, execute, or test code
- You need to verify calculations or algorithm correctness
- You want to demonstrate code behavior with actual output

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
- The script is self-contained - only requires `hyperlight-nanvix`

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

## Installation

```bash
# Option 1: Install from PyPI (when available)
pip install hyperlight-nanvix

# Option 2: Build from source
git clone https://github.com/hyperlight-dev/hyperlight-nanvix.git
cd hyperlight-nanvix
pip install maturin
maturin develop --features python
```

## See Also

- `REFERENCE.md` - Detailed API and configuration options
- `scripts/run.py` - The self-contained execution script
