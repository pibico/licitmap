// Mapeo nombre GeoJSON CCAA → comunidad_autonoma en BD
const CCAA_MAP = {
    'Castilla-Leon':      'Castilla y León',
    'Cataluña':           'Cataluña',
    'Ceuta':              'Ciudad Autónoma de Ceuta',
    'Murcia':             'Región de Murcia',
    'La Rioja':           'La Rioja',
    'Baleares':           'Illes Balears',
    'Canarias':           'Canarias',
    'Cantabria':          'Cantabria',
    'Andalucia':          'Andalucía',
    'Asturias':           'Principado de Asturias',
    'Valencia':           'Comunidad Valenciana',
    'Melilla':            'Ciudad Autónoma de Melilla',
    'Navarra':            'Comunidad Foral de Navarra',
    'Galicia':            'Galicia',
    'Aragon':             'Aragón',
    'Madrid':             'Comunidad de Madrid',
    'Extremadura':        'Extremadura',
    'Castilla-La Mancha': 'Castilla-La Mancha',
    'Pais Vasco':         'País Vasco',
};

// ─── Estado de filtros ────────────────────────────────────────────────────
const filtros = {
    q:           document.getElementById('mapa-q')?.value || '',
    cpv_q:       document.getElementById('mapa-cpv-q')?.value || '',
    tipo:        new Set(),
    estado:      new Set(),
    prange:      new Set(),
    ccaa:        new Set(),
    fecha_desde: document.getElementById('mapa-fecha-desde')?.value || '',
    fecha_hasta: document.getElementById('mapa-fecha-hasta')?.value || '',
    provincia:   '',
    municipio:   '',
};

document.querySelectorAll('.lm-check-item.lm-active').forEach(el => {
    const g = el.dataset.group, v = el.dataset.value;
    if (g && v && filtros[g] instanceof Set) filtros[g].add(v);
});

function buildParams(extra) {
    const p = new URLSearchParams();
    if (filtros.q)            p.set('q', filtros.q);
    if (filtros.cpv_q)        p.set('cpv_q', filtros.cpv_q);
    if (filtros.tipo?.size)   p.set('tipo',   [...filtros.tipo].join('|'));
    if (filtros.estado?.size) p.set('estado', [...filtros.estado].join('|'));
    if (filtros.prange?.size) p.set('prange', [...filtros.prange].join('|'));
    if (filtros.ccaa?.size)   p.set('ccaa',   [...filtros.ccaa].join('|'));
    if (filtros.fecha_desde)  p.set('fecha_desde', filtros.fecha_desde);
    if (filtros.fecha_hasta)  p.set('fecha_hasta', filtros.fecha_hasta);
    if (filtros.provincia)    p.set('provincia', filtros.provincia);
    if (filtros.municipio)    p.set('municipio', filtros.municipio);
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
let tileLayer = L.tileLayer(tileUrl(), { maxZoom: 13 }).addTo(map);

// Tooltip único compartido — evita acumulación de tooltips stuck durante drag
const sharedTooltip = L.tooltip({ className: 'lm-map-tooltip lm-tt-card', opacity: 1 });

// ─── Colores coropleta ────────────────────────────────────────────────────
function getColor(n, max) {
    if (!n) return isDark() ? '#2a2e38' : '#e8e8ec';
    const t = Math.sqrt(n / max);
    if (isDark()) {
        return `rgb(${Math.round(2 + t * 10)},${Math.round(60 + t * 151)},${Math.round(80 + t * 73)})`;
    }
    return `rgb(${Math.round(236 - t * 181)},${Math.round(253 - t * 93)},${Math.round(245 - t * 176)})`;
}

function baseStyle(fillColor) {
    return { fillColor, fillOpacity: 0.82, color: isDark() ? '#3a3f52' : '#c0c0cc', weight: 0.8 };
}
function hoverStyle() {
    return { weight: 2.5, color: isDark() ? '#34d399' : '#059669', fillOpacity: 0.92 };
}

// ─── Capas y cachés ───────────────────────────────────────────────────────
const layers   = { ccaa: null, provincias: null, municipios: null };
const conteos  = { ccaa: {}, provincias: {}, municipios: {} };
const maxC     = { ccaa: 1,   provincias: 1,   municipios: 1 };
const geojsons = { ccaa: null, provincias: null, municipios: null };

// Caché de respuestas API (evita refetch al volver al mismo nivel)
const apiCache = { ccaa: null, provincias: null, municipios: null };
const apiCacheTs = { ccaa: 0, provincias: 0, municipios: 0 };
const API_CACHE_TTL = 30000; // 30 s

let nivelActual = null;
let nivelFijado = null;   // null = Auto; 'ccaa' | 'provincias' | 'municipios' = fijado
let renderPending = false;
let renderQueued  = false;

function nivelEfectivo() {
    return nivelFijado || nivelParaZoom(map.getZoom());
}

// ─── Helpers nombre ───────────────────────────────────────────────────────
const getNameCCAA      = f => CCAA_MAP[f.properties.name] || f.properties.name;
const getNameProvincia = f => f.properties.Texto || f.properties.name || '';

function getDatosPorFeature(nivel, feature) {
    let entry;
    if (nivel === 'ccaa')       entry = conteos.ccaa[getNameCCAA(feature)];
    else if (nivel === 'provincias') entry = conteos.provincias[getNameProvincia(feature)];
    else {
        const dbs = feature.properties.db_names || [];
        const total    = dbs.reduce((s, n) => s + (conteos.municipios[n]?.total    || 0), 0);
        const en_plazo = dbs.reduce((s, n) => s + (conteos.municipios[n]?.en_plazo || 0), 0);
        return { total, en_plazo };
    }
    return entry || { total: 0, en_plazo: 0 };
}

function getLabel(nivel, feature) {
    if (nivel === 'ccaa')       return getNameCCAA(feature);
    if (nivel === 'provincias') return getNameProvincia(feature);
    const name = feature.properties.name || '';
    return name.split('/')[0].split(' - ')[0].trim();
}

// ─── Tooltip rico ─────────────────────────────────────────────────────────
function buildTooltipHtml(label, datos) {
    const total    = (datos.total    || 0).toLocaleString('es');
    const en_plazo = (datos.en_plazo || 0).toLocaleString('es');
    return `
        <div class="lm-tt-title">${label}</div>
        <div class="lm-tt-row">
            <span class="lm-tt-label">Licitaciones</span>
            <span class="lm-tt-value">${total}</span>
        </div>
        <div class="lm-tt-row">
            <span class="lm-tt-label">En plazo</span>
            <span class="lm-tt-value lm-tt-accent">${en_plazo}</span>
        </div>`;
}

// ─── Construcción de capa GeoJSON ─────────────────────────────────────────
function buildLayer(nivel, geojson) {
    if (layers[nivel]) { map.removeLayer(layers[nivel]); layers[nivel] = null; }
    sharedTooltip.remove();
    hoveredFeatureLayer = null;

    layers[nivel] = L.geoJSON(geojson, {
        style: f => baseStyle(getColor(getDatosPorFeature(nivel, f).total, maxC[nivel])),
        onEachFeature(feature, layer) {
            layer.on('mouseover', function (e) {
                hoveredFeatureLayer = this;
                this.bringToFront();
                this.setStyle(hoverStyle());
                sharedTooltip
                    .setContent(buildTooltipHtml(getLabel(nivel, feature), getDatosPorFeature(nivel, feature)))
                    .setLatLng(e.latlng)
                    .addTo(map);
            });
            layer.on('mousemove', function (e) {
                sharedTooltip.setLatLng(e.latlng);
            });
            layer.on('mouseout', function () {
                hoveredFeatureLayer = null;
                sharedTooltip.remove();
                const lyr = layers[nivel];
                if (lyr) lyr.resetStyle(this);
            });
            layer.on('click', function () {
                if (nivel === 'ccaa') {
                    const ccaaName = getNameCCAA(feature);
                    const p = buildParams({ pais: 'España', ccaa: ccaaName, open: seccionesActivas().join(',') });
                    window.location.href = '/?' + p.toString();
                } else if (nivel === 'provincias') {
                    const provName = getNameProvincia(feature);
                    const secs = [...seccionesActivas(), 'provincia'];
                    const p = buildParams({ pais: 'España', provincia: provName, open: secs.join(',') });
                    window.location.href = '/?' + p.toString();
                } else {
                    const dbs = feature.properties.db_names || [];
                    const municipio = dbs[0] || feature.properties.name;
                    const p = buildParams({ pais: 'España', municipio, open: seccionesActivas().join(',') });
                    window.location.href = '/?' + p.toString();
                }
            });
        },
    }).addTo(map);
}

// ─── Fetch GeoJSON (caché permanente) ────────────────────────────────────
async function fetchGeoJSON(nivel) {
    if (geojsons[nivel]) return geojsons[nivel];
    const urls = {
        ccaa:       '/static/data/ccaa.geojson',
        provincias: '/static/data/provincias.geojson',
        municipios: '/static/data/municipios.geojson',
    };
    geojsons[nivel] = await fetch(urls[nivel]).then(r => r.json());
    return geojsons[nivel];
}

// ─── Fetch API (caché 30 s por nivel) ────────────────────────────────────
async function fetchApi(nivel) {
    const params = buildParams().toString();
    const cacheKey = nivel + '|' + params;
    const now = Date.now();
    if (apiCache[nivel]?.key === cacheKey && now - apiCacheTs[nivel] < API_CACHE_TTL) {
        return apiCache[nivel].data;
    }
    const urls = {
        ccaa:       '/api/mapa',
        provincias: '/api/mapa/provincias',
        municipios: '/api/mapa/municipios',
    };
    const data = await fetch(urls[nivel] + '?' + params).then(r => r.json());
    apiCache[nivel] = { key: cacheKey, data };
    apiCacheTs[nivel] = now;
    return data;
}

// ─── Zoom → nivel ─────────────────────────────────────────────────────────
function nivelParaZoom(zoom) {
    if (zoom >= 9) return 'municipios';
    if (zoom >= 7) return 'provincias';
    return 'ccaa';
}

// ─── Render principal ─────────────────────────────────────────────────────
async function renderMapa() {
    if (renderPending) { renderQueued = true; return; }
    renderPending = true;
    renderQueued  = false;
    try {
        const nivel = nivelEfectivo();

        // Fetch en paralelo: GeoJSON (probablemente ya en caché) + API
        const [geojson, apiData] = await Promise.all([fetchGeoJSON(nivel), fetchApi(nivel)]);

        if (nivel === 'ccaa') {
            conteos.ccaa = apiData.ccaa || {};
            maxC.ccaa    = Math.max(1, ...Object.values(conteos.ccaa).map(v => v.total || 0));
            actualizarStats(apiData);
        } else if (nivel === 'provincias') {
            conteos.provincias = apiData.provincias || {};
            maxC.provincias    = Math.max(1, ...Object.values(conteos.provincias).map(v => v.total || 0));
        } else {
            conteos.municipios = apiData.municipios || {};
            maxC.municipios    = Math.max(1, ...Object.values(conteos.municipios).map(v => v.total || 0));
        }

        // Eliminar capas de otros niveles
        for (const n of ['ccaa', 'provincias', 'municipios']) {
            if (n !== nivel && layers[n]) { map.removeLayer(layers[n]); layers[n] = null; }
        }
        buildLayer(nivel, geojson);

        nivelActual = nivel;
        actualizarLeyenda(conteos[nivel], maxC[nivel]);
        actualizarIndicadorNivel();
        actualizarUrl();
    } finally {
        renderPending = false;
        if (renderQueued) { renderQueued = false; renderMapa(); }
    }
}

// ─── Limpiar artefactos al arrastrar ─────────────────────────────────────
// dragstart solo se dispara en drag del usuario (no en fitBounds/flyTo)
let hoveredFeatureLayer = null;

map.on('dragstart', () => {
    sharedTooltip.remove();
    if (hoveredFeatureLayer) {
        const lyr = layers[nivelActual];
        if (lyr) lyr.resetStyle(hoveredFeatureLayer);
        hoveredFeatureLayer = null;
    }
});

// ─── Zoom switching ───────────────────────────────────────────────────────
let zoomTimer = null;
map.on('zoomend', () => {
    clearTimeout(zoomTimer);
    zoomTimer = setTimeout(async () => {
        if (!nivelFijado) {
            const nuevo = nivelParaZoom(map.getZoom());
            if (nuevo !== nivelActual) await renderMapa();
        }
        actualizarIndicadorNivel();
        actualizarUrl();
    }, 120);
});

// ─── Stats y leyenda ──────────────────────────────────────────────────────
function actualizarStats(apiData) {
    const enPlazo    = document.getElementById('mapa-en-plazo');
    const resultados = document.getElementById('mapa-resultados');
    if (apiData?.en_plazo   != null && enPlazo)    enPlazo.textContent   = apiData.en_plazo;
    if (apiData?.resultados != null && resultados) resultados.textContent = apiData.resultados;
}

function actualizarLeyenda(cnt, max) {
    const legend = document.getElementById('mapa-legend');
    if (!legend) return;
    const steps = [0, 0.25, 0.5, 0.75, 1];
    legend.innerHTML = '<span class="lm-legend-label">Licitaciones:</span>'
        + steps.map(t => `<span class="lm-legend-item">
            <span class="lm-legend-dot" style="background:${getColor(t * max, max)}"></span>
            ${Math.round(t * t * max).toLocaleString('es')}
        </span>`).join('');
}

function actualizarIndicadorNivel() {
    const activo = nivelFijado || 'auto';
    document.querySelectorAll('#nivel-selector button').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.nivel === activo);
    });
}

function actualizarUrl() {
    const p = buildParams();
    history.replaceState(null, '', '/mapa' + (p.toString() ? '?' + p.toString() : ''));
}

// ─── Autocomplete ─────────────────────────────────────────────────────────
function stripAccents(s) {
    return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function setupAutocomplete(inputId, listId, getOptions, onSelect) {
    const input = document.getElementById(inputId);
    const list  = document.getElementById(listId);
    if (!input || !list) return;
    list.style.position = 'fixed';
    list.style.zIndex   = '9999';

    let activeIdx = -1;

    function updatePos() {
        const r = input.getBoundingClientRect();
        list.style.top = r.bottom + 'px'; list.style.left = r.left + 'px'; list.style.width = r.width + 'px';
    }

    function showList(items) {
        if (!items.length) { list.classList.remove('open'); return; }
        list.innerHTML = items.slice(0, 10).map(item =>
            `<div class="lm-autocomplete-item" data-val="${item}">${item}</div>`
        ).join('');
        updatePos();
        list.classList.add('open');
        activeIdx = -1;
        list.querySelectorAll('.lm-autocomplete-item').forEach(el => {
            el.addEventListener('mousedown', e => {
                e.preventDefault();
                input.value = el.dataset.val;
                list.classList.remove('open');
                onSelect(el.dataset.val);
            });
        });
    }

    function setActive(idx) {
        const items = list.querySelectorAll('.lm-autocomplete-item');
        items.forEach(el => el.classList.remove('lm-ac-active'));
        if (idx >= 0 && idx < items.length) { items[idx].classList.add('lm-ac-active'); activeIdx = idx; }
    }

    input.addEventListener('input', () => {
        const val = stripAccents(input.value.trim());
        if (!val) { list.classList.remove('open'); onSelect(''); return; }
        const matches = getOptions().filter(o => stripAccents(o).includes(val));
        showList(matches);
    });

    input.addEventListener('keydown', e => {
        const items = list.querySelectorAll('.lm-autocomplete-item');
        if (e.key === 'ArrowDown')  { e.preventDefault(); setActive(Math.min(activeIdx + 1, items.length - 1)); }
        else if (e.key === 'ArrowUp')   { e.preventDefault(); setActive(Math.max(activeIdx - 1, 0)); }
        else if (e.key === 'Enter' && activeIdx >= 0 && items[activeIdx]) {
            input.value = items[activeIdx].dataset.val;
            list.classList.remove('open');
            onSelect(input.value);
        } else if (e.key === 'Escape') { list.classList.remove('open'); }
    });

    document.addEventListener('click', e => {
        if (!input.contains(e.target) && !list.contains(e.target)) list.classList.remove('open');
    });
}

// ─── Cargar nombres para autocomplete ────────────────────────────────────
let nombresProvincias = [];
let nombresMunicipios = [];

fetch('/api/mapa/nombres').then(r => r.json()).then(data => {
    nombresProvincias = data.provincias || [];
    nombresMunicipios = data.municipios || [];

    setupAutocomplete('mapa-provincia', 'mapa-provincia-list',
        () => nombresProvincias,
        val => { filtros.provincia = val; renderMapa(); }
    );
    setupAutocomplete('mapa-municipio', 'mapa-municipio-list',
        () => nombresMunicipios,
        val => { filtros.municipio = val; renderMapa(); }
    );
});

// ─── Sidebar: checkboxes e inputs ─────────────────────────────────────────
document.querySelectorAll('.lm-check-item').forEach(el => {
    el.addEventListener('click', () => {
        const g = el.dataset.group, v = el.dataset.value;
        if (!g || !v) return;
        if (!filtros[g]) filtros[g] = new Set();
        if (filtros[g].has(v)) { filtros[g].delete(v); el.classList.remove('lm-active'); }
        else                   { filtros[g].add(v);    el.classList.add('lm-active'); }
        saveLMFilters(); actualizarUrl(); renderMapa();
    });
});

let debounceTimer;
['mapa-q', 'mapa-cpv-q'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', e => {
        filtros[id === 'mapa-q' ? 'q' : 'cpv_q'] = e.target.value;
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => { saveLMFilters(); actualizarUrl(); renderMapa(); }, 400);
    });
});
document.getElementById('mapa-fecha-desde')?.addEventListener('change', e => {
    filtros.fecha_desde = e.target.value; saveLMFilters(); actualizarUrl(); renderMapa();
});
document.getElementById('mapa-fecha-hasta')?.addEventListener('change', e => {
    filtros.fecha_hasta = e.target.value; saveLMFilters(); actualizarUrl(); renderMapa();
});

// ─── Cambio de tema ───────────────────────────────────────────────────────
new MutationObserver(() => {
    tileLayer.setUrl(tileUrl());
    for (const nivel of ['ccaa', 'provincias', 'municipios']) {
        if (!layers[nivel]) continue;
        layers[nivel].setStyle(f => baseStyle(getColor(getDatosPorFeature(nivel, f).total, maxC[nivel])));
    }
    const n = nivelParaZoom(map.getZoom());
    actualizarLeyenda(conteos[n], maxC[n]);
}).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

// ─── Selector de nivel ────────────────────────────────────────────────────
document.querySelectorAll('#nivel-selector button').forEach(btn => {
    btn.addEventListener('click', () => {
        nivelFijado = btn.dataset.nivel === 'auto' ? null : btn.dataset.nivel;
        actualizarIndicadorNivel();
        renderMapa();
    });
});

// ─── LMFilters: guardar estado compartido ────────────────────────────────
function saveLMFilters() {
    if (typeof LMFilters === 'undefined') return;
    LMFilters.save({
        q: filtros.q, cpv_q: filtros.cpv_q,
        tipo:   [...filtros.tipo].join('|'),
        estado: [...filtros.estado].join('|'),
        prange: [...filtros.prange].join('|'),
        ccaa:   [...filtros.ccaa].join('|'),
        fecha_desde: filtros.fecha_desde, fecha_hasta: filtros.fecha_hasta,
        provincia: filtros.provincia, municipio: filtros.municipio,
    });
}

// ─── LMFilters: cargar al inicio si URL limpia ────────────────────────────
(function () {
    if (typeof LMFilters === 'undefined') return;
    const url = new URLSearchParams(window.location.search);
    const hasUrl = ['q','cpv_q','tipo','estado','prange','ccaa','fecha_desde','fecha_hasta','provincia','municipio'].some(k => url.get(k));
    if (hasUrl) return;
    const f = LMFilters.get();
    if (f.q)    { filtros.q = f.q;          const el = document.getElementById('mapa-q');       if (el) el.value = f.q; }
    if (f.cpv_q){ filtros.cpv_q = f.cpv_q;  const el = document.getElementById('mapa-cpv-q');   if (el) el.value = f.cpv_q; }
    ['tipo','estado','prange','ccaa'].forEach(key => {
        if (!f[key]) return;
        f[key].split('|').filter(Boolean).forEach(v => {
            filtros[key].add(v);
            const item = document.querySelector(`.lm-check-item[data-group="${key}"][data-value="${v}"]`);
            if (item) item.classList.add('lm-active');
        });
    });
    if (f.fecha_desde) { filtros.fecha_desde = f.fecha_desde; const el = document.getElementById('mapa-fecha-desde'); if(el) el.value = f.fecha_desde; }
    if (f.fecha_hasta) { filtros.fecha_hasta = f.fecha_hasta; const el = document.getElementById('mapa-fecha-hasta'); if(el) el.value = f.fecha_hasta; }
    if (f.provincia) filtros.provincia = f.provincia;
    if (f.municipio) filtros.municipio = f.municipio;
})();

// ─── Prefetch silencioso de los 3 GeoJSONs ───────────────────────────────
fetchGeoJSON('ccaa');
setTimeout(() => fetchGeoJSON('provincias'), 300);
setTimeout(() => fetchGeoJSON('municipios'), 1000);

// ─── Arrancar ─────────────────────────────────────────────────────────────
map.fitBounds([[27, -18], [44, 5]], { padding: [10, 10] });
renderMapa();
