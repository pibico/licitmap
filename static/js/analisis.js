(function () {
  'use strict';

  // ── Paleta desde CSS vars ─────────────────────────────────────────────────
  function css(v) {
    return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  }

  function palette() {
    return {
      ac:        css('--ac-main'),
      acSoft:    css('--ac-soft'),
      txMuted:   css('--tx-muted'),
      txPrimary: css('--tx-primary'),
      bgBase:    css('--bg-base'),
      bgMantle:  css('--bg-mantle'),
      series: [
        css('--ac-main'), css('--co-blue'), css('--co-mauve'), css('--co-yellow'),
        css('--co-red'),  css('--co-sky'),
        '#10b981','#f59e0b','#8b5cf6','#06b6d4','#84cc16','#f97316',
        '#a855f7','#14b8a6','#ef4444','#ec4899','#64748b','#22d3ee','#fb923c',
      ],
    };
  }

  // ── Formato ───────────────────────────────────────────────────────────────
  function fmtN(n) {
    if (n === null || n === undefined) return '—';
    return Number(n).toLocaleString('es-ES');
  }
  function fmtEur(n) {
    if (n === null || n === undefined) return '—';
    n = Number(n);
    if (n >= 1e9)  return (n / 1e9).toLocaleString('es-ES', {maximumFractionDigits: 2}) + ' MM€';
    if (n >= 1e6)  return (n / 1e6).toLocaleString('es-ES', {maximumFractionDigits: 2}) + ' M€';
    if (n >= 1e3)  return (n / 1e3).toLocaleString('es-ES', {maximumFractionDigits: 1}) + ' K€';
    return n.toLocaleString('es-ES', {maximumFractionDigits: 0}) + ' €';
  }
  function fmtPct(n) {
    if (n === null || n === undefined) return '—';
    return Number(n).toLocaleString('es-ES', {maximumFractionDigits: 1}) + '%';
  }

  // ── Chart.js ──────────────────────────────────────────────────────────────
  const _charts = {};

  function destroy(id) {
    if (_charts[id]) { _charts[id].destroy(); delete _charts[id]; }
  }

  function setDefaults(p) {
    Chart.defaults.color = p.txMuted;
    Chart.defaults.borderColor = p.bgMantle;
    Chart.defaults.font.size = 11;
  }

  function hBar(id, labels, values, p, opts) {
    opts = opts || {};
    destroy(id);
    var ctx = document.getElementById(id);
    if (!ctx) return;
    _charts[id] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: labels.map(function (_, i) { return p.series[i % p.series.length]; }),
          borderWidth: 0,
          borderRadius: 3,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (c) { return opts.eur ? ' ' + fmtEur(c.raw) : ' ' + fmtN(c.raw); },
            },
          },
        },
        scales: {
          x: { grid: { color: p.bgMantle }, ticks: { color: p.txMuted } },
          y: {
            grid: { display: false },
            ticks: {
              color: p.txPrimary,
              font: { size: 11 },
              callback: function (val) {
                var label = this.getLabelForValue(val);
                return label.length > 36 ? label.slice(0, 34) + '…' : label;
              },
            },
          },
        },
      },
    });
  }

  function vBar(id, labels, values, p, opts) {
    opts = opts || {};
    destroy(id);
    var ctx = document.getElementById(id);
    if (!ctx) return;
    _charts[id] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: labels.map(function (_, i) { return p.series[i % p.series.length]; }),
          borderWidth: 0,
          borderRadius: 3,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (c) { return opts.eur ? ' ' + fmtEur(c.raw) : ' ' + fmtN(c.raw); },
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: p.txMuted, maxRotation: 45,
              callback: function (val) {
                var label = this.getLabelForValue(val);
                return label.length > 13 ? label.slice(0, 11) + '…' : label;
              },
            },
          },
          y: { grid: { color: p.bgMantle }, ticks: { color: p.txMuted } },
        },
      },
    });
  }

  function donut(id, labels, values, p) {
    destroy(id);
    var ctx = document.getElementById(id);
    if (!ctx) return;
    _charts[id] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: labels.map(function (_, i) { return p.series[i % p.series.length]; }),
          borderWidth: 2,
          borderColor: p.bgBase,
          hoverOffset: 8,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '58%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: p.txMuted, padding: 10, font: { size: 11 }, boxWidth: 12, boxHeight: 12 },
          },
          tooltip: {
            callbacks: {
              label: function (c) {
                var total = c.dataset.data.reduce(function (a, b) { return a + b; }, 0);
                var pct = total ? ((c.raw / total) * 100).toFixed(1) : 0;
                return ' ' + c.label + ': ' + fmtN(c.raw) + ' (' + pct + '%)';
              },
            },
          },
        },
      },
    });
  }

  function line(id, labels, values, p) {
    destroy(id);
    var ctx = document.getElementById(id);
    if (!ctx) return;
    _charts[id] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          data: values,
          borderColor: p.ac,
          backgroundColor: p.acSoft,
          fill: true,
          tension: 0.3,
          pointRadius: values.length > 40 ? 0 : 3,
          pointHoverRadius: 5,
          pointBackgroundColor: p.ac,
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: function (c) { return ' ' + fmtN(c.raw) + ' publicadas'; } },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: p.txMuted, maxTicksLimit: 24, maxRotation: 45 } },
          y: { grid: { color: p.bgMantle }, ticks: { color: p.txMuted } },
        },
      },
    });
  }

  // ── KPIs ──────────────────────────────────────────────────────────────────
  function set(id, v) { var el = document.getElementById(id); if (el) el.textContent = v; }

  function updateKpis(k) {
    set('kpi-total',       fmtN(k.total));
    set('kpi-plazo',       fmtN(k.en_plazo));
    set('kpi-pct-plazo',   fmtPct(k.pct_en_plazo) + ' del total');
    set('kpi-presup-total', fmtEur(k.presupuesto_total));
    set('kpi-presup-medio', fmtEur(k.presupuesto_medio));
    set('kpi-presup-max',   fmtEur(k.presupuesto_max));
    set('kpi-con-presup',   fmtN(k.con_presupuesto));
    set('kpi-pct-presup',   fmtPct(k.pct_presupuesto) + ' del total');
    set('kpi-organismos',   fmtN(k.organismos_distintos));
    set('kpi-provincias',   fmtN(k.provincias_distintas));
    set('kpi-municipios',   fmtN(k.municipios_distintos));
  }

  // ── Render gráficas ───────────────────────────────────────────────────────
  function renderAll(data) {
    var p = palette();
    setDefaults(p);

    hBar('chart-ccaa',
      data.por_ccaa.map(function (d) { return d.label; }),
      data.por_ccaa.map(function (d) { return d.value; }), p);

    var badge = document.getElementById('badge-ccaa');
    if (badge && data.por_ccaa.length > 0) {
      badge.textContent = '▲ ' + data.por_ccaa[0].label + ' · ' + fmtN(data.por_ccaa[0].value);
    }

    donut('chart-tipo',
      data.por_tipo.map(function (d) { return d.label; }),
      data.por_tipo.map(function (d) { return d.value; }), p);

    line('chart-mes',
      data.por_mes.map(function (d) { return d.label; }),
      data.por_mes.map(function (d) { return d.value; }), p);

    donut('chart-estado',
      data.por_estado.map(function (d) { return d.label; }),
      data.por_estado.map(function (d) { return d.value; }), p);

    vBar('chart-prange',
      data.por_prange.map(function (d) { return d.label; }),
      data.por_prange.map(function (d) { return d.value; }), p);

    hBar('chart-org',
      data.top_organismos.map(function (d) { return d.label; }),
      data.top_organismos.map(function (d) { return d.value; }), p);

    vBar('chart-prov',
      data.top_provincias.map(function (d) { return d.label; }),
      data.top_provincias.map(function (d) { return d.value; }), p);

    vBar('chart-mun',
      data.top_municipios.map(function (d) { return d.label; }),
      data.top_municipios.map(function (d) { return d.value; }), p);

    hBar('chart-presup-medio',
      data.presupuesto_medio_ccaa.map(function (d) { return d.label; }),
      data.presupuesto_medio_ccaa.map(function (d) { return d.value; }), p, { eur: true });

    hBar('chart-presup-total',
      data.presupuesto_total_ccaa.map(function (d) { return d.label; }),
      data.presupuesto_total_ccaa.map(function (d) { return d.value; }), p, { eur: true });
  }

  // ── Estado de filtros ─────────────────────────────────────────────────────
  var state = {
    solo_plazo:  '',
    ccaa:        '',
    estado:      '',
    tipo:        '',
    prange:      '',
    fecha_desde: '',
    fecha_hasta: '',
    organismo:   '',
  };

  function buildUrl() {
    var params = new URLSearchParams();
    Object.keys(state).forEach(function (k) {
      if (state[k]) params.set(k, state[k]);
    });
    return '/api/analisis/data?' + params.toString();
  }

  // ── Carga de datos ────────────────────────────────────────────────────────
  var _lastData = null;
  var _debounceTimer = null;

  function load() {
    document.getElementById('an-loading').style.display = '';
    document.getElementById('an-charts').style.display = 'none';
    fetch(buildUrl())
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        _lastData = data;
        updateKpis(data.kpis);
        renderAll(data);
        document.getElementById('an-loading').style.display = 'none';
        document.getElementById('an-charts').style.display = '';
      })
      .catch(function (err) {
        document.getElementById('an-loading').innerHTML =
          '<div class="alert alert-danger mx-auto" style="max-width:400px">'
          + '<strong>Error cargando datos</strong><br><small>' + err.message + '</small></div>';
      });
  }

  function debounced(fn, ms) {
    return function () {
      var self = this, args = arguments;
      clearTimeout(_debounceTimer);
      _debounceTimer = setTimeout(function () { fn.apply(self, args); }, ms);
    };
  }

  // ── Sidebar: toggles (abrir/cerrar secciones) ─────────────────────────────
  function initToggles() {
    document.querySelectorAll('#an-sidebar .lm-sidebar-toggle').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var targetId = this.dataset.target;
        var body = document.getElementById(targetId);
        if (!body) return;
        var open = body.classList.toggle('open');
        this.classList.toggle('open', open);
      });
    });
  }

  // ── Sidebar: items de filtro (radio por sección) ──────────────────────────
  function initFilterItems() {
    document.querySelectorAll('#an-sidebar .lm-an-fi').forEach(function (item) {
      item.addEventListener('click', function () {
        var section = this.dataset.section;
        var value = this.dataset.value;
        state[section] = value;
        // Actualizar clases activas en la sección
        document.querySelectorAll('#an-sidebar .lm-an-fi[data-section="' + section + '"]')
          .forEach(function (el) {
            el.classList.toggle('lm-active', el.dataset.value === value);
          });
        load();
      });
    });
  }

  // ── Sidebar: solo activas (booleano) ──────────────────────────────────────
  function initSoloPlazo() {
    var el = document.getElementById('an-solo-plazo');
    var icon = document.getElementById('an-plazo-check');
    if (!el) return;
    el.addEventListener('click', function () {
      state.solo_plazo = state.solo_plazo ? '' : '1';
      el.classList.toggle('lm-active', !!state.solo_plazo);
      if (icon) icon.style.opacity = state.solo_plazo ? '1' : '0';
      load();
    });
  }

  // ── Sidebar: fechas ───────────────────────────────────────────────────────
  function initFechas() {
    var desde = document.getElementById('an-fecha-desde');
    var hasta = document.getElementById('an-fecha-hasta');
    if (desde) desde.addEventListener('change', function () { state.fecha_desde = this.value; load(); });
    if (hasta) hasta.addEventListener('change', function () { state.fecha_hasta = this.value; load(); });
  }

  // ── Sidebar: organismo (debounced) ────────────────────────────────────────
  function initOrganismo() {
    var input = document.getElementById('an-organismo-input');
    if (!input) return;
    input.addEventListener('input', debounced(function () {
      state.organismo = input.value.trim();
      load();
    }, 500));
  }

  // ── Reset ─────────────────────────────────────────────────────────────────
  function initReset() {
    var btn = document.getElementById('an-reset');
    if (!btn) return;
    btn.addEventListener('click', function () {
      Object.keys(state).forEach(function (k) { state[k] = ''; });
      // Restaurar "Todos/Todas" como activos
      document.querySelectorAll('#an-sidebar .lm-an-fi').forEach(function (el) {
        el.classList.toggle('lm-active', el.dataset.value === '');
      });
      var plazoEl = document.getElementById('an-solo-plazo');
      var plazoIcon = document.getElementById('an-plazo-check');
      if (plazoEl) plazoEl.classList.remove('lm-active');
      if (plazoIcon) plazoIcon.style.opacity = '0';
      var desde = document.getElementById('an-fecha-desde');
      var hasta = document.getElementById('an-fecha-hasta');
      if (desde) desde.value = '';
      if (hasta) hasta.value = '';
      var org = document.getElementById('an-organismo-input');
      if (org) org.value = '';
      load();
    });
  }

  // ── Re-pintar al cambiar tema ─────────────────────────────────────────────
  function initTheme() {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.addEventListener('click', function () {
      setTimeout(function () {
        if (_lastData) renderAll(_lastData);
      }, 60);
    });
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    // Marcar tab activo
    var tab = document.querySelector('.lm-nav-tabs a[href="/analisis"]');
    if (tab) tab.classList.add('lm-nav-tab-active');

    initToggles();
    initFilterItems();
    initSoloPlazo();
    initFechas();
    initOrganismo();
    initReset();
    initTheme();

    load();
  });
})();
