# Contributing

Thanks for helping improve the local-first Dictionary API.

## Setup

Use Python 3.10 or newer. Create a virtual environment and install the development extras:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Before opening a pull request

Run the network-free test suite and quality checks:

```sh
python -m pytest
python -m ruff check app tests
python -m ruff format --check app tests
python -m mypy app
```

Mock provider HTTP calls in default tests. Live integration tests must be opt-in and must not be required for CI. Add tests for failure paths and malformed provider data when changing adapters.

## Design expectations

- Keep the application runnable locally without a hosted backend, paid service, or mandatory API key.
- Keep provider-specific HTTP and parsing in adapters that satisfy the provider protocols.
- Preserve existing response fields. Use `/api/v3` for future incompatible API changes.
- Never invent dictionary data. Mark optional data missing when a source does not provide it.
- Do not add a word list or dictionary corpus unless its redistribution license is verified and documented.
- Keep large NLP libraries and datasets optional.
- Add configuration through environment variables and never commit secrets.

## Pull requests

Describe the behavior change, configuration impact, and tests run. Update the README or versioned API docs when a public route or response changes.
