import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger("jevflow.jev_client")


class TypeSafeError(Exception):
    """Base exception for TypeSafe Jev client errors."""
    pass


class TypeSafeAuthError(TypeSafeError):
    """Raised when authentication fails (HTTP 401)."""
    pass


class TypeSafeValidationError(TypeSafeError):
    """Raised when request fails schema validation (HTTP 422)."""
    pass


class TypeSafeTimeoutError(TypeSafeError):
    """Raised when the Jev evaluation times out."""
    pass


class TypeSafeAPIError(TypeSafeError):
    """Raised when upstream Jev API returns a 5xx error or unexpected status."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(f"TypeSafe API Error ({status_code}): {detail}")
        self.status_code = status_code
        self.detail = detail


class TypeSafeJevClient:
    """
    Official asynchronous client for TypeSafe Jev System One API.
    
    Adheres strictly to the official OpenAPI 3.1 contract:
    - POST /v1/systemone
    - GET /v1/models
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_ms: int = 2500,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key
        if self.api_key and (self.api_key.startswith("sk-or-") or "openrouter.ai" in (base_url or "")):
            self.base_url = (base_url or "https://openrouter.ai/api/alpha/decisions").rstrip("/")
        else:
            self.base_url = (base_url or "https://api.typesafe.ai").rstrip("/")
        self.timeout = httpx.Timeout(timeout_ms / 1000.0)
        self._custom_client = http_client

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise TypeSafeAuthError("API Key is not configured. Set OPENROUTER_API_KEY or TYPESAFE_API_KEY in .env.")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "JevFlow-Gateway/0.1.0",
        }
        if "openrouter.ai" in self.base_url or (self.api_key and self.api_key.startswith("sk-or-")):
            headers["HTTP-Referer"] = "https://github.com/tusharkkp/JevFlow"
            headers["X-Title"] = "JevFlow Gateway"
        return headers

    async def _execute_http(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        headers: Dict[str, str],
        json_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            if method == "GET":
                response = await client.get(url, headers=headers)
            else:
                response = await client.post(url, headers=headers, json=json_payload)
        except httpx.TimeoutException as exc:
            raise TypeSafeTimeoutError(f"Request to {url} timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise TypeSafeAPIError(500, f"Network error connecting to {url}: {exc}") from exc

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise TypeSafeAuthError("Invalid or missing TypeSafe API key.")
        elif response.status_code == 422:
            raise TypeSafeValidationError(f"Invalid System One request schema: {response.text}")
        else:
            raise TypeSafeAPIError(response.status_code, response.text)

    async def get_models(self) -> Dict[str, Any]:
        """Fetch available models and aliases from GET /v1/models."""
        headers = self._get_headers()
        url = f"{self.base_url}/v1/models"

        if self._custom_client is not None:
            return await self._execute_http(self._custom_client, "GET", url, headers)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await self._execute_http(client, "GET", url, headers)

    async def evaluate_system_one(
        self,
        state: Any,
        questions: Dict[str, Any],
        model: str = "jev-latest",
    ) -> Dict[str, Any]:
        """
        Send a multi-question evaluation to POST /v1/systemone or OpenRouter /api/alpha/decisions.
        
        Args:
            state: The content all questions refer to (string, dict, or list).
            questions: Dict of typed question objects keyed by question identifier.
            model: Model name or alias (e.g. 'jev-latest' or 'typesafe/jev-1.13').
            
        Returns:
            Dict containing 'model', 'answers', and 'usage'.
        """
        headers = self._get_headers()
        is_openrouter = "openrouter.ai" in self.base_url or (self.api_key and self.api_key.startswith("sk-or-"))
        if is_openrouter:
            url = f"{self.base_url}/api/alpha/decisions" if not self.base_url.endswith("/decisions") else self.base_url
            target_model = "typesafe/jev-1.13" if model in ("jev-latest", "typesafe/jev-1.13") else model
        else:
            url = f"{self.base_url}/v1/systemone"
            target_model = model

        payload = {
            "model": target_model,
            "state": state,
            "questions": questions,
        }

        if self._custom_client is not None:
            return await self._execute_http(self._custom_client, "POST", url, headers, payload)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await self._execute_http(client, "POST", url, headers, payload)
