"""Tests for config_manager module."""

import os
import threading
from unittest.mock import MagicMock, patch

import pytest

from splunk_as.config_manager import (
    DEFAULT_EARLIEST_TIME,
    DEFAULT_LATEST_TIME,
    ConfigManager,
    get_api_settings,
    get_config,
    get_config_manager,
    get_search_defaults,
    get_splunk_client,
)
from splunk_as.error_handler import ValidationError


class TestConfigManagerConstants:
    """Tests for config_manager constants."""

    def test_default_earliest_time(self):
        """Test DEFAULT_EARLIEST_TIME constant."""
        assert DEFAULT_EARLIEST_TIME == "-24h"

    def test_default_latest_time(self):
        """Test DEFAULT_LATEST_TIME constant."""
        assert DEFAULT_LATEST_TIME == "now"


class TestConfigManager:
    """Tests for ConfigManager class."""

    @patch.object(ConfigManager, "__init__", lambda x: None)
    def test_get_service_name(self):
        """Test get_service_name returns 'splunk'."""
        manager = ConfigManager.__new__(ConfigManager)
        assert manager.get_service_name() == "splunk"

    @patch.object(ConfigManager, "__init__", lambda x: None)
    def test_get_default_config_structure(self):
        """Test get_default_config returns expected structure."""
        manager = ConfigManager.__new__(ConfigManager)
        defaults = manager.get_default_config()

        # Check top-level keys
        assert "url" in defaults
        assert "port" in defaults
        assert "auth_method" in defaults
        assert "default_app" in defaults
        assert "default_index" in defaults
        assert "verify_ssl" in defaults
        assert "deployment_type" in defaults
        assert "api" in defaults
        assert "search_defaults" in defaults

    @patch.object(ConfigManager, "__init__", lambda x: None)
    def test_get_default_config_values(self):
        """Test get_default_config returns expected values."""
        manager = ConfigManager.__new__(ConfigManager)
        defaults = manager.get_default_config()

        assert defaults["port"] == 8089
        assert defaults["auth_method"] == "bearer"
        assert defaults["default_app"] == "search"
        assert defaults["default_index"] == "main"
        assert defaults["verify_ssl"] is True
        assert defaults["deployment_type"] == "on-prem"

    @patch.object(ConfigManager, "__init__", lambda x: None)
    def test_get_default_config_api_settings(self):
        """Test get_default_config API settings."""
        manager = ConfigManager.__new__(ConfigManager)
        defaults = manager.get_default_config()
        api = defaults["api"]

        assert api["timeout"] == 30
        assert api["search_timeout"] == 300
        assert api["max_retries"] == 3
        assert api["retry_backoff"] == 2.0
        assert api["default_output_mode"] == "json"
        assert api["prefer_v2_api"] is True

    @patch.object(ConfigManager, "__init__", lambda x: None)
    def test_get_default_config_search_defaults(self):
        """Test get_default_config search defaults."""
        manager = ConfigManager.__new__(ConfigManager)
        defaults = manager.get_default_config()
        search = defaults["search_defaults"]

        assert search["earliest_time"] == DEFAULT_EARLIEST_TIME
        assert search["latest_time"] == DEFAULT_LATEST_TIME
        assert search["max_count"] == 50000
        assert search["status_buckets"] == 300
        assert search["auto_cancel"] == 300


class TestGetEnvOverrides:
    """Tests for _get_env_overrides method."""

    def _setup_manager(self):
        """Helper to create properly configured manager for testing."""
        manager = ConfigManager.__new__(ConfigManager)
        manager.service_name = "splunk"
        manager.env_prefix = "SPLUNK"
        return manager

    @patch.dict(os.environ, {"SPLUNK_SITE_URL": "https://splunk.example.com"}, clear=True)
    def test_url_override(self):
        """Test URL environment variable override."""
        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = self._setup_manager()
            overrides = manager._get_env_overrides()
            assert overrides["url"] == "https://splunk.example.com"

    @patch.dict(os.environ, {"SPLUNK_MANAGEMENT_PORT": "8088"}, clear=True)
    def test_port_override(self):
        """Test port environment variable override."""
        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = self._setup_manager()
            overrides = manager._get_env_overrides()
            assert overrides["port"] == 8088

    @patch.dict(os.environ, {"SPLUNK_MANAGEMENT_PORT": "invalid"}, clear=True)
    def test_port_override_invalid(self):
        """Test invalid port is ignored."""
        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = self._setup_manager()
            overrides = manager._get_env_overrides()
            assert "port" not in overrides

    @patch.dict(os.environ, {"SPLUNK_TOKEN": "test-token"}, clear=True)
    def test_token_override(self):
        """Test token environment variable override."""
        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = self._setup_manager()
            overrides = manager._get_env_overrides()
            assert overrides["token"] == "test-token"
            assert overrides["auth_method"] == "bearer"

    @patch.dict(
        os.environ,
        {"SPLUNK_USERNAME": "admin", "SPLUNK_PASSWORD": "changeme"},
        clear=True,
    )
    def test_basic_auth_override(self):
        """Test username/password environment variable override."""
        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = self._setup_manager()
            overrides = manager._get_env_overrides()
            assert overrides["username"] == "admin"
            assert overrides["password"] == "changeme"
            assert overrides["auth_method"] == "basic"

    @patch.dict(
        os.environ,
        {"SPLUNK_TOKEN": "test-token", "SPLUNK_PASSWORD": "changeme"},
        clear=True,
    )
    def test_token_takes_precedence(self):
        """Test token takes precedence over password for auth method."""
        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = self._setup_manager()
            overrides = manager._get_env_overrides()
            assert overrides["auth_method"] == "bearer"

    @patch.dict(os.environ, {"SPLUNK_VERIFY_SSL": "true"}, clear=True)
    def test_verify_ssl_true(self):
        """Test verify_ssl true variations."""
        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = self._setup_manager()
            overrides = manager._get_env_overrides()
            assert overrides["verify_ssl"] is True

    @patch.dict(os.environ, {"SPLUNK_VERIFY_SSL": "false"}, clear=True)
    def test_verify_ssl_false(self):
        """Test verify_ssl false."""
        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = self._setup_manager()
            overrides = manager._get_env_overrides()
            assert overrides["verify_ssl"] is False

    @patch.dict(os.environ, {"SPLUNK_VERIFY_SSL": "1"}, clear=True)
    def test_verify_ssl_1(self):
        """Test verify_ssl '1' as true."""
        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = self._setup_manager()
            overrides = manager._get_env_overrides()
            assert overrides["verify_ssl"] is True

    @patch.dict(os.environ, {"SPLUNK_VERIFY_SSL": "yes"}, clear=True)
    def test_verify_ssl_yes(self):
        """Test verify_ssl 'yes' as true."""
        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = self._setup_manager()
            overrides = manager._get_env_overrides()
            assert overrides["verify_ssl"] is True

    @patch.dict(os.environ, {"SPLUNK_DEFAULT_APP": "myapp"}, clear=True)
    def test_default_app_override(self):
        """Test default_app environment variable override."""
        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = self._setup_manager()
            overrides = manager._get_env_overrides()
            assert overrides["default_app"] == "myapp"

    @patch.dict(os.environ, {"SPLUNK_DEFAULT_INDEX": "security"}, clear=True)
    def test_default_index_override(self):
        """Test default_index environment variable override."""
        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = self._setup_manager()
            overrides = manager._get_env_overrides()
            assert overrides["default_index"] == "security"


class TestGetClientKwargs:
    """Tests for get_client_kwargs method."""

    def test_client_kwargs_structure(self):
        """Test get_client_kwargs returns expected structure."""
        mock_config = {
            "url": "https://splunk.example.com",
            "port": 8089,
            "token": "test-token",
            "auth_method": "bearer",
            "verify_ssl": True,
            "api": {
                "timeout": 30,
                "max_retries": 3,
                "retry_backoff": 2.0,
            },
        }

        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = ConfigManager.__new__(ConfigManager)
            manager.get_splunk_config = MagicMock(return_value=mock_config)
            kwargs = manager.get_client_kwargs()

            assert kwargs["base_url"] == "https://splunk.example.com"
            assert kwargs["port"] == 8089
            assert kwargs["timeout"] == 30
            assert kwargs["verify_ssl"] is True
            assert kwargs["max_retries"] == 3
            assert kwargs["retry_backoff"] == 2.0
            assert kwargs["token"] == "test-token"

    def test_client_kwargs_basic_auth(self):
        """Test get_client_kwargs with basic auth."""
        mock_config = {
            "url": "https://splunk.example.com",
            "port": 8089,
            "username": "admin",
            "password": "changeme",
            "auth_method": "basic",
            "verify_ssl": True,
            "api": {},
        }

        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = ConfigManager.__new__(ConfigManager)
            manager.get_splunk_config = MagicMock(return_value=mock_config)
            kwargs = manager.get_client_kwargs()

            assert kwargs["username"] == "admin"
            assert kwargs["password"] == "changeme"
            assert "token" not in kwargs

    def test_client_kwargs_fallback_to_token(self):
        """Test get_client_kwargs falls back to token if no basic auth."""
        mock_config = {
            "url": "https://splunk.example.com",
            "port": 8089,
            "token": "fallback-token",
            "auth_method": "basic",  # Set to basic but no username/password
            "verify_ssl": True,
            "api": {},
        }

        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = ConfigManager.__new__(ConfigManager)
            manager.get_splunk_config = MagicMock(return_value=mock_config)
            kwargs = manager.get_client_kwargs()

            assert kwargs["token"] == "fallback-token"


class TestValidateConfig:
    """Tests for validate_config method."""

    def test_validate_missing_url(self):
        """Test validation fails with missing URL."""
        mock_config = {"auth_method": "bearer", "token": "test"}

        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = ConfigManager.__new__(ConfigManager)
            manager.get_splunk_config = MagicMock(return_value=mock_config)
            errors = manager.validate_config()

            assert len(errors) >= 1
            assert any("URL" in e for e in errors)

    def test_validate_missing_token(self):
        """Test validation fails with missing token for bearer auth."""
        mock_config = {"url": "https://splunk.example.com", "auth_method": "bearer"}

        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = ConfigManager.__new__(ConfigManager)
            manager.get_splunk_config = MagicMock(return_value=mock_config)
            errors = manager.validate_config()

            assert len(errors) >= 1
            assert any("token" in e.lower() for e in errors)

    def test_validate_missing_basic_auth(self):
        """Test validation fails with missing username/password for basic auth."""
        mock_config = {
            "url": "https://splunk.example.com",
            "auth_method": "basic",
            "username": "admin",
            # Missing password
        }

        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = ConfigManager.__new__(ConfigManager)
            manager.get_splunk_config = MagicMock(return_value=mock_config)
            errors = manager.validate_config()

            assert len(errors) >= 1
            assert any("password" in e.lower() for e in errors)

    def test_validate_valid_bearer_config(self):
        """Test validation passes with valid bearer config."""
        mock_config = {
            "url": "https://splunk.example.com",
            "auth_method": "bearer",
            "token": "valid-token",
        }

        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = ConfigManager.__new__(ConfigManager)
            manager.get_splunk_config = MagicMock(return_value=mock_config)
            errors = manager.validate_config()

            assert len(errors) == 0

    def test_validate_valid_basic_config(self):
        """Test validation passes with valid basic auth config."""
        mock_config = {
            "url": "https://splunk.example.com",
            "auth_method": "basic",
            "username": "admin",
            "password": "changeme",
        }

        with patch.object(ConfigManager, "__init__", lambda x: None):
            manager = ConfigManager.__new__(ConfigManager)
            manager.get_splunk_config = MagicMock(return_value=mock_config)
            errors = manager.validate_config()

            assert len(errors) == 0


class TestGlobalFunctions:
    """Tests for global configuration functions."""

    def test_get_config_manager_creates_singleton(self):
        """Test get_config_manager creates singleton."""
        # Reset the global (thread-safe)
        import splunk_as.config_manager as cm

        with cm._config_manager_lock:
            cm._config_manager = None

        result1 = get_config_manager()
        result2 = get_config_manager()

        # Should return same instance (singleton behavior)
        assert result1 is result2
        assert isinstance(result1, ConfigManager)

    @patch("splunk_as.config_manager.get_config_manager")
    def test_get_config(self, mock_get_manager):
        """Test get_config returns splunk config."""
        mock_manager = MagicMock()
        mock_manager.get_splunk_config.return_value = {"url": "https://test.com"}
        mock_get_manager.return_value = mock_manager

        result = get_config()

        assert result == {"url": "https://test.com"}
        mock_manager.get_splunk_config.assert_called_once()

    @patch("splunk_as.config_manager.get_config_manager")
    def test_get_search_defaults(self, mock_get_manager):
        """Test get_search_defaults returns search defaults."""
        mock_manager = MagicMock()
        mock_manager.get_splunk_config.return_value = {
            "search_defaults": {"earliest_time": "-1h", "latest_time": "now"}
        }
        mock_get_manager.return_value = mock_manager

        result = get_search_defaults()

        assert result["earliest_time"] == "-1h"
        assert result["latest_time"] == "now"

    @patch("splunk_as.config_manager.get_config_manager")
    def test_get_api_settings(self, mock_get_manager):
        """Test get_api_settings returns API settings."""
        mock_manager = MagicMock()
        mock_manager.get_splunk_config.return_value = {"api": {"timeout": 60}}
        mock_get_manager.return_value = mock_manager

        result = get_api_settings()

        assert result["timeout"] == 60

    @patch("splunk_as.config_manager.SplunkClient")
    @patch("splunk_as.config_manager.get_config_manager")
    def test_get_splunk_client_valid_config(self, mock_get_manager, mock_client_class):
        """Test get_splunk_client creates client with valid config."""
        mock_manager = MagicMock()
        mock_manager.validate_config.return_value = []  # No errors
        mock_manager.get_client_kwargs.return_value = {
            "base_url": "https://test.com",
            "token": "test-token",
        }
        mock_get_manager.return_value = mock_manager

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        result = get_splunk_client()

        assert result is mock_client
        mock_client_class.assert_called_once()

    @patch("splunk_as.config_manager.get_config_manager")
    def test_get_splunk_client_invalid_config(self, mock_get_manager):
        """Test get_splunk_client raises ValidationError with invalid config."""
        mock_manager = MagicMock()
        mock_manager.validate_config.return_value = [
            "Missing URL",
            "Missing token",
        ]
        mock_get_manager.return_value = mock_manager

        with pytest.raises(ValidationError) as exc_info:
            get_splunk_client()

        assert "Missing URL" in str(exc_info.value)
        assert "Missing token" in str(exc_info.value)


class TestThreadSafety:
    """Tests for thread-safe singleton access."""

    def test_concurrent_access(self):
        """Test concurrent access to get_config_manager."""
        # Reset the global (thread-safe)
        import splunk_as.config_manager as cm

        with cm._config_manager_lock:
            cm._config_manager = None

        results = []
        errors = []

        def get_manager():
            try:
                manager = get_config_manager()
                results.append(manager)
            except Exception as e:
                errors.append(e)

        # Run multiple threads concurrently
        threads = [threading.Thread(target=get_manager) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should get the same instance with no errors
        assert len(errors) == 0
        assert all(r is results[0] for r in results)
