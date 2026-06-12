# Contributing to HEAS

Thank you for your interest in contributing to HEAS. This document describes how to report issues, propose features, and submit code changes.

## Reporting issues

Use the GitHub issue tracker at https://github.com/ryZhangHason/heas/issues.  
Before opening a new issue, search existing issues to avoid duplicates.

When reporting a bug, please include:
- HEAS version (`pip show heas`)
- Python version and OS
- A minimal reproducible example
- The full error traceback

## Feature requests

Open an issue with the label `enhancement` and describe:
- The use case or research workflow the feature would support
- How you currently work around its absence

## Submitting changes

1. Fork the repository and create a branch from `main`.
2. Make your changes. Add or update tests in `tests/` as appropriate.
3. Run the test suite locally: `python -m pytest tests/`
4. Open a pull request against `main`. Describe what changed and why.

## Code style

- Follow PEP 8. Use `black` for formatting if in doubt.
- Keep public functions and classes documented with a one-line docstring minimum.
- New features should include at least one test.

## Scope

HEAS is a research-oriented framework. Contributions that add domain-specific models (ecology, economics, organizational dynamics) as examples, improve the evolutionary search interface, or improve test coverage are especially welcome.

## Questions

Open a GitHub Discussion or contact the maintainer at ruiyuzh@connect.hku.hk.
