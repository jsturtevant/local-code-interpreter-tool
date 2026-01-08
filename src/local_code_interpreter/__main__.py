# Copyright (c) Microsoft. All rights reserved.

"""Entry point for running the package as a module: python -m local_code_interpreter"""

from .agent import cli

if __name__ == "__main__":
    cli()
