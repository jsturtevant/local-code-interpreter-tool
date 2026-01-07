# Copyright (c) Microsoft. All rights reserved.

"""Entry point for running the package as a module: python -m local_code_interpreter"""

import asyncio
import sys

from .agent import main, run_devui, _configure_logging


if __name__ == "__main__":
    # Handle --devui before entering async context (serve() runs its own event loop)
    if "--devui" in sys.argv:
        verbose = "--verbose" in sys.argv or "-v" in sys.argv
        environment = "hyperlight" if "--hyperlight" in sys.argv else "python"
        port = 8090
        host = "127.0.0.1"
        auto_open = "--no-browser" not in sys.argv
        for arg in sys.argv:
            if arg.startswith("--port="):
                port = int(arg.split("=")[1])
            if arg.startswith("--host="):
                host = arg.split("=")[1]
        _configure_logging(verbose=verbose)
        run_devui(environment=environment, port=port, host=host, auto_open=auto_open)
    else:
        asyncio.run(main())
