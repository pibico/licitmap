// Mapeo nombre GeoJSON → comunidad_autonoma en BD
const CCAA_MAP = {
    'Castilla-Leon':     'Castilla y León',
    'Cataluña':          'Cataluña',
    'Ceuta':             'Ciudad Autónoma de Ceuta',
    'Murcia':            'Región de Murcia',
    'La Rioja':          'La Rioja',
    'Baleares':          'Illes Balears',
    'Canarias':          'Canarias',
    'Cantabria':         'Cantabria',
    'Andalucia':         'Andalucía',
    'Asturias':          'Principado de Asturias',
    'Valencia':          'Comunidad Valenciana',
    'Melilla':           'Ciudad Autónoma de Melilla',
    'Navarra':           'Comunidad Foral de Navarra',
    'Galicia':           'Galicia',
    'Aragon':            'Aragón',
    'Madrid':            'Comunidad de Madrid',
    'Extremadura':       'Extremadura',
    'Castilla-La Mancha':'Castilla-La Mancha',
    'Pais Vasco':        'País Vasco',
};

// ─── Estado de filtros ────────────────────────────────────────────────────
const filtros = {
    q:           document.getElementById('mapa-q')?.value || '',
    tipo:        new Set(),
    estado:      new Set(),
    prange:      new Set(),
    fecha_desde: document.getElementById('mapa-fecha-desde')?.value || '',
    fecha_hasta: document.getElementById('mapa-fecha-hasta')?.value || '',
};

document.querySelectorAll('.lm-check-item.lm-active').forEach(el => {
    const g = el.dataset.group, v = el.dataset.value;
    if (g && v && filtros[g] instanceof Set) filtros[g].add(v);
});

function buildParams(extra) {
    const p = new URLSearchParams();
    if (filtros.q)            p.set('q', filtros.q);
    if (filtros.tipo?.size)   p.set('tipo',   [...filtros.tipo].join('|'));
    if (filtros.estado?.size) p.set('estado', [...filtros.estado].join('|'));
    if (filtros.prange?.size) p.set('prange', [...filtros.prange].join('|'));
    if (filtros.fecha_desde)  p.set('fecha_desde', filtros.fecha_desde);
    if (filtros.fecha_hasta)  p.set('fecha_hasta', filtros.fecha_hasta);
    if (extra) Object.entries(extra).forEach(([k, v]) => { if (v) p.set(k, v); else p.delete(k); });
    return p;
}

function seccionesActivas() {
    const secs = [];
    if (filtros.tipo?.size)   secs.push('tipo');
    if (filtros.estado?.size) secs.push('estado');
    if (filtros.prange?.size) secs.push('prange');
    if (filtros.fecha_desde || filtros.fecha_hasta) secs.push('fecha');
    secs.push('territorio', 'ccaa');
    return secs;
}

// ─── Mapa ─────────────────────────────────────────────────────────────────
const isDark = () => document.documentElement.getAttribute('data-theme') === 'dark';

function tileUrl() {
    return isDark()
        ? 'https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png'
        : 'https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png';
}

const map = L.map('mapa-leaflet', {
    center: [40.4, -3.7], zoom: 5,
    zoomControl: true, attributionControl: false,
});
let tileLayer = L.tileLayer(tileUrl(), { maxZoom: 12 }).addTo(map);

function getColor(n, max) {
    if (!n) return isDark() ? '#2a2e38' : '#e8e8ec';
    const t = Math.sqrt(n / max);
    if (isDark()) {
        return `rgb(${Math.round(2+t*10)},${Math.round(60+t*151)},${Math.round(80+t*73)})`;
    }
    return `rgb(${Math.round(236-t*181)},${Math.round(253-t*93)},${Math.round(245-t*176)})`;
}

let geojsonLayer = null;
let conteos = {};
let maxConteo = 1;
let geojsonCache = null;

function getDbName(feature) {
    return CCAA_MAP[feature.properties.name] || feature.properties.name;
}

function onEachFeature(feature, layer) {
    const dbName = getDbName(feature);

    layer.on('mouseover', function() {
        this.setStyle({ weight: 2, color: isDark() ? '#34d399' : '#059669' });
        const n = conteos[dbName] || 0;
        this._tt = L.tooltip({ sticky: true, className: 'lm-map-tooltip' })
            .setContent(`<strong>${dbName}</strong><br>${n.toLocaleString('es')} licitaciones`)
            .addTo(map);
    });
    layer.on('mousemove', function(e) {
        if (this._tt) this._tt.setLatLng(e.latlng);
    });
    layer.on('mouseout', function() {
        geojsonLayer.resetStyle(this);
        if (this._tt) { map.removeLayer(this._tt); this._tt = null; }
    });
    layer.on('click', function() {
        const secs = seccionesActivas();
        const params = buildParams({ pais: 'España', ccaa: dbName, open: secs.join(',') });
        window.location.href = '/?' + params.toString();
    });
}

async function renderMapa() {
    const [geojson, conteosData] = await Promise.all([
        geojsonCache
            ? Promise.resolve(geojsonCache)
            : fetch('/static/data/ccaa.geojson').then(r => r.json()).then(d => { geojsonCache = d; return d; }),
        fetch('/api/mapa?' + buildParams().toString()).then(r => r.json()),
    ]);

    conteos = conteosData;
    maxConteo = Math.max(1, ...Object.values(conteos));

    if (geojsonLayer) { map.removeLayer(geojsonLayer); geojsonLayer = null; }

    geojsonLayer = L.geoJSON(geojson, {
        style: f => ({
            fillColor: getColor(conteos[getDbName(f)] || 0, maxConteo),
            fillOpacity: 0.85,
            color: isDark() ? '#3a3f52' : '#c8c8d0',
            weight: 1,
        }),
        onEachFeature,
    }).addTo(map);

    map.fitBounds([[27, -18], [44, 5]], { padding: [10, 10] });
    actualizarStats();
    actualizarLeyenda();
}

function actualizarStats() {
    const total = Object.values(conteos).reduce((a, b) => a + b, 0);
    const el = document.getElementById('mapa-total');
    if (el) el.textContent = total.toLocaleString('es');
}

function actualizarLeyenda() {
    const legend = document.getElementById('mapa-legend');
    if (!legend) return;
    const steps = [0, 0.25, 0.5, 0.75, 1];
    legend.innerHTML = '<span class="lm-legend-label">Licitaciones:</span>'
        + steps.map(t => `<span class="lm-legend-item">
            <span class="lm-legend-dot" style="background:${getColor(t * maxConteo, maxConteo)}"></span>
            ${Math.round(t * t * maxConteo).toLocaleString('es')}
        </span>`).join('');
}

function actualizarUrl() {
    const p = buildParams();
    history.replaceState(null, '', '/mapa' + (p.toString() ? '?' + p.toString() : ''));
}

// ─── Sidebar: checkboxes ──────────────────────────────────────────────────
document.querySelectorAll('.lm-check-item').forEach(el => {
    el.addEventListener('click', () => {
        const g = el.dataset.group, v = el.dataset.value;
        if (!g || !v) return;
        if (!filtros[g]) filtros[g] = new Set();
        if (filtros[g].has(v)) { filtros[g].delete(v); el.classList.remove('lm-active'); }
        else                   { filtros[g].add(v);    el.classList.add('lm-active'); }
        actualizarUrl();
        renderMapa();
    });
});

let debounceTimer;
document.getElementById('mapa-q')?.addEventListener('input', e => {
    filtros.q = e.target.value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => { actualizarUrl(); renderMapa(); }, 400);
});
document.getElementById('mapa-fecha-desde')?.addEventListener('change', e => {
    filtros.fecha_desde = e.target.value; actualizarUrl(); renderMapa();
});
document.getElementById('mapa-fecha-hasta')?.addEventListener('change', e => {
    filtros.fecha_hasta = e.target.value; actualizarUrl(); renderMapa();
});

// ─── Sidebar toggles ──────────────────────────────────────────────────────
document.querySelectorAll('.lm-sidebar-toggle[data-section]').forEach(btn => {
    const body = document.getElementById('sc-' + btn.dataset.section);
    if (!body) return;
    btn.addEventListener('click', () => {
        const open = btn.classList.toggle('open');
        body.classList.toggle('open', open);
    });
});

// ─── Reaccionar al cambio de tema ─────────────────────────────────────────
new MutationObserver(() => {
    tileLayer.setUrl(tileUrl());
    if (geojsonLayer) geojsonLayer.setStyle(f => ({
        fillColor: getColor(conteos[getDbName(f)] || 0, maxConteo),
        fillOpacity: 0.85,
        color: isDark() ? '#3a3f52' : '#c8c8d0',
        weight: 1,
    }));
    actualizarLeyenda();
}).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

// ─── Arrancar ─────────────────────────────────────────────────────────────
renderMapa();
