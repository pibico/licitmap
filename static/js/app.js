// LicitMap JS

(function () {
  var THEME_KEY = 'licitmap-theme';

  function applyTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    localStorage.setItem(THEME_KEY, theme);
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Theme toggle
    var btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', function () {
        var current = document.documentElement.getAttribute('data-theme');
        applyTheme(current === 'dark' ? 'light' : 'dark');
      });
    }

    // CCAA filter: solo visible cuando país = España
    var paisSel = document.getElementById('filtro-pais');
    var ccaaWrap = document.getElementById('filtro-ccaa-wrap');
    if (paisSel && ccaaWrap) {
      function toggleCCAA() {
        var esEspana = paisSel.value === 'España';
        ccaaWrap.style.display = esEspana ? '' : 'none';
        if (!esEspana) {
          ccaaWrap.querySelector('select').value = '';
        }
      }
      paisSel.addEventListener('change', toggleCCAA);
      toggleCCAA();
    }

    // Auto-filtrado AJAX
    var form = document.getElementById('filtros-form');
    if (form) {
      function fetchResultados() {
        var params = new URLSearchParams(new FormData(form));
        params.set('partial', '1');
        fetch('/?' + params.toString())
          .then(function (r) { return r.json(); })
          .then(function (data) {
            document.getElementById('tabla-body').innerHTML = data.filas;
            document.getElementById('paginacion-top').innerHTML = data.paginacion;
            document.getElementById('paginacion-bottom').innerHTML = data.paginacion;
            document.getElementById('resultados-count').textContent = data.resultados + ' resultado(s)';
          });
      }

      // Selects y fechas: fetch inmediato al cambiar
      form.querySelectorAll('select, input[type="date"]').forEach(function (el) {
        el.addEventListener('change', fetchResultados);
      });

      // Inputs texto/número: fetch con debounce 600ms
      var debounceTimer;
      form.querySelectorAll('input[type="text"], input[type="number"]').forEach(function (inp) {
        inp.addEventListener('input', function () {
          clearTimeout(debounceTimer);
          debounceTimer = setTimeout(fetchResultados, 600);
        });
      });
    }
  });
})();
