# Splunk AS

[![PyPI version](https://badge.fury.io/py/splunk-as.svg)](https://badge.fury.io/py/splunk-as)
[![Python Versions](https://img.shields.io/pypi/pyversions/splunk-as.svg)](https://pypi.org/project/splunk-as/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/grandcamel/splunk-assistant-skills-lib/actions/workflows/ci.yml/badge.svg)](https://github.com/grandcamel/splunk-assistant-skills-lib/actions/workflows/ci.yml)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

A Python library for interacting with the Splunk REST API. Provides HTTP client, configuration management, error handling, validators, and utilities for building Splunk automation tools.

## Installation

```bash
pip install splunk-as
```

## Quick Start

```python
from splunk_as import get_splunk_client, handle_errors, validate_spl

@handle_errors
def main():
    # Get a configured client (reads from environment or config file)
    client = get_splunk_client()

    # Validate and execute a search
    spl = validate_spl("index=main | head 10")
    results = client.post(
        '/search/jobs/oneshot',
        data={'search': spl, 'output_mode': 'json'}
    )
    print(results)

if __name__ == '__main__':
    main()
```

## CLI

The library includes a full command-line interface (`splunk-as`) for interacting with Splunk:

```bash
# Get help
splunk-as --help
splunk-as search --help

# Search commands
splunk-as search oneshot "index=main | head 10"
splunk-as search oneshot "index=main | stats count by host" -o json
splunk-as search oneshot "error" -e "-1h" -l "now" --fields host,message
splunk-as search normal "index=main | stats count" --wait --timeout 120
splunk-as search blocking "index=main | head 100"
splunk-as search validate "index=main | stats count" --suggestions

# Job management
splunk-as job list
splunk-as job list --state running
splunk-as job status 1703779200.12345
splunk-as job cancel 1703779200.12345
splunk-as job results 1703779200.12345 --count 100 -o csv

# Metadata discovery
splunk-as metadata indexes
splunk-as metadata sourcetypes --index main
splunk-as metadata hosts --index main --earliest -24h
splunk-as metadata sources --sourcetype syslog

# Export data
splunk-as export results "index=main | stats count by host" -o results.csv
splunk-as export results "index=main" -o data.json --format json
splunk-as export job 1703779200.12345 -o results.csv
splunk-as export estimate "index=main | head 10000"

# Lookups and KV Store
splunk-as lookup list
splunk-as lookup get my_lookup.csv
splunk-as lookup upload data.csv --name my_lookup
splunk-as kvstore list --app search
splunk-as kvstore get mycollection --key record_id

# Saved searches and alerts
splunk-as savedsearch list --app search
splunk-as savedsearch run "My Saved Search"
splunk-as alert list
splunk-as alert history "My Alert"

# Administration
splunk-as admin info
splunk-as admin health
splunk-as admin rest GET /server/settings
splunk-as security whoami
splunk-as security capabilities
splunk-as app list
```

### Available Command Groups

| Group | Description |
|-------|-------------|
| `search` | SPL query execution (oneshot/normal/blocking) |
| `job` | Search job lifecycle management |
| `export` | Data export and extraction |
| `metadata` | Index, source, sourcetype discovery |
| `lookup` | CSV and lookup file management |
| `kvstore` | App Key Value Store operations |
| `savedsearch` | Saved search and report management |
| `alert` | Alert management and monitoring |
| `app` | Application management |
| `security` | Token management and RBAC |
| `admin` | Server administration and REST API |
| `tag` | Knowledge object tagging |
| `metrics` | Real-time metrics operations |

## Features

### HTTP Client (`SplunkClient`)

- Dual authentication: JWT Bearer token (preferred) or Basic Auth
- Automatic retry with exponential backoff on 429/5xx errors
- Configurable timeouts for short and long-running operations
- SSL verification with option to disable for self-signed certs
- Streaming support for large result sets

```python
from splunk_as import SplunkClient

client = SplunkClient(
    base_url="https://splunk.example.com",
    token="your-jwt-token",
    port=8089,
    verify_ssl=True
)

# GET request
info = client.get("/server/info")

# POST request
job = client.post("/search/jobs", data={"search": "index=main | head 10"})

# Stream results
for chunk in client.stream_results(f"/search/jobs/{sid}/results"):
    process(chunk)
```

### Configuration Management

Multi-source configuration:
1. Environment variables (highest priority)
2. `.claude/settings.local.json` (personal, gitignored)
3. `.claude/settings.json` (team defaults)
4. Built-in defaults (lowest priority)

```python
from splunk_as import get_splunk_client, get_config

# Get a configured client (reads from env vars or config files)
client = get_splunk_client()

# Get configuration dictionary
config = get_config()
```

**Environment Variables:**
- `SPLUNK_TOKEN` - JWT Bearer token (preferred)
- `SPLUNK_USERNAME` / `SPLUNK_PASSWORD` - Basic Auth credentials
- `SPLUNK_SITE_URL` - Splunk host URL
- `SPLUNK_MANAGEMENT_PORT` - Management port (default: 8089)
- `SPLUNK_VERIFY_SSL` - SSL verification (true/false)
- `SPLUNK_DEFAULT_APP` - Default app context
- `SPLUNK_DEFAULT_INDEX` - Default search index

### Error Handling

Comprehensive exception hierarchy and `@handle_errors` decorator for CLI scripts:

```python
from splunk_as import (
    handle_errors,
    SplunkError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
)

@handle_errors
def main():
    # Exceptions are caught and printed nicely
    client = get_splunk_client()
    client.get("/nonexistent")  # Raises NotFoundError
```

**Exception Hierarchy:**
- `SplunkError` (base)
  - `AuthenticationError` (401)
  - `AuthorizationError` (403)
  - `ValidationError` (400)
  - `NotFoundError` (404)
  - `RateLimitError` (429)
  - `SearchQuotaError` (503)
  - `JobFailedError`
  - `ServerError` (5xx)

### Input Validators

Validate Splunk-specific formats:

```python
from splunk_as import (
    validate_spl,
    validate_sid,
    validate_time_modifier,
    validate_index_name,
)

# Validates SPL syntax (balanced parens, valid pipes, etc.)
spl = validate_spl("index=main | stats count by host")

# Validates search job ID format
sid = validate_sid("1703779200.12345")

# Validates time modifier format
time = validate_time_modifier("-1h@h")

# Validates index name
index = validate_index_name("main")
```

### SPL Query Building

Build and optimize SPL queries:

```python
from splunk_as import (
    build_search,
    add_time_bounds,
    estimate_search_complexity,
    parse_spl_commands,
)

# Build search with common options
spl = build_search(
    "error",
    index="main",
    earliest_time="-1h",
    latest_time="now",
    fields=["host", "message"],
    head=100
)

# Estimate complexity
complexity = estimate_search_complexity(spl)  # 'simple', 'medium', 'complex'

# Parse into commands
commands = parse_spl_commands(spl)  # [('search', '...'), ('fields', '...')]
```

### Job Polling

Monitor and manage search jobs:

```python
from splunk_as import (
    poll_job_status,
    cancel_job,
    pause_job,
    JobState,
)

# Poll until completion
progress = poll_job_status(client, sid, timeout=300)
print(f"Results: {progress.result_count}")

# Cancel a job
cancel_job(client, sid)

# Check job state
if progress.state == JobState.DONE:
    print("Job completed successfully")
```

### Time Utilities

Work with Splunk time modifiers:

```python
from splunk_as import (
    parse_splunk_time,
    datetime_to_time_modifier,
    validate_time_range,
    get_time_range_presets,
)

# Parse time modifier to datetime
dt = parse_splunk_time("-1h")

# Convert datetime to Splunk time modifier
time_str = datetime_to_time_modifier(dt, format_type="epoch")

# Validate time range
is_valid, error = validate_time_range("-1h", "now")

# Get common presets
presets = get_time_range_presets()
# {'last_hour': ('-1h', 'now'), 'today': ('@d', 'now'), ...}
```

### Output Formatters

Format data for display:

```python
from splunk_as import (
    format_table,
    format_json,
    format_search_results,
    export_csv,
    export_csv_string,
    print_success,
    print_warning,
)

# Format as table
print(format_table(results, columns=["host", "count"]))

# Format search results
print(format_search_results(response, output_format="table"))

# Export to CSV file
export_csv(results, "output.csv", columns=["host", "count"])

# Export to CSV string
csv_data = export_csv_string(results, columns=["host", "count"])

# Colored output
print_success("Operation completed")
print_warning("Check your configuration")
```

### Security Validators

Prevent path traversal and injection attacks:

```python
from splunk_as import (
    validate_file_path,
    validate_path_component,
    quote_field_value,
    build_filter_clause,
)

# Validate file paths (prevents directory traversal)
safe_path = validate_file_path("exports/data.csv", "output_file")
# Raises ValidationError for "../etc/passwd" or absolute paths outside CWD

# Validate URL path components (prevents URL injection)
safe_name = validate_path_component("my-app", "app_name")
# Raises ValidationError for "../admin" or paths with slashes

# Quote values for safe SPL interpolation
safe_value = quote_field_value("user input with spaces")
# Returns: '"user input with spaces"'

# Build filter clauses safely
filters = build_filter_clause({
    "host": "server1",
    "status": ["200", "201"],  # OR clause
    "user": None,  # NOT user=*
})
# Returns: 'host="server1" (status="200" OR status="201") NOT user=*'
```

## Configuration File Example

Create `.claude/settings.local.json`:

```json
{
  "splunk": {
    "url": "https://splunk.company.com",
    "port": 8089,
    "token": "your-jwt-token",
    "auth_method": "bearer",
    "verify_ssl": true,
    "default_app": "search",
    "default_index": "main"
  }
}
```

Or use Basic Auth:

```json
{
  "splunk": {
    "url": "https://splunk.company.com",
    "port": 8089,
    "username": "admin",
    "password": "changeme",
    "auth_method": "basic",
    "verify_ssl": false
  }
}
```

## API Reference

### Modules

| Module | Description |
|--------|-------------|
| `cli` | Command-line interface (`splunk-as`) |
| `splunk_client` | HTTP client with retry logic and dual auth |
| `config_manager` | Multi-source configuration management |
| `error_handler` | Exception hierarchy and error handling |
| `validators` | Input validation for Splunk formats |
| `formatters` | Output formatting utilities |
| `spl_helper` | SPL query building and parsing |
| `job_poller` | Job state polling and management |
| `time_utils` | Splunk time modifier handling |

## Security

This library implements defense-in-depth security practices to protect against common vulnerabilities.

### SPL Injection Prevention

All user input interpolated into SPL queries is properly escaped or validated:

- **`quote_field_value()`** - Escapes special characters and quotes values
- **`validate_spl()`** - Validates SPL syntax before execution
- **`build_filter_clause()`** - Safely builds filter expressions from dictionaries

### Path Traversal Prevention

File and URL path operations are protected against traversal attacks:

- **`validate_file_path()`** - Rejects `..` patterns, validates symlinks, ensures paths don't escape working directory
- **`validate_path_component()`** - Prevents path separators and traversal patterns in URL segments

### Input Validation

All Splunk-specific formats are validated before use:

- SIDs validated against expected format patterns
- Time modifiers validated for correct Splunk syntax
- Index and app names validated against allowed character sets
- Port numbers and URLs validated for correctness

### Sensitive Data Protection

Output formatters automatically redact sensitive fields:

- Passwords, tokens, API keys, secrets
- Authentication and credential fields
- Session keys and bearer tokens

Fields containing these patterns are replaced with `[REDACTED]` in output.

### Defense-in-Depth

Multiple validation layers ensure security even if one layer is bypassed:

- Input validated at CLI argument level
- Re-validated in internal functions before use
- URL path components are URL-encoded even after validation
- JSON payloads have size limits to prevent DoS

## Development

```bash
# Clone the repository
git clone https://github.com/grandcamel/splunk-assistant-skills-lib.git
cd splunk-assistant-skills-lib

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src tests
isort src tests

# Type checking
mypy src
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Related Projects

- [Splunk Assistant Skills](https://github.com/grandcamel/Splunk-Assistant-Skills) - Claude Code plugin for Splunk automation
