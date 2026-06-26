import httpx

_client = None

def get_http_client() -> httpx.AsyncClient:
    """Returns a singleton shared httpx.AsyncClient for connection pooling."""
    global _client
    if _client is None:
        # Standard limits for pooling
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=30)
        _client = httpx.AsyncClient(limits=limits)
    return _client

async def close_http_client():
    """Closes the shared http client connection pool on app shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
