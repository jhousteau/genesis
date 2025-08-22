"""
API Client Module

HTTP client with retry mechanisms, circuit breaker, authentication,
and comprehensive error handling for external API integrations.
"""

import json
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

import httpx

from ..errors import AuthenticationError, CircuitBreaker, NetworkError, retry
from ..logging import get_logger

logger = get_logger(__name__)


class HTTPMethod(Enum):
    """HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class APIResponse:
    """API response wrapper."""

    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    json_data: Optional[Dict[str, Any]]
    url: str
    request_time: float

    @property
    def is_success(self) -> bool:
        """Check if response is successful."""
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if response is client error."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response is server error."""
        return 500 <= self.status_code < 600

    def raise_for_status(self) -> None:
        """Raise exception for HTTP errors."""
        if self.is_client_error:
            raise NetworkError(
                f"Client error {self.status_code}: {self.text}", url=self.url
            )
        elif self.is_server_error:
            raise NetworkError(
                f"Server error {self.status_code}: {self.text}", url=self.url
            )

    def json(self) -> Dict[str, Any]:
        """Get JSON data from response."""
        if self.json_data is None:
            try:
                self.json_data = json.loads(self.text)
            except json.JSONDecodeError as e:
                raise ValueError(f"Response is not valid JSON: {e}")
        return self.json_data

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status_code": self.status_code,
            "headers": dict(self.headers),
            "text": self.text,
            "json_data": self.json_data,
            "url": self.url,
            "request_time": self.request_time,
            "is_success": self.is_success,
        }


class Authentication:
    """Base authentication class."""

    def apply_auth(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Apply authentication to headers."""
        return headers


class BearerTokenAuth(Authentication):
    """Bearer token authentication."""

    def __init__(self, token: str):
        self.token = token

    def apply_auth(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Apply bearer token to headers."""
        headers = headers.copy()
        headers["Authorization"] = f"Bearer {self.token}"
        return headers


class APIKeyAuth(Authentication):
    """API key authentication."""

    def __init__(self, api_key: str, header_name: str = "X-API-Key"):
        self.api_key = api_key
        self.header_name = header_name

    def apply_auth(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Apply API key to headers."""
        headers = headers.copy()
        headers[self.header_name] = self.api_key
        return headers


class BasicAuth(Authentication):
    """HTTP Basic authentication."""

    def __init__(self, username: str, password: str):
        import base64

        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.credentials = credentials

    def apply_auth(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Apply basic auth to headers."""
        headers = headers.copy()
        headers["Authorization"] = f"Basic {self.credentials}"
        return headers


class RequestInterceptor:
    """Request interceptor for modifying requests."""

    def before_request(
        self, method: str, url: str, headers: Dict[str, str], **kwargs
    ) -> Dict[str, Any]:
        """Called before sending request."""
        return {"method": method, "url": url, "headers": headers, **kwargs}

    def after_response(self, response: APIResponse) -> APIResponse:
        """Called after receiving response."""
        return response


class LoggingInterceptor(RequestInterceptor):
    """Logging interceptor."""

    def before_request(
        self, method: str, url: str, headers: Dict[str, str], **kwargs
    ) -> Dict[str, Any]:
        """Log request details."""
        logger.info(f"API Request: {method} {url}")
        logger.debug("Request headers", headers=headers)
        return super().before_request(method, url, headers, **kwargs)

    def after_response(self, response: APIResponse) -> APIResponse:
        """Log response details."""
        logger.info(
            f"API Response: {response.status_code}",
            url=response.url,
            status_code=response.status_code,
            request_time=response.request_time,
        )
        if not response.is_success:
            logger.warning(
                f"API Error Response: {response.status_code}",
                url=response.url,
                response_text=response.text[:500],
            )
        return response


class RateLimitInterceptor(RequestInterceptor):
    """Rate limiting interceptor."""

    def __init__(self, requests_per_second: float = 10.0):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0
        self._lock = threading.Lock()

    def before_request(
        self, method: str, url: str, headers: Dict[str, str], **kwargs
    ) -> Dict[str, Any]:
        """Apply rate limiting."""
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f}s")
                time.sleep(sleep_time)

            self.last_request_time = time.time()

        return super().before_request(method, url, headers, **kwargs)


class APIClient:
    """
    High-level HTTP client with advanced features.
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        circuit_breaker: Optional[CircuitBreaker] = None,
        auth: Optional[Authentication] = None,
        default_headers: Optional[Dict[str, str]] = None,
        verify_ssl: bool = True,
        user_agent: str = "Whitehorse-APIClient/1.0",
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.auth = auth
        self.verify_ssl = verify_ssl

        # Default headers
        self.default_headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
            "Content-Type": "application/json",
            **(default_headers or {}),
        }

        # Interceptors
        self.interceptors: List[RequestInterceptor] = []

        # Add default logging interceptor
        self.add_interceptor(LoggingInterceptor())

        # HTTP client
        self.client = httpx.Client(timeout=timeout, verify=verify_ssl)

        logger.info(f"Initialized API client with base URL: {base_url}")

    def add_interceptor(self, interceptor: RequestInterceptor) -> None:
        """Add request interceptor."""
        self.interceptors.append(interceptor)
        logger.debug(f"Added interceptor: {interceptor.__class__.__name__}")

    def remove_interceptor(self, interceptor_class: type) -> None:
        """Remove interceptor by class."""
        self.interceptors = [
            i for i in self.interceptors if not isinstance(i, interceptor_class)
        ]
        logger.debug(f"Removed interceptor: {interceptor_class.__name__}")

    def _build_url(self, path: str) -> str:
        """Build full URL from path."""
        if path.startswith(("http://", "https://")):
            return path

        if self.base_url:
            return urljoin(f"{self.base_url}/", path.lstrip("/"))

        return path

    def _prepare_headers(
        self, headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Prepare request headers."""
        request_headers = self.default_headers.copy()

        if headers:
            request_headers.update(headers)

        # Apply authentication
        if self.auth:
            request_headers = self.auth.apply_auth(request_headers)

        return request_headers

    def _apply_interceptors_before(
        self, method: str, url: str, **kwargs
    ) -> Dict[str, Any]:
        """Apply before-request interceptors."""
        request_data = {"method": method, "url": url, **kwargs}

        for interceptor in self.interceptors:
            request_data = interceptor.before_request(**request_data)

        return request_data

    def _apply_interceptors_after(self, response: APIResponse) -> APIResponse:
        """Apply after-response interceptors."""
        for interceptor in self.interceptors:
            response = interceptor.after_response(response)

        return response

    @retry()
    def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        files: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> APIResponse:
        """Make HTTP request with retry logic."""
        start_time = time.time()

        try:
            # Build URL and prepare headers
            full_url = self._build_url(url)
            request_headers = self._prepare_headers(headers)

            # Prepare request data
            request_kwargs = {"headers": request_headers, "params": params, **kwargs}

            # Add body data
            if json_data is not None:
                request_kwargs["json"] = json_data
            elif data is not None:
                request_kwargs["data"] = data
            elif files is not None:
                request_kwargs["files"] = files
                # Remove content-type for multipart uploads
                if "Content-Type" in request_headers:
                    del request_headers["Content-Type"]

            # Apply interceptors
            request_data = self._apply_interceptors_before(
                method, full_url, **request_kwargs
            )

            # Make request
            response = self.client.request(**request_data)

            # Parse JSON if possible
            json_response = None
            try:
                if response.headers.get("content-type", "").startswith(
                    "application/json"
                ):
                    json_response = response.json()
            except (json.JSONDecodeError, ValueError):
                pass

            # Create response object
            api_response = APIResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                content=response.content,
                text=response.text,
                json_data=json_response,
                url=str(response.url),
                request_time=time.time() - start_time,
            )

            # Apply after-response interceptors
            api_response = self._apply_interceptors_after(api_response)

            return api_response

        except Exception as e:
            request_time = time.time() - start_time
            logger.error(
                f"Request failed: {method} {url}",
                error=str(e),
                request_time=request_time,
            )
            raise NetworkError(f"Request failed: {str(e)}", url=url)

    def get(self, url: str, **kwargs) -> APIResponse:
        """Make GET request."""
        return self._make_request(HTTPMethod.GET.value, url, **kwargs)

    def post(self, url: str, **kwargs) -> APIResponse:
        """Make POST request."""
        return self._make_request(HTTPMethod.POST.value, url, **kwargs)

    def put(self, url: str, **kwargs) -> APIResponse:
        """Make PUT request."""
        return self._make_request(HTTPMethod.PUT.value, url, **kwargs)

    def patch(self, url: str, **kwargs) -> APIResponse:
        """Make PATCH request."""
        return self._make_request(HTTPMethod.PATCH.value, url, **kwargs)

    def delete(self, url: str, **kwargs) -> APIResponse:
        """Make DELETE request."""
        return self._make_request(HTTPMethod.DELETE.value, url, **kwargs)

    def head(self, url: str, **kwargs) -> APIResponse:
        """Make HEAD request."""
        return self._make_request(HTTPMethod.HEAD.value, url, **kwargs)

    def options(self, url: str, **kwargs) -> APIResponse:
        """Make OPTIONS request."""
        return self._make_request(HTTPMethod.OPTIONS.value, url, **kwargs)

    def upload_file(
        self,
        url: str,
        file_path: str,
        file_field: str = "file",
        additional_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> APIResponse:
        """Upload file to endpoint."""
        try:
            with open(file_path, "rb") as f:
                files = {file_field: f}

                # Add additional form data
                data = additional_data or {}

                return self.post(url, files=files, data=data, **kwargs)

        except FileNotFoundError:
            raise ValueError(f"File not found: {file_path}")

    def download_file(self, url: str, file_path: str, **kwargs) -> bool:
        """Download file from endpoint."""
        try:
            response = self.get(url, **kwargs)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                f.write(response.content)

            logger.info(
                f"Downloaded file: {file_path}", url=url, size=len(response.content)
            )
            return True

        except Exception as e:
            logger.error(f"Failed to download file: {e}", url=url, file_path=file_path)
            return False

    def paginate(
        self,
        url: str,
        page_param: str = "page",
        size_param: str = "size",
        page_size: int = 100,
        max_pages: Optional[int] = None,
        **kwargs,
    ) -> List[APIResponse]:
        """Paginate through API responses."""
        responses = []
        page = 1

        while True:
            if max_pages and page > max_pages:
                break

            # Add pagination parameters
            params = kwargs.get("params", {}).copy()
            params[page_param] = page
            params[size_param] = page_size

            request_kwargs = kwargs.copy()
            request_kwargs["params"] = params

            try:
                response = self.get(url, **request_kwargs)
                response.raise_for_status()
                responses.append(response)

                # Check if there are more pages
                json_data = response.json()

                # Common pagination patterns
                if isinstance(json_data, dict):
                    # Check for 'has_more', 'next', or empty results
                    if (
                        json_data.get("has_more") is False
                        or json_data.get("next") is None
                        or not json_data.get("data", json_data.get("results", []))
                    ):
                        break
                elif isinstance(json_data, list) and len(json_data) < page_size:
                    # If we get fewer results than page size, we're done
                    break

                page += 1

            except Exception as e:
                logger.error(f"Pagination failed at page {page}: {e}")
                break

        logger.info(f"Paginated through {len(responses)} pages", url=url)
        return responses

    def set_auth(self, auth: Authentication) -> None:
        """Set authentication method."""
        self.auth = auth
        logger.info(f"Set authentication: {auth.__class__.__name__}")

    def set_base_url(self, base_url: str) -> None:
        """Set base URL."""
        self.base_url = base_url.rstrip("/")
        logger.info(f"Set base URL: {base_url}")

    def add_default_header(self, name: str, value: str) -> None:
        """Add default header."""
        self.default_headers[name] = value
        logger.debug(f"Added default header: {name}")

    def remove_default_header(self, name: str) -> None:
        """Remove default header."""
        if name in self.default_headers:
            del self.default_headers[name]
            logger.debug(f"Removed default header: {name}")

    def close(self) -> None:
        """Close HTTP client."""
        self.client.close()
        logger.info("Closed API client")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class AsyncAPIClient:
    """
    Async version of APIClient for high-performance applications.
    """

    def __init__(self, **kwargs):
        # Similar to APIClient but with async httpx client
        self.config = kwargs
        self.client = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(**self.config)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()


# Convenience functions
def create_client(
    base_url: str = "",
    auth_token: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs,
) -> APIClient:
    """
    Create API client with common authentication patterns.

    Args:
        base_url: Base URL for API
        auth_token: Bearer token for authentication
        api_key: API key for authentication
        **kwargs: Additional APIClient parameters

    Returns:
        Configured APIClient instance
    """
    auth = None

    if auth_token:
        auth = BearerTokenAuth(auth_token)
    elif api_key:
        auth = APIKeyAuth(api_key)

    return APIClient(base_url=base_url, auth=auth, **kwargs)


def quick_get(url: str, **kwargs) -> APIResponse:
    """Quick GET request without client setup."""
    with APIClient() as client:
        return client.get(url, **kwargs)


def quick_post(
    url: str, json_data: Optional[Dict[str, Any]] = None, **kwargs
) -> APIResponse:
    """Quick POST request without client setup."""
    with APIClient() as client:
        return client.post(url, json_data=json_data, **kwargs)
