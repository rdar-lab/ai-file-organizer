#!/usr/bin/env python3
"""Entry-point wrapper for the GUI executable.

Ensures `src` is on sys.path so `ai_file_organizer.gui` can be imported as a
package (so relative imports inside `gui.py` work) and invokes its `main()`.
This file is intended to be used as the PyInstaller entry script.
"""
import os
import sys

HERE = os.path.abspath(os.path.dirname(__file__))
SRC = os.path.join(HERE, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from ai_file_organizer.gui import main


if __name__ == "__main__":
    main()
