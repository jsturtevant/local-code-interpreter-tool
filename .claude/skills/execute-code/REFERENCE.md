# Execute Code - Reference

## Script Usage

```bash
python3 scripts/run.py [OPTIONS]
```

### Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--code` | Yes* | - | The code to execute |
| `--lang` | No | `javascript` | Language: `javascript`, `js`, `python`, or `py` |
| `--file` | No | - | Read code from file instead of --code |

*Either `--code` or `--file` is required.

### Examples

```bash
# Inline JavaScript
python3 scripts/run.py --lang javascript --code 'console.log("Hello!");'

# Inline Python
python3 scripts/run.py --lang python --code 'print("Hello!")'

# Short language aliases
python3 scripts/run.py --lang js --code 'console.log(42);'
python3 scripts/run.py --lang py --code 'print(42)'

# From file
python3 scripts/run.py --lang python --file script.py
```

## Hyperlight Sandbox

The skill uses [hyperlight-nanvix](https://github.com/hyperlight-dev/hyperlight-nanvix) for VM-level code isolation.

### Requirements

- Linux with KVM support
- `/dev/kvm` device accessible
- hyperlight-nanvix Python package

### Supported Languages

| Language | Aliases | Extension | Output Function |
|----------|---------|-----------|-----------------|
| JavaScript | `javascript`, `js` | `.js` | `console.log()` |
| Python | `python`, `py` | `.py` | `print()` |

### Security Model

- Code executes in isolated VM (not just a container)
- No network access from sandbox
- No filesystem access outside sandbox
- Memory and CPU limits enforced by hypervisor

## Direct Python Usage

You can also use the script as a module:

```python
import asyncio
from run import execute_code

# JavaScript
result = asyncio.run(execute_code('console.log(2 + 2);', 'javascript'))
print(result)  # 4

# Python
result = asyncio.run(execute_code('print(sum(range(101)))', 'python'))
print(result)  # 5050
```

## Troubleshooting

### "hyperlight-nanvix not installed"
```bash
# Build from source
git clone https://github.com/hyperlight-dev/hyperlight-nanvix.git
cd hyperlight-nanvix
pip install maturin
maturin develop --features python
```

### "/dev/kvm not accessible"
```bash
# Check KVM availability
ls -la /dev/kvm

# Add user to kvm group
sudo usermod -aG kvm $USER
# Log out and back in for group change to take effect
```

### "No output"
- JavaScript: Wrap expressions in `console.log()`
- Python: Wrap expressions in `print()`

Without explicit output functions, calculations run silently.
