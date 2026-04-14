# LicitMap — contexto de proyecto

## Reglas críticas de desarrollo
- **Templates**: usar `Path("templates/X.html").read_text()` + `str.replace("{{key}}", value)`. NO usar `Jinja2Templates` — bug con Python 3.13+.
- **Estáticos**: incrementar `?v=N` en `<script>`/`<link>` de `base.html`/`mapa.html` cada vez que se toque CSS o JS.
- **Commits**: sin `Co-Authored-By`. Solo el usuario como autor.

## Comandos frecuentes
```bash
cd /root/licitmap && source .venv/bin/activate
supervisorctl restart licitmap
docker exec licitmap-db psql -U licitmap -c "SELECT count(*) FROM licitaciones;"
```

## Documentación completa
Ver `.planning/PROJECT.md` — modelo de datos, filtros, AJAX, mapa, infraestructura.
