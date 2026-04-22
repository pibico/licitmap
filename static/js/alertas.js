// LicitMap — Alertas JS v3

(function () {

  // ── Toast ──────────────────────────────────────────────────────────────────
  function showToast(msg, type) {
    var t = document.getElementById('lm-toast');
    if (!t) return;
    t.textContent = msg;
    t.className = 'lm-toast lm-toast-' + (type || 'info') + ' show';
    clearTimeout(t._timer);
    t._timer = setTimeout(function () { t.classList.remove('show'); }, 4000);
  }

  // ── API helper ────────────────────────────────────────────────────────────
  function api(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(function (r) { return r.json(); });
  }

  // ── Chip picker helpers ───────────────────────────────────────────────────
  function getChipVals(id) {
    var picker = document.getElementById(id);
    if (!picker) return [];
    return Array.from(picker.querySelectorAll('.lm-chip.lm-chip-active'))
      .map(function (c) { return c.dataset.val; });
  }

  function setChipVals(id, vals) {
    var picker = document.getElementById(id);
    if (!picker) return;
    picker.querySelectorAll('.lm-chip').forEach(function (c) {
      c.classList.toggle('lm-chip-active', vals.indexOf(c.dataset.val) >= 0);
    });
  }

  function clearChips(id) {
    var picker = document.getElementById(id);
    if (!picker) return;
    picker.querySelectorAll('.lm-chip').forEach(function (c) {
      c.classList.remove('lm-chip-active');
    });
  }

  // Attach click-toggle to all chip pickers
  function initChipPickers() {
    document.querySelectorAll('.lm-chip-picker').forEach(function (picker) {
      picker.addEventListener('click', function (e) {
        var chip = e.target.closest('.lm-chip');
        if (!chip) return;
        chip.classList.toggle('lm-chip-active');
      });
    });
  }

  // ── Newsletter ─────────────────────────────────────────────────────────────
  function initNl() {
    var form    = document.getElementById('nl-form');
    var guardar = document.getElementById('nl-guardar');
    var probar  = document.getElementById('nl-probar');
    var freqSel = document.getElementById('nl-frecuencia');
    var diaCol  = document.getElementById('nl-dia-col');

    if (!form) return;

    if (freqSel) {
      freqSel.addEventListener('change', function () {
        if (diaCol) diaCol.style.display = freqSel.value === 'semanal' ? '' : 'none';
      });
    }

    if (guardar) {
      guardar.addEventListener('click', function () {
        var ccaa = getChipVals('nl-ccaa');
        var payload = {
          nombre:       document.getElementById('nl-nombre').value,
          activa:       document.getElementById('nl-activa').checked,
          frecuencia:   freqSel ? freqSel.value : 'diaria',
          dia_semana:   parseInt(document.getElementById('nl-dia').value, 10) || 0,
          hora_envio:   parseInt(document.getElementById('nl-hora').value, 10) || 8,
          keywords:     document.getElementById('nl-keywords').value.trim(),
          presmin:      document.getElementById('nl-presmin').value,
          solo_activas: document.getElementById('nl-solo-activas').checked,
          ccaa:         ccaa,
        };
        guardar.disabled = true;
        api('/api/alertas/newsletter', payload).then(function (r) {
          if (r.ok) showToast('Newsletter guardada correctamente.', 'success');
          else showToast('Error: ' + (r.error || 'desconocido'), 'error');
        }).catch(function () {
          showToast('Error de red al guardar.', 'error');
        }).finally(function () { guardar.disabled = false; });
      });
    }

    if (probar) {
      probar.addEventListener('click', function () {
        probar.disabled = true;
        probar.textContent = 'Enviando…';
        fetch('/api/alertas/newsletter/probar', { method: 'POST' })
          .then(function (r) { return r.json(); })
          .then(function (r) {
            if (r.ok) showToast('Prueba enviada (' + r.count + ' licitaciones).', 'success');
            else showToast('Error: ' + (r.error || 'desconocido'), 'error');
          })
          .catch(function () { showToast('Error de red.', 'error'); })
          .finally(function () { probar.disabled = false; probar.textContent = 'Enviar prueba'; });
      });
    }
  }

  // ── Alerta: form nueva / editar ───────────────────────────────────────────
  function initAlertaForm() {
    var wrap     = document.getElementById('form-alerta-wrap');
    var btnNueva = document.getElementById('btn-nueva-alerta');
    var btnCanc  = document.getElementById('al-cancelar');
    var btnGuard = document.getElementById('al-guardar');
    var freqSel  = document.getElementById('al-frecuencia');
    var diaCol   = document.getElementById('al-dia-col');

    if (!wrap) return;

    function openForm() {
      wrap.style.display = '';
      wrap.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    function closeForm() { wrap.style.display = 'none'; resetForm(); }

    function resetForm() {
      document.getElementById('alerta-edit-id').value = '';
      document.getElementById('al-nombre').value      = '';
      document.getElementById('al-keywords').value    = '';
      document.getElementById('al-cpv').value         = '';
      document.getElementById('al-presmin').value     = '';
      document.getElementById('al-presmax').value     = '';
      document.getElementById('al-solo-activas').checked = false;
      clearChips('al-ccaa');
      clearChips('al-tipo');
      clearChips('al-estado');
      if (freqSel) freqSel.value = 'diaria';
      document.getElementById('al-hora').value = '8';
      if (diaCol) diaCol.style.display = 'none';
    }

    if (freqSel) {
      freqSel.addEventListener('change', function () {
        if (diaCol) diaCol.style.display = freqSel.value === 'semanal' ? '' : 'none';
      });
    }

    if (btnNueva) btnNueva.addEventListener('click', function () {
      if (wrap.style.display !== 'none') { closeForm(); return; }
      resetForm();
      openForm();
    });

    if (btnCanc) btnCanc.addEventListener('click', closeForm);

    if (btnGuard) {
      btnGuard.addEventListener('click', function () {
        var nombre = document.getElementById('al-nombre').value.trim();
        if (!nombre) { showToast('El nombre es obligatorio.', 'error'); return; }
        var payload = {
          edit_id:      document.getElementById('alerta-edit-id').value || null,
          nombre:       nombre,
          keywords:     document.getElementById('al-keywords').value.trim(),
          cpv:          document.getElementById('al-cpv').value.trim(),
          ccaa:         getChipVals('al-ccaa'),
          tipo:         getChipVals('al-tipo'),
          estado:       getChipVals('al-estado'),
          presmin:      document.getElementById('al-presmin').value,
          presmax:      document.getElementById('al-presmax').value,
          solo_activas: document.getElementById('al-solo-activas').checked,
          frecuencia:   freqSel ? freqSel.value : 'diaria',
          dia_semana:   parseInt(document.getElementById('al-dia').value, 10) || 0,
          hora_envio:   parseInt(document.getElementById('al-hora').value, 10) || 8,
        };
        btnGuard.disabled = true;
        api('/api/alertas/nueva', payload).then(function (r) {
          if (r.ok) {
            showToast('Alerta guardada.', 'success');
            setTimeout(function () { location.reload(); }, 800);
          } else {
            showToast('Error: ' + (r.error || 'desconocido'), 'error');
          }
        }).catch(function () {
          showToast('Error de red.', 'error');
        }).finally(function () { btnGuard.disabled = false; });
      });
    }

    // Editar: rellenar form desde data-* del botón
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.btn-editar');
      if (!btn) return;
      var d = btn.dataset;
      document.getElementById('alerta-edit-id').value = d.id;
      document.getElementById('al-nombre').value      = d.nombre || '';
      document.getElementById('al-keywords').value    = d.keywords || '';
      document.getElementById('al-cpv').value         = d.cpv || '';
      document.getElementById('al-presmin').value     = d.presmin || '';
      document.getElementById('al-presmax').value     = d.presmax || '';
      document.getElementById('al-solo-activas').checked = d.soloactivas === '1';
      if (freqSel) freqSel.value = d.frecuencia || 'diaria';
      document.getElementById('al-dia').value  = d.dia  || '0';
      document.getElementById('al-hora').value = d.hora || '8';
      if (diaCol) diaCol.style.display = (d.frecuencia === 'semanal') ? '' : 'none';
      setChipVals('al-ccaa',   (d.ccaa   || '').split('|').filter(Boolean));
      setChipVals('al-tipo',   (d.tipo   || '').split('|').filter(Boolean));
      setChipVals('al-estado', (d.estado || '').split('|').filter(Boolean));
      openForm();
    });
  }

  // ── Suscripción: form ────────────────────────────────────────────────────
  function initSubForm() {
    var wrap     = document.getElementById('form-sub-wrap');
    var btnNueva = document.getElementById('btn-nueva-sub');
    var btnCanc  = document.getElementById('sub-cancelar');
    var btnGuard = document.getElementById('sub-guardar');
    var tipoSel  = document.getElementById('sub-tipo');
    var freqSel  = document.getElementById('sub-frecuencia');
    var diaCol   = document.getElementById('sub-dia-col');
    var selCol   = document.getElementById('sub-valor-select-col');
    var txtCol   = document.getElementById('sub-valor-text-col');
    var valorLbl = document.getElementById('sub-valor-label');

    if (!wrap) return;

    var PLACEHOLDERS = {
      provincia: 'Ej: Madrid, Barcelona…',
      organismo: 'Ej: Ministerio de Defensa…',
      cpv:       'Ej: 72212000',
    };
    var LABELS = { provincia: 'Provincia', organismo: 'Organismo', cpv: 'Código CPV' };

    function updateTipoUI() {
      var tipo = tipoSel.value;
      if (tipo === 'ccaa') {
        selCol.style.display = ''; txtCol.style.display = 'none';
      } else {
        selCol.style.display = 'none'; txtCol.style.display = '';
        if (valorLbl) valorLbl.textContent = LABELS[tipo] || 'Valor';
        var inp = document.getElementById('sub-valor-text');
        if (inp) inp.placeholder = PLACEHOLDERS[tipo] || '';
      }
    }

    if (tipoSel) tipoSel.addEventListener('change', updateTipoUI);
    if (freqSel) freqSel.addEventListener('change', function () {
      if (diaCol) diaCol.style.display = freqSel.value === 'semanal' ? '' : 'none';
    });

    function openForm() { wrap.style.display = ''; wrap.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }
    function closeForm() { wrap.style.display = 'none'; resetForm(); }
    function resetForm() {
      document.getElementById('sub-edit-id').value    = '';
      document.getElementById('sub-nombre').value     = '';
      document.getElementById('sub-valor-text').value = '';
      if (tipoSel) { tipoSel.value = 'ccaa'; updateTipoUI(); }
      if (freqSel) { freqSel.value = 'diaria'; if (diaCol) diaCol.style.display = 'none'; }
      document.getElementById('sub-hora').value = '8';
    }

    if (btnNueva) btnNueva.addEventListener('click', function () {
      if (wrap.style.display !== 'none') { closeForm(); return; }
      resetForm(); openForm();
    });
    if (btnCanc) btnCanc.addEventListener('click', closeForm);

    if (btnGuard) {
      btnGuard.addEventListener('click', function () {
        var tipo  = tipoSel.value;
        var valor = tipo === 'ccaa'
          ? document.getElementById('sub-valor-ccaa').value
          : document.getElementById('sub-valor-text').value.trim();
        if (!valor) { showToast('Indica el valor de la entidad.', 'error'); return; }
        var payload = {
          edit_id:       document.getElementById('sub-edit-id').value || null,
          nombre:        document.getElementById('sub-nombre').value.trim(),
          entidad_tipo:  tipo,
          entidad_valor: valor,
          frecuencia:    freqSel ? freqSel.value : 'diaria',
          dia_semana:    parseInt(document.getElementById('sub-dia').value, 10) || 0,
          hora_envio:    parseInt(document.getElementById('sub-hora').value, 10) || 8,
        };
        btnGuard.disabled = true;
        api('/api/alertas/suscripcion', payload).then(function (r) {
          if (r.ok) {
            showToast('Suscripción guardada.', 'success');
            setTimeout(function () { location.reload(); }, 800);
          } else {
            showToast('Error: ' + (r.error || 'desconocido'), 'error');
          }
        }).catch(function () {
          showToast('Error de red.', 'error');
        }).finally(function () { btnGuard.disabled = false; });
      });
    }

    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.btn-editar-sub');
      if (!btn) return;
      var d = btn.dataset;
      document.getElementById('sub-edit-id').value  = d.id;
      document.getElementById('sub-nombre').value   = d.nombre || '';
      if (tipoSel) { tipoSel.value = d.tipo || 'ccaa'; updateTipoUI(); }
      if (d.tipo === 'ccaa') {
        var sel = document.getElementById('sub-valor-ccaa');
        if (sel) sel.value = d.valor || '';
      } else {
        var inp = document.getElementById('sub-valor-text');
        if (inp) inp.value = d.valor || '';
      }
      if (freqSel) {
        freqSel.value = d.frecuencia || 'diaria';
        if (diaCol) diaCol.style.display = freqSel.value === 'semanal' ? '' : 'none';
      }
      document.getElementById('sub-dia').value  = d.dia  || '0';
      document.getElementById('sub-hora').value = d.hora || '8';
      openForm();
    });
  }

  // ── Acciones comunes (toggle, eliminar, probar) ───────────────────────────
  function initActions() {
    document.addEventListener('change', function (e) {
      var chk = e.target.closest('.alerta-toggle');
      if (!chk) return;
      var id = chk.dataset.id;
      api('/api/alertas/' + id + '/toggle', {}).then(function (r) {
        var item = document.querySelector('.lm-alertas-item[data-id="' + id + '"]');
        if (r.ok && item) item.classList.toggle('lm-ai-inactive', !r.activa);
        else if (!r.ok) showToast('Error al cambiar estado.', 'error');
      });
    });

    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.btn-probar');
      if (!btn) return;
      var id = btn.dataset.id;
      var orig = btn.innerHTML;
      btn.disabled = true; btn.textContent = '…';
      fetch('/api/alertas/' + id + '/probar', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (r) {
          if (r.ok) showToast('Prueba enviada — ' + r.count + ' licitaciones.', 'success');
          else showToast('Error: ' + (r.error || 'desconocido'), 'error');
        })
        .catch(function () { showToast('Error de red.', 'error'); })
        .finally(function () { btn.disabled = false; btn.innerHTML = orig; });
    });

    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.btn-eliminar');
      if (!btn) return;
      var id   = btn.dataset.id;
      var item = document.querySelector('.lm-alertas-item[data-id="' + id + '"]');
      var nombre = item ? (item.querySelector('.lm-ai-nombre') || {}).textContent : 'esta alerta';
      if (!confirm('¿Eliminar "' + nombre + '"?')) return;
      api('/api/alertas/' + id + '/eliminar', {}).then(function (r) {
        if (r.ok && item) { item.style.opacity = '0'; setTimeout(function () { item.remove(); }, 300); }
        else showToast('Error al eliminar.', 'error');
      });
    });

    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.btn-unfollow');
      if (!btn) return;
      var segId = btn.dataset.segId;
      var item  = document.querySelector('.lm-watch-item[data-seg-id="' + segId + '"]');
      if (!confirm('¿Dejar de seguir esta licitación?')) return;
      api('/api/alertas/watchlist/' + segId + '/eliminar', {}).then(function (r) {
        if (r.ok && item) { item.style.opacity = '0'; setTimeout(function () { item.remove(); }, 300); }
        else showToast('Error al eliminar seguimiento.', 'error');
      });
    });

    document.addEventListener('change', function (e) {
      var chk = e.target.closest('.watch-cambio-toggle');
      if (!chk) return;
      api('/api/alertas/watchlist/' + chk.dataset.segId + '/config',
          { notif_cambio_estado: chk.checked });
    });

    document.addEventListener('change', function (e) {
      var sel = e.target.closest('.lm-watch-dias-select');
      if (!sel) return;
      var val = sel.value === 'None' || sel.value === '' ? null : parseInt(sel.value, 10);
      api('/api/alertas/watchlist/' + sel.dataset.segId + '/config',
          { notif_dias_vencimiento: val });
    });
  }

  // ── Sidebar filtros compartidos ──────────────────────────────────────────
  function initGlobalSidebar() {
    var sidebar = document.getElementById('lm-gf-sidebar');
    if (!sidebar || typeof LMFilters === 'undefined') return;

    function syncUI() {
      var f = LMFilters.get();
      sidebar.querySelectorAll('.lm-gf-item').forEach(function (el) {
        var key = el.dataset.gfKey, val = el.dataset.gfVal;
        var vals = f[key] ? f[key].split('|').filter(Boolean) : [];
        el.classList.toggle('lm-active', vals.indexOf(val) >= 0);
      });
      var fd = document.getElementById('gf-fecha-desde');
      var fh = document.getElementById('gf-fecha-hasta');
      if (fd) fd.value = f.fecha_desde || '';
      if (fh) fh.value = f.fecha_hasta || '';
    }

    syncUI();

    sidebar.addEventListener('click', function (e) {
      var item = e.target.closest('.lm-gf-item');
      if (!item) return;
      var key = item.dataset.gfKey, val = item.dataset.gfVal;
      var f = LMFilters.get();
      var vals = f[key] ? f[key].split('|').filter(Boolean) : [];
      var idx = vals.indexOf(val);
      if (idx >= 0) vals.splice(idx, 1); else vals.push(val);
      LMFilters.save({ [key]: vals.join('|') });
      syncUI();
    });

    var fd = document.getElementById('gf-fecha-desde');
    var fh = document.getElementById('gf-fecha-hasta');
    if (fd) fd.addEventListener('change', function () { LMFilters.save({ fecha_desde: fd.value }); });
    if (fh) fh.addEventListener('change', function () { LMFilters.save({ fecha_hasta: fh.value }); });

    var resetBtn = document.getElementById('gf-reset');
    if (resetBtn) resetBtn.addEventListener('click', function () { LMFilters.clear(); syncUI(); });

    var crearBtn = document.getElementById('gf-crear-alerta');
    if (crearBtn) {
      crearBtn.addEventListener('click', function () {
        var f      = LMFilters.get();
        var tipos  = f.tipo   ? f.tipo.split('|').filter(Boolean)   : [];
        var ccaas  = f.ccaa   ? f.ccaa.split('|').filter(Boolean)   : [];
        var estados= f.estado ? f.estado.split('|').filter(Boolean) : [];
        setChipVals('al-tipo',   tipos);
        setChipVals('al-ccaa',   ccaas);
        setChipVals('al-estado', estados);
        var wrap = document.getElementById('form-alerta-wrap');
        if (wrap && wrap.style.display === 'none') {
          var btnNueva = document.getElementById('btn-nueva-alerta');
          if (btnNueva) btnNueva.click();
        }
        if (wrap) wrap.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
    }
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    initChipPickers();
    initGlobalSidebar();
    initNl();
    initAlertaForm();
    initSubForm();
    initActions();
  });

})();
