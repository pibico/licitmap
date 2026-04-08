from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app.models import Licitacion

router = APIRouter()


def render(template, **kwargs):
    base = Path("templates/base.html").read_text()
    page = Path(f"templates/{template}").read_text()
    html = base.replace("{{content}}", page)
    for key, value in kwargs.items():
        html = html.replace("{{" + key + "}}", str(value))
    return html


@router.get("/", response_class=HTMLResponse)
def home(db: Session = Depends(get_db)):
    licitaciones = db.query(Licitacion).order_by(Licitacion.fecha_publicacion.desc()).limit(100).all()
    total = db.query(Licitacion).count()

    filas = ""
    for lic in licitaciones:
        presupuesto = f"{lic.presupuesto:,.2f} €" if lic.presupuesto else "—"
        estado = lic.estado or "—"
        filas += f"""<tr>
            <td><a href="{lic.url}" target="_blank">{lic.expediente}</a></td>
            <td>{lic.titulo or '—'}</td>
            <td>{lic.organo_contratacion or '—'}</td>
            <td>{lic.comunidad_autonoma or '—'}</td>
            <td style="text-align:right">{presupuesto}</td>
            <td><span class="badge badge-{estado}">{estado}</span></td>
        </tr>"""

    return render("home.html", total=total, filas=filas)
