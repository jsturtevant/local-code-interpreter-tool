#!/usr/bin/env python3
"""Execute code in a Hyperlight VM sandbox.

This is a self-contained script that uses hyperlight-nanvix directly.

Requirements:
    pip install hyperlight-nanvix

Usage:
    python run.py --lang javascript --code 'console.log("Hello!");'
    python run.py --lang python --code 'print("Hello!")'
    python run.py --lang python --file script.py
"""

import argparse
import asyncio
import os
import sys
import tempfile
import uuid

# Check for hyperlight-nanvix
try:
    from hyperlight_nanvix import NanvixSandbox, SandboxConfig
except ImportError:
    print("Error: hyperlight-nanvix is not installed.", file=sys.stderr)
    print("Install it with: pip install hyperlight-nanvix", file=sys.stderr)
    print("Or build from source: https://github.com/hyperlight-dev/hyperlight-nanvix", file=sys.stderr)
    sys.exit(1)


async def execute_code(
    code: str,
    language: str = "javascript",
) -> str:
    """Execute code in hyperlight sandbox.

    Args:
        code: The code to execute.
        language: 'javascript' or 'python'.

    Returns:
        The execution output.
    """
    tmp_dir = tempfile.gettempdir()

    # Create sandbox
    config = SandboxConfig(
        log_directory=tmp_dir,
        tmp_directory=tmp_dir,
    )
    sandbox = NanvixSandbox(config)

    # Write code to temp file
    extension = "py" if language == "python" else "js"
    filename = f"workload_{uuid.uuid4().hex[:8]}.{extension}"
    workload_path = os.path.join(tmp_dir, filename)
    stdout_capture_path = os.path.join(tmp_dir, f"stdout_{uuid.uuid4().hex[:8]}.txt")

    try:
        with open(workload_path, "w") as f:
            f.write(code)

        # Capture stdout at fd level since hyperlight writes directly to fd 1
        original_stdout_fd = os.dup(1)
        try:
            with open(stdout_capture_path, "w") as capture_file:
                os.dup2(capture_file.fileno(), 1)
                sys.stdout.flush()
                try:
                    result = await sandbox.run(workload_path)
                finally:
                    sys.stdout.flush()
                    os.dup2(original_stdout_fd, 1)

            with open(stdout_capture_path, "r") as f:
                captured_stdout = f.read().strip()
        finally:
            os.close(original_stdout_fd)
            if os.path.exists(stdout_capture_path):
                try:
                    os.remove(stdout_capture_path)
                except OSError:
                    pass

        if result.success:
            return captured_stdout if captured_stdout else "Execution completed successfully."
        else:
            error_msg = result.error or "Unknown error"
            return f"Execution failed: {error_msg}"

    except Exception as e:
        return f"Error during sandbox execution: {e}"

    finally:
        if os.path.exists(workload_path):
            try:
                os.remove(workload_path)
            except OSError:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="Execute code in a Hyperlight VM sandbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --lang javascript --code 'console.log(2 + 2);'
  %(prog)s --lang python --code 'print(sum(range(100)))'
  %(prog)s --lang python --file my_script.py
        """,
    )
    parser.add_argument(
        "--code",
        type=str,
        help="Code to execute (use --file for file input)",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Read code from file instead of --code",
    )
    parser.add_argument(
        "--lang",
        type=str,
        choices=["javascript", "python", "js", "py"],
        default="javascript",
        help="Language: javascript (default) or python",
    )

    args = parser.parse_args()

    # Normalize language
    language = args.lang
    if language == "js":
        language = "javascript"
    elif language == "py":
        language = "python"

    # Get code from --code or --file
    if args.file:
        with open(args.file, "r") as f:
            code = f.read()
    elif args.code:
        code = args.code
    else:
        parser.error("Either --code or --file is required")

    # Execute
    result = asyncio.run(execute_code(code, language))
    print(result)


if __name__ == "__main__":
    main()
