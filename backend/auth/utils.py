from fastapi import Request

def get_external_base_url(request: Request) -> str:
    """
    Resolve the external base URL by checking for standard reverse proxy headers
    (like X-Forwarded-Proto and X-Forwarded-Host) sent by tunnels (e.g. localtunnel).
    """
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    return f"{proto}://{host}"
