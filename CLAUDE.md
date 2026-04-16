# LicitMap — reglas de desarrollo

> Para arquitectura, modelo de datos, features, infraestructura y estado del proyecto: **consultar memoria** antes de actuar.

## Reglas críticas (siempre aplican)

- **Templates**: `Path("templates/X.html").read_text()` + `str.replace("{{key}}", value)`. **NO usar `Jinja2Templates`** — bug con Python 3.13+.
- **Estáticos**: incrementar `?v=N` en `<link>`/`<script>` de `base.html` cada vez que se modifique CSS o JS.
- **Commits**: sin `Co-Authored-By`. Solo el usuario como autor. Commit tras cada feature/fix.

## Comandos de operación

```bash
cd /root/licitmap && source .venv/bin/activate
supervisorctl restart licitmap
supervisorctl status licitmap
docker exec licitmap-db psql -U licitmap -c "SELECT count(*) FROM licitaciones;"
```
