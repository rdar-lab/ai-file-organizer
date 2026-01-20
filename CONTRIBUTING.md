# Contributing to AI File Organizer

Thank you for your interest in contributing to AI File Organizer! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/ai-file-organizer.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Run tests: `pytest tests/`
6. Commit your changes: `git commit -am 'Add some feature'`
7. Push to the branch: `git push origin feature/your-feature-name`
8. Submit a pull request

## Development Setup

```bash
# Clone the repository
git clone https://github.com/rdar-lab/ai-file-organizer.git
cd ai-file-organizer

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov flake8 black isort

# Install in development mode
pip install -e .
```

## Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=ai_file_organizer --cov-report=term --cov-report=html

# Run specific test file
pytest tests/test_ai_facade.py
```

## Code Style

We use the following tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting

Before submitting a PR, please run:

```bash
# Format code
black src/ai_file_organizer tests/

# Sort imports
isort src/ai_file_organizer tests/

# Lint code
flake8 src/ai_file_organizer tests/
```

## Pull Request Guidelines

- Ensure all tests pass
- Add tests for new features
- Update documentation as needed
- Keep PRs focused on a single feature or bug fix
- Write clear commit messages
- Reference related issues in your PR description

## Reporting Bugs

Please use GitHub Issues to report bugs. Include:

- Description of the bug
- Steps to reproduce
- Expected behavior
- Actual behavior
- Python version and OS
- Relevant logs or error messages

## Feature Requests

We welcome feature requests! Please use GitHub Issues and include:

- Clear description of the feature
- Use case and motivation
- Possible implementation approach (optional)

## Questions?

Feel free to open a GitHub Issue for questions or discussions.
