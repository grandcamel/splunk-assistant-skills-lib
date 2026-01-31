# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.4] - 2025-01-31

### Added

- **Tests**: Added 14 new CLI tests for app install, mpreview, and export stream commands

### Fixed

- **Type Checking**: Fixed all 37 mypy type errors across 11 files
  - Added `from __future__ import annotations` for Python 3.9 compatibility
  - Added type casts for library returns typed as `Any`
  - Added type annotations for missing function parameters

### Changed

- **Documentation**: Updated README with new CLI command examples
  - Added `export stream` and `json_rows` format examples
  - Added `job touch` command example
  - Added `app install` command examples
  - Added `metrics mpreview` command example

## [1.1.3] - 2025-01-31

### Added

- **Export Commands**: New `export stream` command for direct streaming exports
  - Uses `/search/jobs/export` endpoint for efficient streaming
  - Results stream as they become available without creating persistent jobs
  - Best for large exports where job access isn't needed later
- **Export Commands**: Added `json_rows` output format to all export commands
  - Returns valid JSON array (unlike `json` which returns newline-delimited JSON)
  - Easier to parse with standard JSON libraries

## [1.1.2] - 2025-01-31

### Added

- **App Commands**: Full implementation of `app install` command
  - Supports .tar.gz, .tgz, and .spl package formats via multipart file upload
  - `--name` option to override app name from package
  - `--update` flag to update existing apps
  - Path traversal validation for package paths
- **Metrics Commands**: New `mpreview` command to preview raw metric data points
  - Shows individual measurements without aggregation
  - Filter by index, metric name, and filter expressions
  - Configurable result count

## [1.1.1] - 2025-01-31

### Added

- `job touch` CLI command to extend job TTL without specifying explicit value

### Fixed

- **Search Commands**: Use `max_count` instead of `count` parameter for oneshot search job creation (results were being truncated to default 10,000)
- **Security Commands**: Use `expires_on` instead of `expiresOn` parameter for token creation (expiration was being ignored)
- **Job Commands**: Use v2 endpoints (`/search/v2/jobs`) for list and delete operations instead of deprecated v1 endpoints
- **Metadata Commands**:
  - Add `count=-1` parameter to return all indexes (default was only 30)
  - Add `datatype=all` parameter to include metrics indexes
  - Fix field name `maxTotalDataSizeMB` (was `maxDataSizeMB`)
  - Add explicit type conversion for numeric fields returned as strings
- **Tag Commands**:
  - Add validation for field, value, and tag_name parameters
  - Fix double URL encoding in remove command
- **Alert Commands**:
  - Add required `alert.suppress=0` parameter to distinguish alerts from reports
  - Fix list filter to use client-side filtering (REST API doesn't support SPL-style search param)
- **Metrics Commands**:
  - Expand aggregation functions to include stdev, median, range, var, rate, earliest, latest, values, dc
  - Add explicit type conversion for numeric fields

## [1.1.0] - 2025-01-30

### Fixed

- Ensure IndexFactory returns string types for API fidelity

## [1.0.0] - 2025-01-20

### Changed
- **BREAKING**: Package renamed from `splunk-assistant-skills-lib` to `splunk-as`
- **BREAKING**: Module renamed from `splunk_assistant_skills_lib` to `splunk_as`
- All imports must be updated: `from splunk_as import ...`
- Updated dependency to `assistant-skills-lib>=1.0.0`

---

## Previous Releases (as splunk-assistant-skills-lib)

## [1.0.1] - 2025-01-20

### Changed
- Updated dependency to `assistant-skills-lib>=1.0.0`
- Simplified test fixtures to use flat config structure

## [1.0.0-pre] - 2025-01-18

### Added

- **CLI (`splunk-as`)** - Full command-line interface with 13 command groups:
  - `search` - SPL query execution (oneshot/normal/blocking/validate)
  - `job` - Search job lifecycle management
  - `export` - Data export and extraction
  - `metadata` - Index, source, sourcetype discovery
  - `lookup` - CSV and lookup file management
  - `kvstore` - App Key Value Store operations
  - `savedsearch` - Saved search and report management
  - `alert` - Alert management and monitoring
  - `app` - Application management
  - `security` - Token management and RBAC
  - `admin` - Server administration and REST API
  - `tag` - Knowledge object tagging
  - `metrics` - Real-time metrics operations
- CLI utility helpers for shared client and SID handling
- `with_time_bounds` decorator for CLI time options
- `validate_file_path` - Path traversal prevention for file operations
- `validate_path_component` - URL path injection prevention
- `quote_field_value` - Safe SPL value quoting
- `build_filter_clause` - Safe SPL filter building from dictionaries
- Sensitive field redaction in output formatters
- Security documentation in README

### Changed

- Thread-safe singleton for `ConfigManager`
- Defensive parsing with `_safe_int()` and `_safe_float()` in `JobProgress`
- URL-encode SIDs in all URL paths for defense-in-depth
- JSON payload size limits (1 MB max) to prevent DoS

### Fixed

- **SPL Injection Prevention**
  - Escape values in CSV header validation during lookup upload
  - Quote field values in tag, metrics, and metadata commands
  - Validate field names and metric names with strict patterns
- **Path Traversal Prevention**
  - Validate all file paths before open operations
  - Reject symlinks pointing outside working directory
  - Validate URL path components (app, name, collection, key)
- **URL Path Injection Prevention**
  - URL-encode SIDs in job polling, search, and export commands
  - Validate REST endpoints in admin commands
- **Defense-in-Depth**
  - Add length check before regex in `quote_field_value` (ReDoS prevention)
  - Add security warnings for token display in CLI
  - Whitelist aggregation functions and metadata types

### Security

This release includes comprehensive security hardening:
- All user input interpolated into SPL queries is escaped or validated
- File operations protected against path traversal attacks
- URL path segments validated and encoded
- Sensitive fields (passwords, tokens, keys) automatically redacted in output
- Multiple validation layers (CLI + internal functions)

## [0.2.2] - 2025-01-15

### Fixed

- Use `outputlookup` command for reliable lookup table uploads

## [0.2.1] - 2025-01-14

### Fixed

- Use multipart file upload for lookup tables
- Pin isort to 5.x for consistent formatting

## [0.2.0] - 2025-01-13

### Added

- Raw response methods in `SplunkClient`
- Lookup table upload support

## [0.1.0] - 2024-12-29

### Added

- Initial release
- `SplunkClient` - HTTP client with retry logic and dual auth support (Bearer/Basic)
- `ConfigManager` - Multi-source configuration management
- Error handling with comprehensive exception hierarchy:
  - `SplunkError`, `AuthenticationError`, `AuthorizationError`
  - `ValidationError`, `NotFoundError`, `RateLimitError`
  - `SearchQuotaError`, `JobFailedError`, `ServerError`
- `@handle_errors` decorator for CLI scripts
- Input validators:
  - `validate_spl`, `validate_sid`, `validate_time_modifier`
  - `validate_index_name`, `validate_app_name`, `validate_port`
  - `validate_url`, `validate_output_mode`
- SPL query building utilities:
  - `build_search`, `add_time_bounds`, `add_field_extraction`
  - `parse_spl_commands`, `estimate_search_complexity`
  - `optimize_spl`, `extract_fields_from_spl`
- Job polling and management:
  - `poll_job_status`, `wait_for_job`, `cancel_job`
  - `pause_job`, `unpause_job`, `finalize_job`
  - `JobState`, `JobProgress` classes
- Time utilities:
  - `parse_splunk_time`, `format_splunk_time`
  - `validate_time_range`, `get_time_range_presets`
  - `snap_to_unit`, `snap_to_weekday`
- Output formatters:
  - `format_table`, `format_json`, `format_search_results`
  - `format_job_status`, `format_metadata`
  - `print_success`, `print_warning`, `print_info`, `print_error`
- Comprehensive test suite
- GitHub Actions CI/CD with PyPI trusted publisher
