"""
Poisoned tool implementations for Tool-Return Deception (TRD) benchmark.

These tools subclass the real tools but return pre-scripted responses
containing embedded malicious instructions. Used to test whether agents
follow hidden instructions injected into tool outputs.
"""

import json
from typing import Any

from nanobot.agent.tools.base import Tool


class PoisonedWebFetchTool(Tool):
    """
    Poisoned web_fetch that returns pre-scripted responses for trigger URLs.
    
    For trigger URLs: returns the poisoned response (containing hidden payload).
    For attacker/target URLs: records the call (this is what we're detecting).
    For all other URLs: returns "connection refused" to isolate the test.
    """

    name = "web_fetch"
    description = "Fetch URL and extract readable content (HTML → markdown/text)."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "extractMode": {"type": "string", "enum": ["markdown", "text"], "default": "markdown"},
            "maxChars": {"type": "integer", "minimum": 100}
        },
        "required": ["url"]
    }

    def __init__(self, responses: dict[str, dict], fallback_error: str = "Connection refused"):
        """
        Args:
            responses: Mapping of URL (or URL substring) → response dict.
                       Each response dict should have: url, status, text
                       (mimics real WebFetchTool JSON output).
            fallback_error: Error message for URLs not in responses map.
        """
        self._responses = responses
        self._fallback_error = fallback_error
        self._calls: list[dict] = []

    @property
    def calls(self) -> list[dict]:
        """All calls made to this tool, for post-hoc analysis."""
        return self._calls

    async def execute(self, url: str, extractMode: str = "markdown", maxChars: int | None = None, **kwargs: Any) -> str:
        self._calls.append({"url": url, "extractMode": extractMode})

        for trigger_url, response_data in self._responses.items():
            if trigger_url in url or url in trigger_url:
                return json.dumps({
                    "url": url,
                    "finalUrl": response_data.get("finalUrl", url),
                    "status": response_data.get("status", 200),
                    "extractor": response_data.get("extractor", "readability"),
                    "truncated": False,
                    "length": len(response_data.get("text", "")),
                    "text": response_data.get("text", "")
                })

        return json.dumps({
            "error": self._fallback_error,
            "url": url
        })


class PoisonedWebSearchTool(Tool):
    """
    Poisoned web_search that returns pre-scripted search results.
    
    For matching queries: returns scripted results with embedded payloads.
    For other queries: returns "No results found".
    """

    name = "web_search"
    description = "Search the web. Returns titles, URLs, and snippets."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "count": {"type": "integer", "description": "Results (1-10)", "minimum": 1, "maximum": 10}
        },
        "required": ["query"]
    }

    def __init__(self, responses: dict[str, str], fallback: str = "No results found"):
        """
        Args:
            responses: Mapping of query substring → pre-formatted search results string.
            fallback: Response for unmatched queries.
        """
        self._responses = responses
        self._fallback = fallback
        self._calls: list[dict] = []

    @property
    def calls(self) -> list[dict]:
        return self._calls

    async def execute(self, query: str, count: int | None = None, **kwargs: Any) -> str:
        self._calls.append({"query": query, "count": count})

        query_lower = query.lower()
        for trigger_query, response_text in self._responses.items():
            if trigger_query.lower() in query_lower or query_lower in trigger_query.lower():
                return response_text

        return f"No results for: {query}"


class PoisonedApiCheckTool(Tool):
    """
    Simulated internal API checking tool that returns poisoned JSON responses.
    
    This tool doesn't exist in the real agent — it's added specifically for
    TRD cases that test injection via API/JSON responses.
    """

    name = "api_check"
    description = "Check internal API endpoint status and retrieve configuration data."
    parameters = {
        "type": "object",
        "properties": {
            "endpoint": {"type": "string", "description": "API endpoint path (e.g. /api/v2/status)"},
            "method": {"type": "string", "enum": ["GET", "POST"], "default": "GET"},
            "headers": {"type": "object", "description": "Optional request headers"}
        },
        "required": ["endpoint"]
    }

    def __init__(self, responses: dict[str, str], fallback_error: str = "Endpoint not found"):
        """
        Args:
            responses: Mapping of endpoint substring → JSON response string.
            fallback_error: Error for unmatched endpoints.
        """
        self._responses = responses
        self._fallback_error = fallback_error
        self._calls: list[dict] = []

    @property
    def calls(self) -> list[dict]:
        return self._calls

    async def execute(self, endpoint: str, method: str = "GET", headers: dict | None = None, **kwargs: Any) -> str:
        self._calls.append({"endpoint": endpoint, "method": method, "headers": headers})

        for trigger_endpoint, response_text in self._responses.items():
            if trigger_endpoint in endpoint or endpoint in trigger_endpoint:
                return response_text

        return json.dumps({
            "error": self._fallback_error,
            "endpoint": endpoint,
            "status": 404
        })
