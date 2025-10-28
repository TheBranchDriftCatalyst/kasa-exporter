# Contributing to Kasa Exporter

Thank you for contributing! This document provides guidelines and instructions for contributing to this project.

## Development Setup

### Prerequisites

- Python 3.12+
- Poetry
- Lefthook (optional, for git hooks)
- Docker & Docker Compose (for running services)

### Initial Setup

```bash
# Install dependencies
poetry install --with dev

# Install git hooks
lefthook install
# or
task hooks:install
```

## Code Quality

This project uses several tools to maintain code quality:

### Ruff

We use [Ruff](https://docs.astral.sh/ruff/) for fast Python linting and formatting.

```bash
# Format code
task format
# or
poetry run ruff format .

# Lint code (with auto-fix)
task lint
# or
poetry run ruff check --fix .

# Check linting (no auto-fix)
task lint:check
# or
poetry run ruff check .
```

### Testing

We use pytest for testing with comprehensive coverage.

```bash
# Run tests
task test
# or
poetry run pytest -v

# Run tests with coverage report
task test:cov
# or
poetry run pytest -v --cov=kasa_exporter --cov-report=term-missing --cov-report=html
```

### Pre-commit Checks

Git hooks are configured via Lefthook to automatically:
- Format code with ruff
- Lint code with ruff
- Validate commit messages (conventional commits)

These run automatically on `git commit` when lefthook is installed.

## Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages:

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Other changes (dependencies, etc.)

### Examples

```
feat(api): add new endpoint for device status
fix(exporter): resolve metric staleness issue
docs: update README with installation steps
test(tou): add comprehensive test suite for TOU calculator
chore(deps): update prometheus-client to v0.20.0
```

## Release Process

This project uses semantic versioning and automated releases.

### Creating a Release

```bash
# For bug fixes (0.1.0 -> 0.1.1)
task release:patch

# For new features (0.1.0 -> 0.2.0)
task release:minor

# For breaking changes (0.1.0 -> 1.0.0)
task release:major
```

The release process will:
1. Bump version in `VERSION` and `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create a git commit
4. Create a git tag
5. Prompt you to push

After pushing the tag, GitHub Actions will:
- Run tests
- Build the package
- Create a GitHub release with changelog
- Upload build artifacts

### Manual Release Steps

If you prefer manual control:

```bash
# Check current version
task release:version

# Run pre-release checks
task release:check

# Create release (this creates commit + tag locally)
task release:patch  # or minor/major

# Review the changes
git log --oneline -5
git show HEAD

# Push to trigger GitHub Actions
git push && git push --tags
```

## Development Workflow

### Running the Development Stack

```bash
# Start all services (native exporter + Docker services)
task dev

# This will start:
# - Prometheus (http://localhost:9090)
# - Grafana (http://localhost:3000) - admin/admin
# - Pushgateway (http://localhost:9091)
# - Kasa Exporter (http://localhost:8000)

# Stop all services
task dev:stop
```

### Making Changes

1. Create a feature branch
   ```bash
   git checkout -b feat/my-feature
   ```

2. Make your changes
   ```bash
   # Edit files
   # ...

   # Format and lint
   task format
   task lint

   # Run tests
   task test
   ```

3. Commit with conventional commits
   ```bash
   git add .
   git commit -m "feat(api): add new device discovery endpoint"
   ```

   The pre-commit hooks will:
   - Format your code
   - Lint your code
   - Validate your commit message

4. Push and create a PR
   ```bash
   git push origin feat/my-feature
   ```

   The pre-push hooks will:
   - Run all tests
   - Check code quality
   - Verify formatting

## Testing Guidelines

### Writing Tests

- Place tests in `tests/` subdirectories next to the code they test
- Follow the naming convention: `test_*.py`
- Use pytest fixtures for setup
- Use parametrize for testing multiple scenarios
- Aim for high coverage (>90%)

### Test Organization

```python
"""
Module docstring describing what's being tested.
"""

import pytest
from your_module import YourClass


class TestYourClass:
    """Test suite for YourClass."""

    @pytest.fixture
    def instance(self):
        """Fixture providing a test instance."""
        return YourClass()

    def test_basic_functionality(self, instance):
        """Test basic functionality."""
        assert instance.method() == expected_value

    @pytest.mark.parametrize("input,expected", [
        (1, 2),
        (2, 4),
    ])
    def test_with_parameters(self, instance, input, expected):
        """Test with multiple parameter sets."""
        assert instance.method(input) == expected
```

## CI/CD

### GitHub Actions Workflows

- **CI** (`.github/workflows/ci.yml`): Runs on every push and PR
  - Linting and formatting checks
  - Test suite execution
  - Package build verification

- **Release** (`.github/workflows/release.yml`): Runs on tag push
  - Runs full test suite
  - Builds Python package
  - Creates GitHub release
  - Uploads artifacts

## Project Structure

```
kasa-exporter/
├── .github/
│   └── workflows/        # GitHub Actions workflows
├── kasa_exporter/        # Main package
│   ├── devices/          # Device-specific code
│   ├── routines/         # Core routines (exporter, registry, etc.)
│   ├── utils/            # Utility modules
│   └── __main__.py       # Application entry point
├── etc/                  # Configuration and deployment files
├── scripts/              # Helper scripts
├── tests/                # Test files (mirror package structure)
├── lefthook.yml          # Git hooks configuration
├── pyproject.toml        # Python project metadata
├── Taskfile.yml          # Task definitions
├── Taskfile.release.yml  # Release task definitions
├── VERSION               # Current version
└── CHANGELOG.md          # Version history
```

## Getting Help

- Check existing issues on GitHub
- Read the documentation
- Ask questions in discussions

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
