#!/usr/bin/env python3
"""
Configuration Manager for Splunk Skills

Provides configuration management from environment variables and config files.
Configuration priority (highest to lowest):
    1. Environment variables
    2. .claude/settings.local.json (personal, gitignored)
    3. .claude/settings.json (team defaults)
    4. Built-in defaults

Environment Variables:
    SPLUNK_TOKEN - JWT Bearer token (preferred auth)
    SPLUNK_USERNAME - Username for Basic Auth
    SPLUNK_PASSWORD - Password for Basic Auth
    SPLUNK_SITE_URL - Splunk host URL
    SPLUNK_MANAGEMENT_PORT - Management port (default: 8089)
    SPLUNK_VERIFY_SSL - SSL verification (true/false)
    SPLUNK_DEFAULT_APP - Default app context
    SPLUNK_DEFAULT_INDEX - Default search index
"""

from typing import Any, Dict, Optional

from assistant_skills_lib.config_manager import BaseConfigManager

from .error_handler import ValidationError
from .splunk_client import SplunkClient

# Default time bounds for searches
DEFAULT_EARLIEST_TIME = "-24h"
DEFAULT_LATEST_TIME = "now"


class ConfigManager(BaseConfigManager):
    """Manages Splunk configuration from environment variables and config files."""

    def __init__(self):
        """Initialize the configuration manager."""
        super().__init__(profile=None)

    def get_service_name(self) -> str:
        """Returns the name of the service, which is 'splunk'."""
        return "splunk"

    def get_default_config(self) -> Dict[str, Any]:
        """Returns the default configuration dictionary for Splunk."""
        return {
            "url": "",
            "port": 8089,
            "auth_method": "bearer",
            "default_app": "search",
            "default_index": "main",
            "verify_ssl": True,
            "deployment_type": "on-prem",
            "api": {
                "timeout": 30,
                "search_timeout": 300,
                "max_retries": 3,
                "retry_backoff": 2.0,
                "default_output_mode": "json",
                "prefer_v2_api": True,
            },
            "search_defaults": {
                "earliest_time": DEFAULT_EARLIEST_TIME,
                "latest_time": DEFAULT_LATEST_TIME,
                "max_count": 50000,
                "status_buckets": 300,
                "auto_cancel": 300,
            },
        }

    def get_splunk_config(self) -> Dict[str, Any]:
        """
        Get Splunk configuration merged with environment variable overrides.

        Returns:
            Configuration dictionary
        """
        # Start with defaults
        defaults = self.get_default_config()

        # Get config from files (flat structure under "splunk" key)
        file_config = self.config.get(self.service_name, {})

        # Merge file config over defaults
        merged = self._deep_merge(defaults, file_config)

        # Apply environment variable overrides (highest priority)
        env_overrides = self._get_env_overrides()
        final_config = self._deep_merge(merged, env_overrides)

        return final_config

    def _get_env_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables."""
        overrides: Dict[str, Any] = {}

        if url := self.get_credential_from_env("SITE_URL"):
            overrides["url"] = url
        if port := self.get_credential_from_env("MANAGEMENT_PORT"):
            try:
                overrides["port"] = int(port)
            except ValueError:
                pass
        if token := self.get_credential_from_env("TOKEN"):
            overrides["token"] = token
            overrides["auth_method"] = "bearer"
        if username := self.get_credential_from_env("USERNAME"):
            overrides["username"] = username
        if password := self.get_credential_from_env("PASSWORD"):
            overrides["password"] = password
            if not overrides.get("token"):
                overrides["auth_method"] = "basic"
        if verify_ssl := self.get_credential_from_env("VERIFY_SSL"):
            overrides["verify_ssl"] = verify_ssl.lower() in ("true", "1", "yes")
        if default_app := self.get_credential_from_env("DEFAULT_APP"):
            overrides["default_app"] = default_app
        if default_index := self.get_credential_from_env("DEFAULT_INDEX"):
            overrides["default_index"] = default_index

        return overrides

    def get_client_kwargs(self) -> Dict[str, Any]:
        """Get keyword arguments for SplunkClient initialization."""
        config = self.get_splunk_config()
        api_config = config.get("api", {})

        kwargs: Dict[str, Any] = {
            "base_url": config.get("url", ""),
            "port": config.get("port", 8089),
            "timeout": api_config.get("timeout", 30),
            "verify_ssl": config.get("verify_ssl", True),
            "max_retries": api_config.get("max_retries", 3),
            "retry_backoff": api_config.get("retry_backoff", 2.0),
        }

        auth_method = config.get("auth_method", "bearer")
        if auth_method == "bearer" and config.get("token"):
            kwargs["token"] = config["token"]
        elif config.get("username") and config.get("password"):
            kwargs["username"] = config["username"]
            kwargs["password"] = config["password"]
        elif config.get("token"):
            kwargs["token"] = config["token"]

        return kwargs

    def validate_config(self) -> list:
        """Validate configuration and return list of issues."""
        errors = []
        config = self.get_splunk_config()

        if not config.get("url"):
            errors.append("Missing Splunk URL. Set SPLUNK_SITE_URL or configure in settings.json")

        auth_method = config.get("auth_method", "bearer")
        if auth_method == "bearer" and not config.get("token"):
            errors.append("Missing Splunk token. Set SPLUNK_TOKEN or configure in settings.local.json")
        elif auth_method != "bearer" and not (config.get("username") and config.get("password")):
            errors.append(
                "Missing Splunk username/password for basic auth. "
                "Set SPLUNK_USERNAME and SPLUNK_PASSWORD or configure in settings.local.json"
            )

        return errors


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create global ConfigManager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager.get_instance()
    return _config_manager


def get_config() -> Dict[str, Any]:
    """Get Splunk configuration."""
    return get_config_manager().get_splunk_config()


def get_splunk_client() -> SplunkClient:
    """Create SplunkClient instance from configuration."""
    manager = get_config_manager()
    errors = manager.validate_config()
    if errors:
        raise ValidationError("\n".join(errors))
    kwargs = manager.get_client_kwargs()
    return SplunkClient(**kwargs)


def get_search_defaults() -> Dict[str, Any]:
    """Get search default settings."""
    config = get_config()
    return config.get("search_defaults", {})


def get_api_settings() -> Dict[str, Any]:
    """Get API settings."""
    config = get_config()
    return config.get("api", {})
