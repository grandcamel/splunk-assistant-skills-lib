# Splunk Assistant Skills Library

[![PyPI version](https://badge.fury.io/py/splunk-assistant-skills-lib.svg)](https://badge.fury.io/py/splunk-assistant-skills-lib)
[![Python Versions](https://img.shields.io/pypi/pyversions/splunk-assistant-skills-lib.svg)](https://pypi.org/project/splunk-assistant-skills-lib/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A shared Python library for interacting with the Splunk REST API. Provides HTTP client, configuration management, error handling, validators, and utilities for building Splunk automation tools.

## Installation

```bash
pip install splunk-assistant-skills-lib
```

## Quick Start

```python
from splunk_assistant_skills_lib import get_splunk_client, handle_errors, validate_spl

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

## Features

### HTTP Client (`SplunkClient`)

- Dual authentication: JWT Bearer token (preferred) or Basic Auth
- Automatic retry with exponential backoff on 429/5xx errors
- Configurable timeouts for short and long-running operations
- SSL verification with option to disable for self-signed certs
- Streaming support for large result sets

```python
from splunk_assistant_skills_lib import SplunkClient

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

Multi-source configuration with profile support:
1. Environment variables (highest priority)
2. `.claude/settings.local.json` (personal, gitignored)
3. `.claude/settings.json` (team defaults)
4. Built-in defaults (lowest priority)

```python
from splunk_assistant_skills_lib import get_splunk_client, get_config

# Use default profile
client = get_splunk_client()

# Use specific profile
client = get_splunk_client(profile="production")

# Get configuration
config = get_config(profile="production")
```

**Environment Variables:**
- `SPLUNK_TOKEN` - JWT Bearer token
- `SPLUNK_USERNAME` / `SPLUNK_PASSWORD` - Basic Auth credentials
- `SPLUNK_SITE_URL` - Splunk host URL
- `SPLUNK_MANAGEMENT_PORT` - Management port (default: 8089)
- `SPLUNK_PROFILE` - Profile name to use
- `SPLUNK_VERIFY_SSL` - SSL verification (true/false)

### Error Handling

Comprehensive exception hierarchy and `@handle_errors` decorator for CLI scripts:

```python
from splunk_assistant_skills_lib import (
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
from splunk_assistant_skills_lib import (
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
from splunk_assistant_skills_lib import (
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
from splunk_assistant_skills_lib import (
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
from splunk_assistant_skills_lib import (
    parse_splunk_time,
    format_splunk_time,
    validate_time_range,
    get_time_range_presets,
)

# Parse time modifier to datetime
dt = parse_splunk_time("-1h")

# Format datetime as Splunk time
time_str = format_splunk_time(dt, format_type="epoch")

# Validate time range
is_valid, error = validate_time_range("-1h", "now")

# Get common presets
presets = get_time_range_presets()
# {'last_hour': ('-1h', 'now'), 'today': ('@d', 'now'), ...}
```

### Output Formatters

Format data for display:

```python
from splunk_assistant_skills_lib import (
    format_table,
    format_json,
    format_search_results,
    print_success,
    print_warning,
)

# Format as table
print(format_table(results, columns=["host", "count"]))

# Format search results
print(format_search_results(response, output_format="table"))

# Colored output
print_success("Operation completed")
print_warning("Check your configuration")
```

## Configuration File Example

Create `.claude/settings.local.json`:

```json
{
  "splunk": {
    "default_profile": "production",
    "profiles": {
      "production": {
        "url": "https://splunk.company.com",
        "port": 8089,
        "token": "your-jwt-token",
        "auth_method": "bearer",
        "verify_ssl": true
      },
      "development": {
        "url": "https://splunk-dev.company.com",
        "port": 8089,
        "username": "admin",
        "password": "changeme",
        "auth_method": "basic",
        "verify_ssl": false
      }
    }
  }
}
```

## API Reference

### Modules

| Module | Description |
|--------|-------------|
| `splunk_client` | HTTP client with retry logic and dual auth |
| `config_manager` | Multi-source configuration management |
| `error_handler` | Exception hierarchy and error handling |
| `validators` | Input validation for Splunk formats |
| `formatters` | Output formatting utilities |
| `spl_helper` | SPL query building and parsing |
| `job_poller` | Job state polling and management |
| `time_utils` | Splunk time modifier handling |

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
