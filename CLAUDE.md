# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run tests with coverage
pytest --cov=splunk_as --cov-report=xml -v

# Run a single test file
pytest tests/test_validators.py

# Run a specific test
pytest tests/test_validators.py::test_validate_sid

# Format code (always run before committing)
black src tests
isort src tests

# Type checking
mypy src --ignore-missing-imports

# CLI
splunk-as --help
splunk-as search oneshot "index=main | head 10"
```

## Architecture

This is a Python library for interacting with the Splunk REST API. The package is located at `src/splunk_as/` and exports all public APIs from `__init__.py`.

### CLI Module

- **cli/main.py**: Entry point for `splunk-as` command
- **cli/cli_utils.py**: Shared CLI utilities including:
  - `get_client_from_context(ctx)` - shared SplunkClient via Click context (preferred over direct `get_splunk_client()`)
  - `validate_sid_callback` - Click callback for SID validation on arguments
  - `extract_sid_from_response(response)` - unified SID extraction from job responses
  - `with_time_bounds` - decorator adding `--earliest`/`--latest` options
  - `handle_cli_errors` - exception handling decorator
  - `get_time_bounds`, `build_endpoint`, `output_results`
- **cli/commands/**: 13 command groups (search, job, export, metadata, lookup, kvstore, savedsearch, alert, app, security, admin, tag, metrics)

### Core Modules

- **splunk_client.py**: HTTP client (`SplunkClient`) with retry logic, dual auth (JWT Bearer or Basic), streaming support, and lookup file uploads
- **config_manager.py**: Multi-source configuration. Priority: env vars > `.claude/settings.local.json` > `.claude/settings.json` > defaults
- **error_handler.py**: Exception hierarchy (`SplunkError` base class with subclasses for 401/403/404/429/5xx) and `@handle_errors` decorator for CLI scripts

### Utility Modules

- **validators.py**: Input validation for Splunk formats (SID, SPL, time modifiers, index names) and security validators (`validate_file_path`, `validate_path_component`)
- **spl_helper.py**: SPL query building, parsing, and complexity estimation
- **job_poller.py**: Search job state polling with `JobState` enum and `JobProgress` dataclass
- **time_utils.py**: Splunk time modifier parsing and formatting

### Key Patterns

- Configuration via environment variables (SPLUNK_TOKEN, SPLUNK_SITE_URL, etc.)
- `get_splunk_client()` is the main entry point - reads config automatically
- All HTTP errors are converted to typed exceptions via `handle_splunk_error()`
- Tests use mock fixtures from `tests/conftest.py` (`mock_splunk_client`, `mock_config`)
- Always run `black` and `isort` before committing

### Test Markers

```bash
# Run only unit tests
pytest -m unit

# Skip slow tests
pytest -m "not slow"

# Run live integration tests (requires credentials)
pytest --live
```

Available markers:
- `@pytest.mark.unit` - Fast unit tests, no external calls
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.live` - Tests requiring live Splunk connection
- `@pytest.mark.destructive` - Tests that modify data

## Coding Patterns

### CLI Commands

When adding new CLI commands:
- Use `client = get_client_from_context(ctx)` instead of `get_splunk_client()` directly
- Use `callback=validate_sid_callback` on Click arguments that accept SIDs
- Use `@with_time_bounds` decorator for commands needing `--earliest`/`--latest`
- Use `extract_sid_from_response(response)` when extracting SID from job creation responses
- Mock `splunk_as.cli.cli_utils.get_splunk_client` in tests (centralized location)

### Thread Safety

- `get_config_manager()` uses double-checked locking for thread-safe singleton access
- Always use locks when implementing singleton patterns that may be accessed concurrently

### Security Considerations

#### Input Validation (validators.py)

- **Path Traversal Prevention**: Use `validate_file_path(path, "param_name")` for any user-provided file paths. Rejects `..` sequences and paths escaping current directory.
- **URL Path Injection Prevention**: Use `validate_path_component(name, "param_name")` for values interpolated into REST API URLs. Rejects `..`, `/`, `\` and URL-encodes the result.

#### SPL Injection Prevention (splunk_client.py)

- **Escape Values**: Use `SplunkClient._escape_spl_value(value)` when interpolating values into SPL queries (escapes `\` and `"`)
- **Validate Field Names**: Use `SplunkClient._validate_spl_field_name(field)` for CSV headers - enforces `[A-Za-z_][A-Za-z0-9_]*` pattern
- **Validate Lookup Names**: Use `SplunkClient._validate_lookup_name(name)` - allows only `[\w\-\.]+`

#### CLI Security Patterns

- **File Operations**: Always call `validate_file_path()` before `open()` in CLI commands
- **Endpoint Construction**: Always call `validate_path_component()` on user-provided path segments (app, name, collection, key) before interpolating into f-string endpoints
- **Admin REST Commands**: Use `_validate_rest_endpoint()` to reject `..` and require leading `/`

#### Data Handling

- **CSV Parsing**: Always use Python's `csv` module, never `split(",")` which breaks on quoted fields
- **Credentials**: Never log or expose tokens/passwords; store in `.claude/settings.local.json` (gitignored)

### Error Handling

- `JobProgress` validates `dispatchState` and uses `_safe_int()`/`_safe_float()` for defensive parsing
- All HTTP errors go through `handle_splunk_error()` which raises typed exceptions
- CLI commands use `@handle_cli_errors` decorator for user-friendly error messages
