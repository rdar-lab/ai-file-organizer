#!/usr/bin/env python3
"""Small entry-point wrapper that imports the package-style CLI.

This wrapper ensures `ai_file_organizer.cli` is imported as a package (so
relative imports inside `cli.py` succeed) and is used as the PyInstaller
entry script instead of `src/ai_file_organizer/cli.py`.
"""
import os
import sys

# Ensure the `src` directory is on sys.path so `ai_file_organizer` imports work
HERE = os.path.abspath(os.path.dirname(__file__))
SRC = os.path.join(HERE, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from ai_file_organizer.cli import main


if __name__ == "__main__":
    main()
