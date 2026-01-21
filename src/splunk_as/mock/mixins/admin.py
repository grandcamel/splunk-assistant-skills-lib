"""
Admin Mixin for Mock Splunk Client

Provides mock responses for administrative operations:
- Server info and health
- User and role management
- Token management
- Generic REST access
"""

import time
import uuid
from typing import Any, Dict, List, Optional


class AdminMixin:
    """Mixin providing administrative mock methods.

    Maintains internal state for users, roles, and tokens.

    Example:
        class MyMock(AdminMixin, MockSplunkClientBase):
            pass

        client = MyMock()
        info = client.get_server_info()
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize admin mixin state."""
        super().__init__(*args, **kwargs)

        self._server_info: Dict[str, Any] = {
            "build": "abc12345",
            "cpu_arch": "x86_64",
            "guid": str(uuid.uuid4()),
            "isFree": False,
            "isTrial": False,
            "licenseState": "OK",
            "mode": "normal",
            "numberOfCores": 8,
            "numberOfVirtualCores": 16,
            "os_build": "#1 SMP",
            "os_name": "Linux",
            "os_version": "5.15.0-generic",
            "physicalMemoryMB": 32768,
            "product_type": "enterprise",
            "server_roles": ["indexer", "search_head"],
            "serverName": "mock-splunk",
            "version": "9.1.0",
        }

        self._current_user: Dict[str, Any] = {
            "username": "admin",
            "realname": "Administrator",
            "email": "admin@example.com",
            "roles": ["admin", "power", "user"],
            "capabilities": [
                "admin_all_objects",
                "search",
                "schedule_search",
                "accelerate_search",
                "list_inputs",
                "edit_user",
            ],
            "defaultApp": "search",
        }

        self._users: Dict[str, Dict[str, Any]] = {
            "admin": self._current_user,
            "power_user": {
                "username": "power_user",
                "realname": "Power User",
                "email": "power@example.com",
                "roles": ["power", "user"],
                "capabilities": ["search", "schedule_search"],
                "defaultApp": "search",
            },
            "regular_user": {
                "username": "regular_user",
                "realname": "Regular User",
                "email": "user@example.com",
                "roles": ["user"],
                "capabilities": ["search"],
                "defaultApp": "search",
            },
        }

        self._roles: Dict[str, Dict[str, Any]] = {
            "admin": {
                "name": "admin",
                "capabilities": ["admin_all_objects", "edit_user", "list_inputs"],
                "imported_roles": ["power"],
                "srchIndexesAllowed": ["*"],
                "srchIndexesDefault": ["main"],
            },
            "power": {
                "name": "power",
                "capabilities": ["schedule_search", "accelerate_search"],
                "imported_roles": ["user"],
                "srchIndexesAllowed": ["*", "_*"],
                "srchIndexesDefault": ["main"],
            },
            "user": {
                "name": "user",
                "capabilities": ["search"],
                "imported_roles": [],
                "srchIndexesAllowed": ["main"],
                "srchIndexesDefault": ["main"],
            },
        }

        self._tokens: Dict[str, Dict[str, Any]] = {}

    def set_server_info(self, **kwargs: Any) -> None:
        """Update server info attributes.

        Args:
            **kwargs: Server info fields to update
        """
        self._server_info.update(kwargs)

    def set_current_user(self, **kwargs: Any) -> None:
        """Update current user attributes.

        Args:
            **kwargs: User fields to update
        """
        self._current_user.update(kwargs)

    def add_user(
        self,
        username: str,
        realname: str = "",
        email: str = "",
        roles: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
    ) -> None:
        """Add a mock user.

        Args:
            username: Username
            realname: Display name
            email: Email address
            roles: List of role names
            capabilities: List of capabilities
        """
        self._users[username] = {
            "username": username,
            "realname": realname or username,
            "email": email,
            "roles": roles or ["user"],
            "capabilities": capabilities or ["search"],
            "defaultApp": "search",
        }

    def add_role(
        self,
        name: str,
        capabilities: Optional[List[str]] = None,
        imported_roles: Optional[List[str]] = None,
        indexes_allowed: Optional[List[str]] = None,
    ) -> None:
        """Add a mock role.

        Args:
            name: Role name
            capabilities: List of capabilities
            imported_roles: Roles to inherit from
            indexes_allowed: Allowed search indexes
        """
        self._roles[name] = {
            "name": name,
            "capabilities": capabilities or [],
            "imported_roles": imported_roles or [],
            "srchIndexesAllowed": indexes_allowed or ["main"],
            "srchIndexesDefault": ["main"],
        }

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information.

        Returns:
            Server info dictionary
        """
        self._record_call("GET", "/services/server/info")

        return self._server_info

    def get_server_health(self) -> Dict[str, Any]:
        """Get server health status.

        Returns:
            Health status dictionary
        """
        self._record_call("GET", "/services/server/health")

        return {
            "status": "green",
            "features": {
                "search": "green",
                "indexing": "green",
                "kvstore": "green",
                "cluster": "green",
            },
            "messages": [],
        }

    def whoami(self) -> Dict[str, Any]:
        """Get current user information.

        Returns:
            Current user dictionary
        """
        self._record_call("GET", "/services/authentication/current-context")

        return self._current_user

    def list_users(
        self,
        count: int = 30,
        offset: int = 0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List all users.

        Args:
            count: Maximum results
            offset: Pagination offset

        Returns:
            User list response
        """
        self._record_call(
            "GET",
            "/services/authentication/users",
            params={"count": count, "offset": offset},
        )

        users = list(self._users.values())
        paginated = users[offset : offset + count]

        return {
            "entry": [{"name": u["username"], "content": u} for u in paginated],
            "paging": {
                "total": len(users),
                "offset": offset,
                "count": len(paginated),
            },
        }

    def get_user(self, username: str) -> Dict[str, Any]:
        """Get specific user details.

        Args:
            username: Username to look up

        Returns:
            User information
        """
        endpoint = f"/services/authentication/users/{username}"
        self._record_call("GET", endpoint)

        user = self._users.get(username)
        if not user:
            return {"entry": []}

        return {"entry": [{"name": username, "content": user}]}

    def list_roles(
        self,
        count: int = 30,
        offset: int = 0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List all roles.

        Args:
            count: Maximum results
            offset: Pagination offset

        Returns:
            Role list response
        """
        self._record_call(
            "GET",
            "/services/authorization/roles",
            params={"count": count, "offset": offset},
        )

        roles = list(self._roles.values())
        paginated = roles[offset : offset + count]

        return {
            "entry": [{"name": r["name"], "content": r} for r in paginated],
            "paging": {
                "total": len(roles),
                "offset": offset,
                "count": len(paginated),
            },
        }

    def get_role(self, role_name: str) -> Dict[str, Any]:
        """Get specific role details.

        Args:
            role_name: Role name to look up

        Returns:
            Role information
        """
        endpoint = f"/services/authorization/roles/{role_name}"
        self._record_call("GET", endpoint)

        role = self._roles.get(role_name)
        if not role:
            return {"entry": []}

        return {"entry": [{"name": role_name, "content": role}]}

    def get_capabilities(self, username: Optional[str] = None) -> Dict[str, Any]:
        """Get capabilities for a user.

        Args:
            username: Username (None for current user)

        Returns:
            Capabilities list
        """
        self._record_call("GET", "/services/authorization/capabilities")

        user = self._users.get(username or "admin", self._current_user)
        return {"capabilities": user.get("capabilities", [])}

    def list_tokens(self, username: Optional[str] = None) -> Dict[str, Any]:
        """List JWT tokens.

        Args:
            username: Filter by username

        Returns:
            Token list
        """
        self._record_call(
            "GET",
            "/services/authorization/tokens",
            params={"username": username},
        )

        tokens = list(self._tokens.values())
        if username:
            tokens = [t for t in tokens if t.get("username") == username]

        return {
            "entry": [{"name": t["id"], "content": t} for t in tokens],
        }

    def create_token(
        self,
        name: str,
        audience: str = "api",
        expires_on: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create a new JWT token.

        Args:
            name: Token name
            audience: Token audience
            expires_on: Expiration time

        Returns:
            Created token info including the token value
        """
        self._record_call(
            "POST",
            "/services/authorization/tokens",
            data={"name": name, "audience": audience, "expires_on": expires_on},
        )

        token_id = str(uuid.uuid4())
        token_value = f"eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.{uuid.uuid4().hex}"

        self._tokens[token_id] = {
            "id": token_id,
            "name": name,
            "audience": audience,
            "username": self._current_user["username"],
            "expires_on": expires_on or "+30d",
            "created_at": time.time(),
            "status": "active",
        }

        return {
            "entry": [
                {
                    "name": token_id,
                    "content": {
                        **self._tokens[token_id],
                        "token": token_value,
                    },
                }
            ]
        }

    def delete_token(self, token_id: str) -> Dict[str, Any]:
        """Delete a JWT token.

        Args:
            token_id: Token ID to delete

        Returns:
            Empty dict on success
        """
        endpoint = f"/services/authorization/tokens/{token_id}"
        self._record_call("DELETE", endpoint)

        if token_id in self._tokens:
            del self._tokens[token_id]

        return {}

    def rest_get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generic REST GET request.

        Args:
            endpoint: REST endpoint
            params: Query parameters

        Returns:
            Response dict
        """
        self._record_call("GET", endpoint, params=params)

        # Check for configured response
        return self._get_response(endpoint, params=params)

    def rest_post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generic REST POST request.

        Args:
            endpoint: REST endpoint
            data: POST data
            params: Query parameters

        Returns:
            Response dict
        """
        self._record_call("POST", endpoint, data=data, params=params)

        return self._get_response(endpoint, data=data, params=params)

    def _get_response(
        self,
        endpoint: str,
        default: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get configured response or default."""
        # Delegate to base class if available
        if hasattr(super(), "_get_response"):
            return super()._get_response(endpoint, default, **kwargs)  # type: ignore[misc]
        return default or {"entry": []}

    def _record_call(self, *args: Any, **kwargs: Any) -> None:
        """Record call - delegates to base class."""
        if hasattr(super(), "_record_call"):
            super()._record_call(*args, **kwargs)  # type: ignore[misc]
