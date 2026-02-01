"""Tests for the Splunk credential manager."""

from unittest.mock import MagicMock, patch

import pytest

from splunk_as.credential_manager import (
    SplunkCredentialManager,
    get_credential_manager,
    get_credentials,
    is_keychain_available,
    store_credentials,
    validate_credentials,
)


class TestSplunkCredentialManager:
    """Tests for SplunkCredentialManager class."""

    def test_get_service_name(self):
        """Test service name is splunk-assistant."""
        manager = SplunkCredentialManager()
        assert manager.get_service_name() == "splunk-assistant"

    def test_get_env_prefix(self):
        """Test environment prefix is SPLUNK."""
        manager = SplunkCredentialManager()
        assert manager.get_env_prefix() == "SPLUNK"

    def test_get_credential_fields(self):
        """Test credential fields list."""
        manager = SplunkCredentialManager()
        fields = manager.get_credential_fields()
        assert "site_url" in fields
        assert "token" in fields
        assert "username" in fields
        assert "password" in fields
        assert "port" in fields

    def test_get_required_fields(self):
        """Test required fields only includes site_url."""
        manager = SplunkCredentialManager()
        required = manager.get_required_fields()
        assert required == ["site_url"]

    def test_get_credential_not_found_hint(self):
        """Test hint text includes setup instructions."""
        manager = SplunkCredentialManager()
        hint = manager.get_credential_not_found_hint()
        assert "SPLUNK_SITE_URL" in hint
        assert "SPLUNK_TOKEN" in hint
        assert "/splunk-assistant-setup" in hint


class TestValidateCredentials:
    """Tests for credential validation."""

    def test_validate_missing_site_url(self):
        """Test validation fails without site_url."""
        from splunk_as.error_handler import ValidationError

        manager = SplunkCredentialManager()
        with pytest.raises(ValidationError, match="site_url is required"):
            manager.validate_credentials({})

    def test_validate_missing_auth(self):
        """Test validation fails without token or username+password."""
        from splunk_as.error_handler import ValidationError

        manager = SplunkCredentialManager()
        with pytest.raises(ValidationError, match="token or username\\+password"):
            manager.validate_credentials({"site_url": "https://splunk.example.com"})

    def test_validate_missing_password_with_username(self):
        """Test validation fails with username but no password."""
        from splunk_as.error_handler import ValidationError

        manager = SplunkCredentialManager()
        with pytest.raises(ValidationError, match="token or username\\+password"):
            manager.validate_credentials(
                {"site_url": "https://splunk.example.com", "username": "admin"}
            )

    @patch("splunk_as.credential_manager.SplunkClient")
    def test_validate_with_token_success(self, mock_client_class):
        """Test validation succeeds with token auth."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get_server_info.return_value = {"serverName": "splunk-server"}
        mock_client_class.return_value = mock_client

        manager = SplunkCredentialManager()
        result = manager.validate_credentials(
            {"site_url": "https://splunk.example.com", "token": "test-token"}
        )

        assert result["serverName"] == "splunk-server"
        mock_client_class.assert_called_once()

    @patch("splunk_as.credential_manager.SplunkClient")
    def test_validate_with_basic_auth_success(self, mock_client_class):
        """Test validation succeeds with basic auth."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get_server_info.return_value = {"serverName": "splunk-server"}
        mock_client_class.return_value = mock_client

        manager = SplunkCredentialManager()
        result = manager.validate_credentials(
            {
                "site_url": "https://splunk.example.com",
                "username": "admin",
                "password": "changeme",
            }
        )

        assert result["serverName"] == "splunk-server"

    @patch("splunk_as.credential_manager.SplunkClient")
    def test_validate_connection_failure(self, mock_client_class):
        """Test validation handles connection failure."""
        from splunk_as.error_handler import AuthenticationError

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get_server_info.side_effect = Exception("Connection refused")
        mock_client_class.return_value = mock_client

        manager = SplunkCredentialManager()
        with pytest.raises(AuthenticationError, match="Failed to connect"):
            manager.validate_credentials(
                {"site_url": "https://splunk.example.com", "token": "bad-token"}
            )


class TestGetCredentials:
    """Tests for get_credentials function."""

    @patch.object(SplunkCredentialManager, "get_credentials_from_json")
    @patch.object(SplunkCredentialManager, "get_credentials_from_keychain")
    @patch.object(SplunkCredentialManager, "get_credentials_from_env")
    def test_priority_env_first(self, mock_env, mock_keychain, mock_json):
        """Test environment variables have highest priority."""
        mock_env.return_value = {
            "site_url": "https://env.example.com",
            "token": "env-token",
        }
        mock_keychain.return_value = {
            "site_url": "https://keychain.example.com",
            "token": "keychain-token",
        }
        mock_json.return_value = {
            "site_url": "https://json.example.com",
            "token": "json-token",
        }

        manager = SplunkCredentialManager()
        creds = manager.get_credentials()

        assert creds["site_url"] == "https://env.example.com"
        assert creds["token"] == "env-token"

    @patch.object(SplunkCredentialManager, "get_credentials_from_json")
    @patch.object(SplunkCredentialManager, "get_credentials_from_keychain")
    @patch.object(SplunkCredentialManager, "get_credentials_from_env")
    def test_fallback_to_keychain(self, mock_env, mock_keychain, mock_json):
        """Test fallback to keychain when env vars empty."""
        mock_env.return_value = {"site_url": None, "token": None}
        mock_keychain.return_value = {
            "site_url": "https://keychain.example.com",
            "token": "keychain-token",
        }
        mock_json.return_value = {}

        manager = SplunkCredentialManager()
        creds = manager.get_credentials()

        assert creds["site_url"] == "https://keychain.example.com"
        assert creds["token"] == "keychain-token"

    @patch.object(SplunkCredentialManager, "get_credentials_from_json")
    @patch.object(SplunkCredentialManager, "get_credentials_from_keychain")
    @patch.object(SplunkCredentialManager, "get_credentials_from_env")
    def test_fallback_to_json(self, mock_env, mock_keychain, mock_json):
        """Test fallback to JSON when keychain empty."""
        mock_env.return_value = {}
        mock_keychain.return_value = {}
        mock_json.return_value = {
            "site_url": "https://json.example.com",
            "token": "json-token",
        }

        manager = SplunkCredentialManager()
        creds = manager.get_credentials()

        assert creds["site_url"] == "https://json.example.com"
        assert creds["token"] == "json-token"

    @patch.object(SplunkCredentialManager, "get_credentials_from_json")
    @patch.object(SplunkCredentialManager, "get_credentials_from_keychain")
    @patch.object(SplunkCredentialManager, "get_credentials_from_env")
    def test_missing_site_url_raises(self, mock_env, mock_keychain, mock_json):
        """Test raises CredentialNotFoundError when site_url missing."""
        from assistant_skills_lib import CredentialNotFoundError

        mock_env.return_value = {"token": "some-token"}
        mock_keychain.return_value = {}
        mock_json.return_value = {}

        manager = SplunkCredentialManager()
        with pytest.raises(CredentialNotFoundError):
            manager.get_credentials()

    @patch.object(SplunkCredentialManager, "get_credentials_from_json")
    @patch.object(SplunkCredentialManager, "get_credentials_from_keychain")
    @patch.object(SplunkCredentialManager, "get_credentials_from_env")
    def test_missing_auth_raises(self, mock_env, mock_keychain, mock_json):
        """Test raises CredentialNotFoundError when no auth credentials."""
        from assistant_skills_lib import CredentialNotFoundError

        mock_env.return_value = {"site_url": "https://splunk.example.com"}
        mock_keychain.return_value = {}
        mock_json.return_value = {}

        manager = SplunkCredentialManager()
        with pytest.raises(CredentialNotFoundError):
            manager.get_credentials()

    @patch.object(SplunkCredentialManager, "get_credentials_from_json")
    @patch.object(SplunkCredentialManager, "get_credentials_from_keychain")
    @patch.object(SplunkCredentialManager, "get_credentials_from_env")
    def test_accepts_basic_auth(self, mock_env, mock_keychain, mock_json):
        """Test accepts username+password instead of token."""
        mock_env.return_value = {
            "site_url": "https://splunk.example.com",
            "username": "admin",
            "password": "changeme",
        }
        mock_keychain.return_value = {}
        mock_json.return_value = {}

        manager = SplunkCredentialManager()
        creds = manager.get_credentials()

        assert creds["site_url"] == "https://splunk.example.com"
        assert creds["username"] == "admin"
        assert creds["password"] == "changeme"


class TestSingletonAndConvenienceFunctions:
    """Tests for singleton and convenience functions."""

    def test_get_credential_manager_singleton(self):
        """Test get_credential_manager returns same instance."""
        # Reset the singleton for testing
        import splunk_as.credential_manager as cm

        cm._credential_manager = None

        manager1 = get_credential_manager()
        manager2 = get_credential_manager()

        assert manager1 is manager2

    @patch("splunk_as.credential_manager.SplunkCredentialManager.is_keychain_available")
    def test_is_keychain_available(self, mock_is_available):
        """Test is_keychain_available wrapper."""
        mock_is_available.return_value = True
        assert is_keychain_available() is True

        mock_is_available.return_value = False
        assert is_keychain_available() is False


class TestStoreCredentials:
    """Tests for store_credentials function."""

    def test_store_requires_site_url(self):
        """Test store_credentials requires non-empty site_url."""
        from splunk_as.error_handler import ValidationError

        with pytest.raises(ValidationError, match="site_url cannot be empty"):
            store_credentials(site_url="")

        with pytest.raises(ValidationError, match="site_url cannot be empty"):
            store_credentials(site_url="   ")

    def test_store_requires_auth(self):
        """Test store_credentials requires token or username+password."""
        from splunk_as.error_handler import ValidationError

        with pytest.raises(ValidationError, match="token or username\\+password"):
            store_credentials(site_url="https://splunk.example.com")

    @patch.object(SplunkCredentialManager, "store_credentials")
    def test_store_with_token(self, mock_store):
        """Test store_credentials with token."""
        from assistant_skills_lib import CredentialBackend

        mock_store.return_value = CredentialBackend.KEYCHAIN

        result = store_credentials(
            site_url="https://splunk.example.com/", token="test-token", port=8089
        )

        mock_store.assert_called_once()
        call_args = mock_store.call_args[0][0]
        assert call_args["site_url"] == "https://splunk.example.com"  # Trailing slash stripped
        assert call_args["token"] == "test-token"
        assert call_args["port"] == "8089"
        assert result == CredentialBackend.KEYCHAIN

    @patch.object(SplunkCredentialManager, "store_credentials")
    def test_store_with_basic_auth(self, mock_store):
        """Test store_credentials with username+password."""
        from assistant_skills_lib import CredentialBackend

        mock_store.return_value = CredentialBackend.JSON_FILE

        result = store_credentials(
            site_url="https://splunk.example.com",
            username="admin",
            password="changeme",
        )

        mock_store.assert_called_once()
        call_args = mock_store.call_args[0][0]
        assert call_args["username"] == "admin"
        assert call_args["password"] == "changeme"
        assert result == CredentialBackend.JSON_FILE


class TestValidateCredentialsConvenience:
    """Tests for validate_credentials convenience function."""

    @patch.object(SplunkCredentialManager, "validate_credentials")
    def test_validate_with_token(self, mock_validate):
        """Test validate_credentials convenience with token."""
        mock_validate.return_value = {"serverName": "splunk-server"}

        result = validate_credentials(
            site_url="https://splunk.example.com", token="test-token", port=8089
        )

        assert result["serverName"] == "splunk-server"
        mock_validate.assert_called_once()
        call_args = mock_validate.call_args[0][0]
        assert call_args["site_url"] == "https://splunk.example.com"
        assert call_args["token"] == "test-token"
        assert call_args["port"] == "8089"

    @patch.object(SplunkCredentialManager, "validate_credentials")
    def test_validate_with_basic_auth(self, mock_validate):
        """Test validate_credentials convenience with basic auth."""
        mock_validate.return_value = {"serverName": "splunk-server"}

        result = validate_credentials(
            site_url="https://splunk.example.com",
            username="admin",
            password="changeme",
        )

        assert result["serverName"] == "splunk-server"
        call_args = mock_validate.call_args[0][0]
        assert call_args["username"] == "admin"
        assert call_args["password"] == "changeme"
