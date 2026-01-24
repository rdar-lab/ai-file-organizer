#!/bin/bash
# Run static code analysis (same as .github/workflows/static-scan.yml)
set -e

# Ensure Python 3.11+ is available (optional: check version)

# Upgrade pip and install dependencies
python3 -m pip install --upgrade pip
pip install flake8 black isort

# Run flake8
flake8 src --max-complexity=20 --max-line-length=200 --ignore=W293,W504

# Check black formatting
black --line-length=200  --no-cache  src

# Check import sorting
isort -n src
