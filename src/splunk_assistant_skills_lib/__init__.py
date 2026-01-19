"""
Splunk Assistant Skills Library

A shared library for interacting with the Splunk REST API, providing:
    - splunk_client: HTTP client with retry logic and dual auth support
    - config_manager: Multi-source configuration management
    - error_handler: Exception hierarchy and error handling
    - validators: Input validation for Splunk-specific formats
    - formatters: Output formatting utilities
    - spl_helper: SPL query building and parsing
    - job_poller: Async job state polling
    - time_utils: Splunk time modifier handling
    - mock: Mixin-based mock client for testing

Example usage:
    from splunk_assistant_skills_lib import get_splunk_client, handle_errors

    @handle_errors
    def main():
        client = get_splunk_client()
        results = client.post('/search/jobs/oneshot', data={'search': 'index=main | head 10'})
        print(results)

For testing:
    from splunk_assistant_skills_lib.mock import MockSplunkClient

    client = MockSplunkClient()
    result = client.oneshot_search("index=main | head 10")
"""

# Batch processing (from base library)
from assistant_skills_lib.batch_processor import (
    BatchConfig,
    BatchProcessor,
    BatchProgress,
    CheckpointManager,
    generate_operation_id,
    get_recommended_batch_size,
    list_pending_checkpoints,
)

# Request Batcher (from base library)
from assistant_skills_lib.request_batcher import (
    BatchError,
    BatchResult,
    RequestBatcher,
)

# Autocomplete Cache
from .autocomplete_cache import (
    AutocompleteCache,
    get_autocomplete_cache,
)

from .config_manager import (
    DEFAULT_EARLIEST_TIME,
    DEFAULT_LATEST_TIME,
    ConfigManager,
    get_api_settings,
    get_config,
    get_config_manager,
    get_search_defaults,
    get_splunk_client,
)
from .credential_manager import (
    CredentialBackend,
    SplunkCredentialManager,
    get_credential_manager,
    get_credentials,
    is_keychain_available,
    store_credentials,
    validate_credentials,
)
from .error_handler import (
    AuthenticationError,
    AuthorizationError,
    JobFailedError,
    NotFoundError,
    RateLimitError,
    SearchQuotaError,
    ServerError,
    SplunkError,
    ValidationError,
    format_error_for_json,
    handle_errors,
    handle_splunk_error,
    parse_error_response,
    print_error,
    sanitize_error_message,
)
from .formatters import (
    Colors,
    colorize,
    export_csv,
    export_csv_string,
    format_bytes,
    format_count,
    format_duration,
    format_job_status,
    format_json,
    format_list,
    format_metadata,
    format_saved_search,
    format_search_results,
    format_splunk_time,
    format_table,
    print_info,
    print_success,
    print_warning,
    supports_color,
)
from .job_poller import (
    JobProgress,
    JobState,
    cancel_job,
    delete_job,
    finalize_job,
    get_dispatch_state,
    get_job_summary,
    list_jobs,
    pause_job,
    poll_job_status,
    set_job_ttl,
    touch_job,
    unpause_job,
    wait_for_job,
)
from .spl_helper import (
    EXPENSIVE_COMMANDS,
    GENERATING_COMMANDS,
    STREAMING_COMMANDS,
    TRANSFORMING_COMMANDS,
    add_field_extraction,
    add_head_limit,
    add_time_bounds,
    build_filter_clause,
    build_search,
    estimate_search_complexity,
    extract_fields_from_spl,
    get_search_command_info,
    optimize_spl,
    parse_spl_commands,
    quote_field_value,
    validate_spl_syntax,
)
from .splunk_client import SplunkClient
from .time_utils import (
    SNAP_UNITS,
    TIME_UNITS,
    datetime_to_time_modifier,
    epoch_to_iso,
    get_relative_time,
    get_search_time_bounds,
    get_time_range_presets,
    parse_splunk_time,
    snap_to_unit,
    snap_to_weekday,
    time_to_epoch,
    validate_time_range,
)
from .search_context import (
    SearchContext,
    clear_context_cache,
    format_context_summary,
    get_common_fields,
    get_common_sourcetypes,
    get_search_context,
    has_search_context,
    suggest_spl_prefix,
)
from .validators import (
    validate_app_name,
    validate_count,
    validate_field_list,
    validate_file_path,
    validate_index_name,
    validate_offset,
    validate_output_mode,
    validate_path_component,
    validate_port,
    validate_search_mode,
    validate_sid,
    validate_spl,
    validate_time_modifier,
    validate_url,
)

__version__ = "1.0.0"
__all__ = [
    # Version
    "__version__",
    # Batch Processing
    "BatchConfig",
    "BatchProcessor",
    "BatchProgress",
    "CheckpointManager",
    "generate_operation_id",
    "get_recommended_batch_size",
    "list_pending_checkpoints",
    # Request Batcher
    "BatchError",
    "BatchResult",
    "RequestBatcher",
    # Autocomplete Cache
    "AutocompleteCache",
    "get_autocomplete_cache",
    # Client
    "SplunkClient",
    # Config
    "ConfigManager",
    "get_config_manager",
    "get_config",
    "get_splunk_client",
    "get_api_settings",
    "get_search_defaults",
    "DEFAULT_EARLIEST_TIME",
    "DEFAULT_LATEST_TIME",
    # Credentials
    "CredentialBackend",
    "SplunkCredentialManager",
    "get_credential_manager",
    "get_credentials",
    "is_keychain_available",
    "store_credentials",
    "validate_credentials",
    # Errors
    "SplunkError",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "NotFoundError",
    "RateLimitError",
    "SearchQuotaError",
    "JobFailedError",
    "ServerError",
    "handle_errors",
    "handle_splunk_error",
    "print_error",
    "parse_error_response",
    "sanitize_error_message",
    "format_error_for_json",
    # Validators
    "validate_sid",
    "validate_spl",
    "validate_time_modifier",
    "validate_index_name",
    "validate_app_name",
    "validate_port",
    "validate_url",
    "validate_output_mode",
    "validate_count",
    "validate_offset",
    "validate_field_list",
    "validate_search_mode",
    "validate_file_path",
    "validate_path_component",
    # Formatters
    "Colors",
    "supports_color",
    "colorize",
    "format_search_results",
    "format_job_status",
    "format_metadata",
    "format_saved_search",
    "format_table",
    "format_json",
    "format_bytes",
    "format_splunk_time",
    "format_list",
    "format_duration",
    "format_count",
    "export_csv",
    "export_csv_string",
    "print_success",
    "print_warning",
    "print_info",
    # SPL Helper
    "GENERATING_COMMANDS",
    "TRANSFORMING_COMMANDS",
    "STREAMING_COMMANDS",
    "EXPENSIVE_COMMANDS",
    "build_search",
    "add_time_bounds",
    "add_field_extraction",
    "add_head_limit",
    "validate_spl_syntax",
    "parse_spl_commands",
    "estimate_search_complexity",
    "optimize_spl",
    "get_search_command_info",
    "extract_fields_from_spl",
    "quote_field_value",
    "build_filter_clause",
    # Job Poller
    "JobState",
    "JobProgress",
    "get_dispatch_state",
    "poll_job_status",
    "wait_for_job",
    "cancel_job",
    "pause_job",
    "unpause_job",
    "finalize_job",
    "set_job_ttl",
    "touch_job",
    "get_job_summary",
    "list_jobs",
    "delete_job",
    # Time Utils
    "TIME_UNITS",
    "SNAP_UNITS",
    "parse_splunk_time",
    "snap_to_unit",
    "snap_to_weekday",
    "datetime_to_time_modifier",
    "validate_time_range",
    "get_relative_time",
    "get_time_range_presets",
    "time_to_epoch",
    "epoch_to_iso",
    "get_search_time_bounds",
    # Search Context
    "SearchContext",
    "get_search_context",
    "clear_context_cache",
    "has_search_context",
    "get_common_sourcetypes",
    "get_common_fields",
    "suggest_spl_prefix",
    "format_context_summary",
]
