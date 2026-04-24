"""Redirects 301 from legacy Spanish URLs to the English ones."""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter()

_REDIRECTS = {
    "/mapa": "/map",
    "/analisis": "/analytics",
    "/alertas": "/alerts",
    "/admin/usuarios": "/admin/users",
    "/admin/config": "/admin/settings",
    "/admin/config/exportacion": "/admin/settings/export",
    "/admin/config/correo": "/admin/settings/email",
    "/admin/config/seguridad": "/admin/settings/security",
}


def _make_redirect(new_prefix: str):
    async def handler(request: Request, rest: str = ""):
        target = new_prefix + ("/" + rest if rest else "")
        qs = request.url.query
        if qs:
            target = f"{target}?{qs}"
        return RedirectResponse(target, status_code=301)
    return handler


for old_prefix, new_prefix in _REDIRECTS.items():
    router.add_api_route(
        old_prefix,
        _make_redirect(new_prefix),
        methods=["GET", "POST"],
        include_in_schema=False,
    )
    router.add_api_route(
        old_prefix + "/{rest:path}",
        _make_redirect(new_prefix),
        methods=["GET", "POST"],
        include_in_schema=False,
    )


# API redirects
@router.api_route("/api/alertas/{rest:path}", methods=["GET", "POST"], include_in_schema=False)
async def _api_alertas(rest: str, request: Request):
    qs = request.url.query
    target = f"/api/alerts/{rest}" + (f"?{qs}" if qs else "")
    return RedirectResponse(target, status_code=307)  # preserve method


@router.api_route("/api/mapa/{rest:path}", methods=["GET", "POST"], include_in_schema=False)
async def _api_mapa(rest: str, request: Request):
    qs = request.url.query
    target = f"/api/map/{rest}" + (f"?{qs}" if qs else "")
    return RedirectResponse(target, status_code=307)


@router.api_route("/api/analisis/{rest:path}", methods=["GET", "POST"], include_in_schema=False)
async def _api_analisis(rest: str, request: Request):
    qs = request.url.query
    target = f"/api/analytics/{rest}" + (f"?{qs}" if qs else "")
    return RedirectResponse(target, status_code=307)
