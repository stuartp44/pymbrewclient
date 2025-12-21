# Contributing to pymbrewclient

Thank you for your interest in contributing to pymbrewclient!

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- pip

### Setting Up Development Environment

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/stuartp44/pymbrewclient.git
   cd pymbrewclient
   ```

2. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks** (recommended)
   ```bash
   pre-commit install
   ```

## Development Workflow

### Making Changes

1. **Create a new branch**
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**
   - Write clean, readable code
   - Follow the existing code style
   - Add/update tests as needed
   - Update documentation if necessary

3. **Run tests**
   ```bash
   pytest
   ```

4. **Run linting**
   ```bash
   ruff check .
   black --check .
   ```

5. **Fix formatting issues**
   ```bash
   black .
   ruff check --fix .
   ```

### Commit Messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/). Please follow these guidelines:

- **feat**: New features
- **fix**: Bug fixes
- **docs**: Documentation changes
- **test**: Test updates
- **refactor**: Code refactoring
- **perf**: Performance improvements
- **build**: Build system changes
- **ci**: CI/CD changes

**Examples:**
```bash
git commit -m "feat(cli): add --verbose flag for detailed output"
git commit -m "fix(client): handle connection timeout errors"
git commit -m "docs: update installation instructions"
```

See [.github/COMMIT_CONVENTION.md](.github/COMMIT_CONVENTION.md) for detailed guidelines.

### Submitting Pull Requests

1. **Push your changes**
   ```bash
   git push origin your-branch-name
   ```

2. **Open a Pull Request**
   - Go to GitHub and create a pull request
   - Fill out the PR template
   - Link any related issues
   - Ensure all CI checks pass

3. **Code Review**
   - A maintainer will review your PR
   - Address any feedback
   - Once approved, your PR will be merged!

## Code Style

### Python Style Guide

- Follow PEP 8
- Use type hints where appropriate
- Maximum line length: 120 characters
- Use meaningful variable and function names

### Testing

- Write tests for new features
- Maintain or improve code coverage
- Use descriptive test names
- Test edge cases and error conditions

**Running specific tests:**
```bash
pytest tests/test_client.py
pytest tests/test_client.py::test_specific_function
pytest -k "test_pattern"
```

**Check coverage:**
```bash
pytest --cov=pymbrewclient --cov-report=html
```

### Documentation

- Update README.md if adding user-facing features
- Add docstrings to new functions and classes
- Use Google-style docstrings

**Example:**
```python
def fetch_data(endpoint: str, timeout: int = 30) -> dict:
    """Fetch data from the API endpoint.
    
    Args:
        endpoint: The API endpoint to query.
        timeout: Request timeout in seconds. Defaults to 30.
        
    Returns:
        The JSON response as a dictionary.
        
    Raises:
        RequestException: If the request fails.
    """
    pass
```

## Project Structure

```
pymbrewclient/
├── src/
│   └── pymbrewclient/
│       ├── __init__.py
│       ├── cli.py          # CLI interface
│       ├── client.py       # Main client
│       └── rest/
│           ├── client.py   # REST client
│           └── models.py   # Data models
├── tests/
│   └── test_client.py      # Tests
├── pyproject.toml          # Project configuration
└── README.md
```

## Release Process

This project uses automated semantic versioning:

- Commits are analyzed to determine version bumps
- Changelog is automatically generated
- Releases are published to PyPI automatically
- GitHub releases are created with release notes

**Version bumps:**
- `feat:` → minor version (0.X.0)
- `fix:`, `perf:`, `refactor:` → patch version (0.0.X)
- `feat!:` or `BREAKING CHANGE:` → major version (X.0.0)

## Getting Help

- Read the [documentation](README.md)
- Open a [discussion](https://github.com/stuartp44/pymbrewclient/discussions)
- Report bugs via [issues](https://github.com/stuartp44/pymbrewclient/issues)

## Code of Conduct

Please be respectful and constructive in all interactions. We're all here to learn and improve the project together.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing!
