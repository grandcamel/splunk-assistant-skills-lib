# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-18

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
- `ConfigManager` - Multi-source configuration management with profile support
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
