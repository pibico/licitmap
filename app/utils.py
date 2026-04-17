from fastapi import Request
from sqlalchemy.orm import Session

_ICON_USER = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24"'
    ' stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'
)
_ICON_SHIELD = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24"'
    ' stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'
)
_ICON_LOGOUT = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24"'
    ' stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>'
    '<polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>'
)


def get_setting(db: Session, key: str, default: str = "") -> str:
    from app.models import Setting
    row = db.query(Setting).filter_by(key=key).first()
    return row.value if row else default


def set_setting(db: Session, key: str, value: str) -> None:
    from app.models import Setting
    row = db.query(Setting).filter_by(key=key).first()
    if row:
        row.value = value
    else:
        db.add(Setting(key=key, value=value))
    db.commit()


def _nav_context(request: Request) -> tuple[str, str]:
    """Devuelve (nav_auth_block_html, nav_busqueda_display_style)."""
    username = request.session.get("username", "")
    if username:
        admin_link = (
            f'<a href="/admin" class="lm-nav-admin-btn">{_ICON_SHIELD}Admin</a>'
            f'<span class="lm-nav-sep"></span>'
            if username == "admin"
            else ""
        )
        auth_block = (
            f'<div class="lm-nav-user">'
            f'<span class="lm-nav-username">{_ICON_USER}{username}</span>'
            f'{admin_link}'
            f'<a href="/logout" class="lm-nav-logout">{_ICON_LOGOUT}Salir</a>'
            f'</div>'
        )
        return auth_block, ""
    return '<a href="/login" class="lm-btn-login">Iniciar sesión</a>', "display:none"
