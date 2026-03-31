import asyncio
import logging
import os
import re
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("weather-mcp")

MCP_API_KEY = os.environ.get("MCP_API_KEY")


class ApiKeyMiddleware:
    """ASGI middleware that validates Bearer tokens against MCP_API_KEY."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        # Accept key via Bearer header or ?api_key= query param
        auth_header = request.headers.get("authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = request.query_params.get("api_key")

        if not token:
            response = JSONResponse(
                {"error": "unauthorized", "message": "Missing API key. Use Bearer header or ?api_key= query param."},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        if token != MCP_API_KEY:
            logger.warning("Invalid API key attempt")
            response = JSONResponse(
                {"error": "unauthorized", "message": "Invalid API key"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


mcp = FastMCP(
    "weather",
    stateless_http=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"
US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "VI", "GU", "AS", "MP",
}


MAX_RETRIES = 3
BACKOFF_BASE = 1  # seconds


async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with retries and exponential backoff."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
    async with httpx.AsyncClient() as client:
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", BACKOFF_BASE * (2 ** attempt)))
                    logger.warning("Rate limited on %s, retrying in %ds (attempt %d/%d)", url, retry_after, attempt + 1, MAX_RETRIES)
                    await asyncio.sleep(retry_after)
                    continue
                if response.status_code >= 500:
                    wait = BACKOFF_BASE * (2 ** attempt)
                    logger.warning("Server error %d on %s, retrying in %ds (attempt %d/%d)", response.status_code, url, wait, attempt + 1, MAX_RETRIES)
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException:
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning("Timeout on %s, retrying in %ds (attempt %d/%d)", url, wait, attempt + 1, MAX_RETRIES)
                await asyncio.sleep(wait)
                continue
            except httpx.HTTPStatusError as e:
                logger.error("HTTP %d from %s", e.response.status_code, url)
                return {"_error": f"http_{e.response.status_code}"}
            except Exception as e:
                logger.error("Unexpected error requesting %s: %s", url, e)
                return None

        logger.error("All %d retries exhausted for %s", MAX_RETRIES, url)
        return {"_error": "rate_limit"}


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get("event", "Unknown")}
Area: {props.get("areaDesc", "Unknown")}
Severity: {props.get("severity", "Unknown")}
Description: {props.get("description", "No description available")}
Instructions: {props.get("instruction", "No specific instructions provided")}
"""


@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    state = state.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", state):
        return f"Invalid state code '{state}'. Please provide a two-letter US state code (e.g. CA, NY)."
    if state not in US_STATE_CODES:
        return f"'{state}' is not a valid US state/territory code."

    logger.info("Fetching alerts for state=%s", state)
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if data and data.get("_error") == "rate_limit":
        return "The weather service is rate-limiting requests. Please try again in a few seconds."
    if data and data.get("_error") == "timeout":
        return "Request to weather service timed out. Please try again."
    if data and isinstance(data.get("_error"), str):
        return "Unable to fetch alerts due to a service error."

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    if not (-90 <= latitude <= 90):
        return f"Invalid latitude {latitude}. Must be between -90 and 90."
    if not (-180 <= longitude <= 180):
        return f"Invalid longitude {longitude}. Must be between -180 and 180."

    logger.info("Fetching forecast for lat=%s, lon=%s", latitude, longitude)
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if points_data and points_data.get("_error") == "rate_limit":
        return "The weather service is rate-limiting requests. Please try again in a few seconds."
    if points_data and points_data.get("_error") == "timeout":
        return "Request to weather service timed out. Please try again."
    if points_data and isinstance(points_data.get("_error"), str):
        return "Unable to fetch forecast. The NWS API only covers US locations."

    if not points_data:
        return "Unable to fetch forecast data for this location."

    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if forecast_data and isinstance(forecast_data.get("_error"), str):
        return "Unable to fetch detailed forecast due to a service error."

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:
        forecast = f"""
{period["name"]}:
Temperature: {period["temperature"]}°{period["temperatureUnit"]}
Wind: {period["windSpeed"]} {period["windDirection"]}
Forecast: {period["detailedForecast"]}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)


# ASGI app for Vercel — this is what Vercel's Python runtime serves
_starlette_app = mcp.streamable_http_app()

# Add API key auth middleware if MCP_API_KEY is configured
if MCP_API_KEY:
    _starlette_app.add_middleware(ApiKeyMiddleware)
else:
    logger.warning("MCP_API_KEY not set — server is running without authentication")

app = _starlette_app
