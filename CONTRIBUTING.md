# Contributing to MCP Document Fetcher

Thank you for your interest in contributing to MCP Document Fetcher! This document provides guidelines and instructions for contributing.

## Development Setup

1. Fork and clone the repository:
```bash
git clone https://github.com/your-username/mcps.git
cd mcps
```

2. Set up the development environment:
```bash
uv venv
uv venv activate
uv pip install -r requirements.txt
```

3. Set up pre-commit hooks:
```bash
pre-commit install
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function arguments and return values
- Write comprehensive docstrings in Google style
- Keep functions focused and single-purpose
- Add comments for complex logic

## Making Changes

1. Create a new branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes:
- Write clear, documented code
- Add tests for new functionality
- Update documentation as needed

3. Test your changes:
```bash
pytest tests/
```

4. Commit your changes:
```bash
git add .
git commit -m "feat: description of your changes"
```

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test changes
- `refactor:` for code refactoring
- `style:` for formatting changes
- `chore:` for maintenance tasks

## Pull Request Process

1. Update your fork:
```bash
git remote add upstream https://github.com/original/mcps.git
git fetch upstream
git rebase upstream/main
```

2. Push your changes:
```bash
git push origin feature/your-feature-name
```

3. Create a Pull Request:
- Use a clear title and description
- Reference any related issues
- Ensure all tests pass
- Request review from maintainers

## Code Review

- Be respectful and constructive
- Address all review comments
- Make requested changes in new commits
- Squash commits before merging

## License

By contributing, you agree that your contributions will be licensed under the project's license. 