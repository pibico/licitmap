from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.i18n import SUPPORTED, DEFAULT_LANG
from app.models import User

router = APIRouter()


@router.get("/lang/{lang}")
@router.post("/lang/{lang}")
def set_language(lang: str, request: Request, db: Session = Depends(get_db)):
    lang = lang.lower()
    if lang not in SUPPORTED:
        lang = DEFAULT_LANG

    redirect_to = request.headers.get("referer") or "/"
    response = RedirectResponse(redirect_to, status_code=303)
    # Un año; sin Secure para que funcione en desarrollo sin TLS
    response.set_cookie(
        "lm_lang", lang, max_age=60 * 60 * 24 * 365, httponly=False, samesite="lax"
    )

    username = request.session.get("username")
    if username:
        user = db.query(User).filter_by(username=username).first()
        if user:
            user.language = lang
            db.commit()

    return response
