#!/usr/bin/env python3
"""Minimal runner for AI File Organizer that delegates entirely to the CLI.

The CLI now reads configuration from files, CLI args, or environment variables
(and supports continuous mode). The docker runner should do nothing fancy — it
just invokes the CLI entrypoint in-process and lets the CLI control behavior.
"""

import sys
import logging
import importlib

# Ensure package path is available when running inside container image
sys.path.insert(0, '/app/src')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    try:
        af_cli = importlib.import_module('ai_file_organizer.cli')
    except Exception as e:
        logger.exception(f'Failed to import ai_file_organizer.cli: {e}')
        sys.exit(1)

    try:
        af_cli.main()
    except SystemExit as se:
        # Allow the CLI's intentional exits to propagate as the process exit code
        code = se.code if isinstance(se.code, int) else 1
        logger.info(f'CLI exited with SystemExit({se.code})')
        raise
    except Exception as e:
        logger.exception(f'Unhandled exception in CLI: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
