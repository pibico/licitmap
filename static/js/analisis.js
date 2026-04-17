(function () {
  'use strict';

  // ── Paleta desde CSS vars ─────────────────────────────────────────────────
  function css(v) {
    return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  }

  function palette() {
    return {
      ac:       css('--ac-main'),
      acSoft:   css('--ac-soft'),
      txMuted:  css('--tx-muted'),
      txFaint:  css('--tx-faint'),
      txPrimary:css('--tx-primary'),
      bgBase:   css('--bg-base'),
      bgMantle: css('--bg-mantle'),
      series: [
        css('--ac-main'),
        css('--co-blue'),
        css('--co-mauve'),
        css('--co-yellow'),
        css('--co-red'),
        css('--co-sky'),
        '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4',
        '#84cc16', '#f97316', '#a855f7', '#14b8a6', '#ef4444',
        '#ec4899', '#64748b', '#22d3ee', '#fb923c',
      ],
    };
  }

  // ── Formateo ──────────────────────────────────────────────────────────────
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

  // ── Instancias de Chart.js ────────────────────────────────────────────────
  const _charts = {};

  function destroy(id) {
    if (_charts[id]) { _charts[id].destroy(); delete _charts[id]; }
  }

  function setDefaults(p) {
    Chart.defaults.color = p.txMuted;
    Chart.defaults.borderColor = p.bgMantle;
    Chart.defaults.font.size = 11;
  }

  // ── Fábricas de gráficas ──────────────────────────────────────────────────

  // Barras horizontales (para rankings con etiquetas largas)
  function hBar(id, labels, values, p, opts = {}) {
    destroy(id);
    const ctx = document.getElementById(id);
    if (!ctx) return;
    _charts[id] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: labels.map((_, i) => p.series[i % p.series.length]),
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
              label: c => opts.eur ? ' ' + fmtEur(c.raw) : ' ' + fmtN(c.raw),
            },
          },
        },
        scales: {
          x: {
            grid: { color: p.bgMantle },
            ticks: { color: p.txMuted },
          },
          y: {
            grid: { display: false },
            ticks: {
              color: p.txPrimary,
              font: { size: 11 },
              callback: function (val, idx) {
                const label = this.getLabelForValue(val);
                return label.length > 38 ? label.slice(0, 36) + '…' : label;
              },
            },
          },
        },
      },
    });
  }

  // Barras verticales
  function vBar(id, labels, values, p, opts = {}) {
    destroy(id);
    const ctx = document.getElementById(id);
    if (!ctx) return;
    _charts[id] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: opts.mono
            ? p.ac
            : labels.map((_, i) => p.series[i % p.series.length]),
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
              label: c => opts.eur ? ' ' + fmtEur(c.raw) : ' ' + fmtN(c.raw),
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: p.txMuted,
              maxRotation: 45,
              callback: function (val) {
                const label = this.getLabelForValue(val);
                return label.length > 14 ? label.slice(0, 12) + '…' : label;
              },
            },
          },
          y: {
            grid: { color: p.bgMantle },
            ticks: { color: p.txMuted },
          },
        },
      },
    });
  }

  // Donut
  function donut(id, labels, values, p) {
    destroy(id);
    const ctx = document.getElementById(id);
    if (!ctx) return;
    _charts[id] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: labels.map((_, i) => p.series[i % p.series.length]),
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
            labels: {
              color: p.txMuted,
              padding: 10,
              font: { size: 11 },
              boxWidth: 12,
              boxHeight: 12,
            },
          },
          tooltip: {
            callbacks: {
              label: c => {
                const total = c.dataset.data.reduce((a, b) => a + b, 0);
                const pct = total ? ((c.raw / total) * 100).toFixed(1) : 0;
                return ` ${c.label}: ${fmtN(c.raw)} (${pct}%)`;
              },
            },
          },
        },
      },
    });
  }

  // Línea (evolución mensual)
  function line(id, labels, values, p) {
    destroy(id);
    const ctx = document.getElementById(id);
    if (!ctx) return;
    _charts[id] = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
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
            callbacks: {
              label: c => ' ' + fmtN(c.raw) + ' publicadas',
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: p.txMuted,
              maxTicksLimit: 24,
              maxRotation: 45,
            },
          },
          y: {
            grid: { color: p.bgMantle },
            ticks: { color: p.txMuted },
          },
        },
      },
    });
  }

  // ── KPI cards ─────────────────────────────────────────────────────────────
  function updateKpis(k) {
    function set(id, v) {
      const el = document.getElementById(id);
      if (el) el.textContent = v;
    }
    set('kpi-total',        fmtN(k.total));
    set('kpi-plazo',        fmtN(k.en_plazo));
    set('kpi-pct-plazo',    fmtPct(k.pct_en_plazo) + ' del total');
    set('kpi-presup-total', fmtEur(k.presupuesto_total));
    set('kpi-presup-medio', fmtEur(k.presupuesto_medio));
    set('kpi-presup-max',   fmtEur(k.presupuesto_max));
    set('kpi-con-presup',   fmtN(k.con_presupuesto) + ' (' + fmtPct(k.pct_presupuesto) + ')');
    set('kpi-organismos',   fmtN(k.organismos_distintos));
    set('kpi-provincias',   fmtN(k.provincias_distintas));
    set('kpi-municipios',   fmtN(k.municipios_distintos));
  }

  // ── Render todas las gráficas ─────────────────────────────────────────────
  function renderAll(data) {
    const p = palette();
    setDefaults(p);

    hBar('chart-ccaa',
      data.por_ccaa.map(d => d.label),
      data.por_ccaa.map(d => d.value),
      p
    );

    // Badge con top CCAA
    const badge = document.getElementById('badge-ccaa');
    if (badge && data.por_ccaa.length > 0) {
      badge.textContent = '▲ ' + data.por_ccaa[0].label + ' · ' + fmtN(data.por_ccaa[0].value);
    }

    donut('chart-tipo',
      data.por_tipo.map(d => d.label),
      data.por_tipo.map(d => d.value),
      p
    );

    line('chart-mes',
      data.por_mes.map(d => d.label),
      data.por_mes.map(d => d.value),
      p
    );

    donut('chart-estado',
      data.por_estado.map(d => d.label),
      data.por_estado.map(d => d.value),
      p
    );

    vBar('chart-prange',
      data.por_prange.map(d => d.label),
      data.por_prange.map(d => d.value),
      p, { mono: false }
    );

    hBar('chart-org',
      data.top_organismos.map(d => d.label),
      data.top_organismos.map(d => d.value),
      p
    );

    vBar('chart-prov',
      data.top_provincias.map(d => d.label),
      data.top_provincias.map(d => d.value),
      p
    );

    vBar('chart-mun',
      data.top_municipios.map(d => d.label),
      data.top_municipios.map(d => d.value),
      p
    );

    hBar('chart-presup-medio',
      data.presupuesto_medio_ccaa.map(d => d.label),
      data.presupuesto_medio_ccaa.map(d => d.value),
      p, { eur: true }
    );

    hBar('chart-presup-total',
      data.presupuesto_total_ccaa.map(d => d.label),
      data.presupuesto_total_ccaa.map(d => d.value),
      p, { eur: true }
    );
  }

  // ── Estado de la app ──────────────────────────────────────────────────────
  let _lastData = null;
  let _loadTimer = null;

  function buildUrl() {
    const form = document.getElementById('an-filters');
    const params = new URLSearchParams(new FormData(form));
    // FormData omite checkboxes desmarcados — correcto
    return '/api/analisis/data?' + params.toString();
  }

  function showLoading() {
    document.getElementById('an-loading').style.display = '';
    document.getElementById('an-charts').style.display = 'none';
  }

  function hideLoading() {
    document.getElementById('an-loading').style.display = 'none';
    document.getElementById('an-charts').style.display = '';
  }

  function load() {
    showLoading();
    fetch(buildUrl())
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        _lastData = data;
        updateKpis(data.kpis);
        renderAll(data);
        hideLoading();
      })
      .catch(function (err) {
        document.getElementById('an-loading').innerHTML =
          '<div class="alert alert-danger mx-auto" style="max-width:400px">'
          + '<strong>Error cargando datos</strong><br><small>' + err.message + '</small></div>';
      });
  }

  // Debounce para inputs de texto
  function debounce(fn, ms) {
    return function () {
      clearTimeout(_loadTimer);
      _loadTimer = setTimeout(fn, ms);
    };
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    // Marcar tab activo
    var tab = document.querySelector('.lm-nav-tabs a[href="/analisis"]');
    if (tab) tab.classList.add('lm-nav-tab-active');

    var form = document.getElementById('an-filters');

    // Selects y checkbox → carga inmediata
    form.addEventListener('change', function (e) {
      if (e.target.tagName !== 'INPUT' || e.target.type !== 'text') {
        load();
      }
    });

    // Texto organismo → debounced
    var orgInput = document.getElementById('an-organismo');
    if (orgInput) {
      orgInput.addEventListener('input', debounce(load, 500));
    }

    // Reset
    document.getElementById('an-reset').addEventListener('click', function () {
      form.reset();
      load();
    });

    // Re-pintar gráficas al cambiar tema (sin nueva llamada API)
    var themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
      themeBtn.addEventListener('click', function () {
        setTimeout(function () {
          if (_lastData) renderAll(_lastData);
        }, 60);
      });
    }

    load();
  });
})();
