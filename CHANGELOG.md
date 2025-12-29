# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
