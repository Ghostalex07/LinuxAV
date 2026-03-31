# Contributing to LinuxAV

Welcome to LinuxAV! This document provides guidelines for contributing.

## Code Style

- Follow PEP 8 guidelines
- Use type hints for all function signatures
- Use English for all code, comments, and docstrings
- Maximum line length: 100 characters

## Project Structure

```
src/linuxav/
├── domain/          # Business entities (no external dependencies)
├── adapters/       # External tool integrations (ClamAV)
├── services/       # Business logic (no UI imports)
├── app/            # Orchestration (controller, state, events)
└── ui/             # Presentation (Tkinter widgets only)
```

## Layer Rules

1. **domain**: Pure Python, no imports from other layers
2. **adapters**: External integrations, no business logic
3. **services**: Business logic, no UI imports
4. **app**: Orchestration, depends on services
5. **ui**: Presentation only, no business logic

## Pull Request Guidelines

1. **Branch**: Create a feature branch from `main`
2. **Tests**: Add tests for new functionality
3. **Documentation**: Update docs if needed
4. **Commit**: Use clear, descriptive commit messages
5. **Review**: Request review before merging

## Testing

Run tests before submitting:
```bash
PYTHONPATH=src python -m pytest tests/unit/ -v
```

## Issue Reporting

Include:
- Python version
- Linux distribution
- ClamAV version
- Steps to reproduce
- Expected vs actual behavior

## Code Review Checklist

- [ ] Type hints present and correct
- [ ] No UI logic in services/adapters
- [ ] Thread safety maintained
- [ ] Error handling implemented
- [ ] Logging added for important events
- [ ] Tests pass
- [ ] English only in code/comments

## Contact

For questions or discussions:
- Open an issue on GitHub
- Tag relevant maintainers
