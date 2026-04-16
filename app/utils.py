from fastapi import Request
from sqlalchemy.orm import Session


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
            '<a href="/admin/usuarios" class="lm-nav-logout">Usuarios</a>'
            '<a href="/admin/config" class="lm-nav-logout">Config</a>'
            if username == "admin"
            else ""
        )
        auth_block = (
            f'<div class="lm-nav-user">'
            f'<span class="lm-nav-username">{username}</span>'
            f'{admin_link}'
            f'<a href="/logout" class="lm-nav-logout">Salir</a>'
            f'</div>'
        )
        return auth_block, ""
    return '<a href="/login" class="lm-btn-login">Iniciar sesión</a>', "display:none"
