// LicitMap — Alertas JS v7

(function () {

  // ── i18n shortcuts ─────────────────────────────────────────────────────────
  var I18N = window.I18N || {};
  var AL   = I18N.al || {};
  var T    = AL.toast || {};
  function fmt(template, vars) {
    return String(template || '').replace(/%\((\w+)\)s/g, function (_, k) {
      return (vars && vars[k] != null) ? vars[k] : '';
    });
  }
  function errMsg(err) {
    return (T.errorPrefix || 'Error:') + ' ' + (err || T.unknown || '');
  }

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

  // ── CSV helpers (para los text inputs de municipios) ──────────────────────
  function parseCsv(s) {
    return (s || '').split(',').map(function (x) { return x.trim(); }).filter(Boolean);
  }
  function formatPipe(pipeStr) {
    return (pipeStr || '').split('|').filter(Boolean).join(', ');
  }

  // ── Progressive disclosure: CCAA → provincia → municipio ──────────────────
  // Rellena el chip picker de provincia con las provincias pertenecientes a
  // las CCAA seleccionadas. Mantiene selección previa si coincide.
  function renderProvChips(pickerEl, provs, selected) {
    var sel = new Set(selected || []);
    pickerEl.innerHTML = (provs || []).map(function (p) {
      var act = sel.has(p) ? ' lm-chip-active' : '';
      return '<button type="button" class="lm-chip' + act + '" data-val="' + p + '">' + p + '</button>';
    }).join('');
  }

  function updateProvChipsFromCcaa(prefix) {
    var picker  = document.getElementById(prefix + '-provincia');
    var provCol = document.getElementById(prefix + '-prov-col');
    var munCol  = document.getElementById(prefix + '-mun-col');
    if (!picker) return;
    var ccaaVals = getChipVals(prefix + '-ccaa');
    if (ccaaVals.length === 0) {
      if (provCol) provCol.style.display = 'none';
      if (munCol)  munCol.style.display  = 'none';
      picker.innerHTML = '';
      return;
    }
    // Selección a restaurar: prioridad a chips ya activos; si no, usa
    // data-selected (cargada desde el backend o puesta por "Crear desde filtros").
    var selected = getChipVals(prefix + '-provincia');
    if (selected.length === 0 && picker.dataset.selected) {
      selected = picker.dataset.selected.split('|').filter(Boolean);
    }
    fetch('/api/geo/provincias-by-ccaa?ccaa=' + encodeURIComponent(ccaaVals.join('|')))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        renderProvChips(picker, d.provincias || [], selected);
        picker.dataset.selected = '';
        if (provCol) provCol.style.display = '';
        updateMunVisibility(prefix);
      })
      .catch(function () {});
  }

  function updateMunVisibility(prefix) {
    var munCol = document.getElementById(prefix + '-mun-col');
    if (!munCol) return;
    var provs = getChipVals(prefix + '-provincia');
    munCol.style.display = provs.length > 0 ? '' : 'none';
  }

  // Engancha listeners al picker de CCAA y al de provincia para encadenar
  // la revelación. Se llama una vez por prefix (`nl`, `al`) al boot.
  function initGeoDisclosure(prefix) {
    var ccaaPicker = document.getElementById(prefix + '-ccaa');
    var provPicker = document.getElementById(prefix + '-provincia');
    if (ccaaPicker) {
      ccaaPicker.addEventListener('click', function (e) {
        if (!e.target.closest('.lm-chip')) return;
        // initChipPickers también está enganchado a este mismo evento y
        // togglea la clase. Diferimos para leer el estado nuevo.
        setTimeout(function () { updateProvChipsFromCcaa(prefix); }, 0);
      });
    }
    if (provPicker) {
      provPicker.addEventListener('click', function (e) {
        if (!e.target.closest('.lm-chip')) return;
        setTimeout(function () { updateMunVisibility(prefix); }, 0);
      });
    }
    // Render inicial si había CCAA guardada (form de newsletter / editar alerta).
    updateProvChipsFromCcaa(prefix);
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
        var ccaa   = getChipVals('nl-ccaa');
        var provs  = getChipVals('nl-provincia');
        var munEl  = document.getElementById('nl-municipio');
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
          provincias:   provs,
          municipios:   munEl ? parseCsv(munEl.value) : [],
        };
        guardar.disabled = true;
        api('/api/alerts/newsletter', payload).then(function (r) {
          if (r.ok) showToast(T.nlSaved, 'success');
          else showToast(errMsg(r.error), 'error');
        }).catch(function () {
          showToast(T.saveError, 'error');
        }).finally(function () { guardar.disabled = false; });
      });
    }

    if (probar) {
      probar.addEventListener('click', function () {
        probar.disabled = true;
        probar.textContent = AL.sending || '…';
        fetch('/api/alerts/newsletter/probar', { method: 'POST' })
          .then(function (r) { return r.json(); })
          .then(function (r) {
            if (r.ok) showToast(fmt(T.testSent, { count: r.count }), 'success');
            else showToast(errMsg(r.error), 'error');
          })
          .catch(function () { showToast(T.netError, 'error'); })
          .finally(function () { probar.disabled = false; probar.textContent = AL.sendTestBtn || ''; });
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
      // Reset geo progressive disclosure
      var munEl = document.getElementById('al-municipio');
      if (munEl) munEl.value = '';
      var provEl = document.getElementById('al-provincia');
      if (provEl) { provEl.innerHTML = ''; provEl.dataset.selected = ''; }
      var provCol = document.getElementById('al-prov-col');
      var munCol  = document.getElementById('al-mun-col');
      if (provCol) provCol.style.display = 'none';
      if (munCol)  munCol.style.display  = 'none';
      if (freqSel) freqSel.value = 'diaria';
      document.getElementById('al-dia').value  = '0';
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
        if (!nombre) { showToast(T.nameRequired, 'error'); return; }
        var munEl = document.getElementById('al-municipio');
        var payload = {
          edit_id:      document.getElementById('alerta-edit-id').value || null,
          nombre:       nombre,
          keywords:     document.getElementById('al-keywords').value.trim(),
          cpv:          document.getElementById('al-cpv').value.trim(),
          ccaa:         getChipVals('al-ccaa'),
          provincias:   getChipVals('al-provincia'),
          municipios:   munEl ? parseCsv(munEl.value) : [],
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
        api('/api/alerts/nueva', payload).then(function (r) {
          if (r.ok) {
            showToast(T.saved, 'success');
            setTimeout(function () { location.reload(); }, 800);
          } else {
            showToast(errMsg(r.error), 'error');
          }
        }).catch(function () {
          showToast(T.netError, 'error');
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
      document.getElementById('al-keywords').value    = (d.keywords || '').replace(/\|/g, ', ');
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
      // Provincia/municipio: stashear en data-selected para que
      // updateProvChipsFromCcaa las aplique tras el fetch.
      var provEl = document.getElementById('al-provincia');
      if (provEl) provEl.dataset.selected = d.provincias || '';
      var munEl = document.getElementById('al-municipio');
      if (munEl) munEl.value = formatPipe(d.municipios || '');
      updateProvChipsFromCcaa('al');
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

    var PLACEHOLDERS = (AL.subPh) || {};
    var LABELS       = (AL.entidad) || {};
    var fallbackValor = AL.valorFallback || 'Valor';

    function updateTipoUI() {
      var tipo = tipoSel.value;
      if (tipo === 'ccaa') {
        selCol.style.display = ''; txtCol.style.display = 'none';
      } else {
        selCol.style.display = 'none'; txtCol.style.display = '';
        if (valorLbl) valorLbl.textContent = LABELS[tipo] || fallbackValor;
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
      var sp = document.getElementById('sub-provincia');
      var sm = document.getElementById('sub-municipio');
      if (sp) sp.value = '';
      if (sm) sm.value = '';
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
        if (!valor) { showToast(T.valueRequired, 'error'); return; }
        var sp = document.getElementById('sub-provincia');
        var sm = document.getElementById('sub-municipio');
        var payload = {
          edit_id:       document.getElementById('sub-edit-id').value || null,
          nombre:        document.getElementById('sub-nombre').value.trim(),
          entidad_tipo:  tipo,
          entidad_valor: valor,
          provincias:    sp ? parseCsv(sp.value) : [],
          municipios:    sm ? parseCsv(sm.value) : [],
          frecuencia:    freqSel ? freqSel.value : 'diaria',
          dia_semana:    parseInt(document.getElementById('sub-dia').value, 10) || 0,
          hora_envio:    parseInt(document.getElementById('sub-hora').value, 10) || 8,
        };
        btnGuard.disabled = true;
        api('/api/alerts/suscripcion', payload).then(function (r) {
          if (r.ok) {
            showToast(T.subSaved, 'success');
            setTimeout(function () { location.reload(); }, 800);
          } else {
            showToast(errMsg(r.error), 'error');
          }
        }).catch(function () {
          showToast(T.netError, 'error');
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
      var sp = document.getElementById('sub-provincia');
      var sm = document.getElementById('sub-municipio');
      if (sp) sp.value = formatPipe(d.provincias || '');
      if (sm) sm.value = formatPipe(d.municipios || '');
      openForm();
    });
  }

  // ── Acciones comunes (toggle, eliminar, probar) ───────────────────────────
  function initActions() {
    document.addEventListener('change', function (e) {
      var chk = e.target.closest('.alerta-toggle');
      if (!chk) return;
      var id = chk.dataset.id;
      api('/api/alerts/' + id + '/toggle', {}).then(function (r) {
        var item = document.querySelector('.lm-alertas-item[data-id="' + id + '"]');
        if (r.ok && item) item.classList.toggle('lm-ai-inactive', !r.activa);
        else if (!r.ok) showToast(T.toggleError, 'error');
      });
    });

    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.btn-probar');
      if (!btn) return;
      var id = btn.dataset.id;
      var orig = btn.innerHTML;
      btn.disabled = true; btn.textContent = AL.sending || '…';
      fetch('/api/alerts/' + id + '/probar', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (r) {
          if (r.ok) showToast(fmt(T.testSentShort, { count: r.count }), 'success');
          else showToast(errMsg(r.error), 'error');
        })
        .catch(function () { showToast(T.netError, 'error'); })
        .finally(function () { btn.disabled = false; btn.innerHTML = orig; });
    });

    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.btn-eliminar');
      if (!btn) return;
      var id   = btn.dataset.id;
      var item = document.querySelector('.lm-alertas-item[data-id="' + id + '"]');
      var nombre = item ? (item.querySelector('.lm-ai-nombre') || {}).textContent : '';
      if (!confirm(fmt(AL.confirmDelete, { name: nombre }))) return;
      api('/api/alerts/' + id + '/eliminar', {}).then(function (r) {
        if (r.ok && item) { item.style.opacity = '0'; setTimeout(function () { item.remove(); }, 300); }
        else showToast(T.deleteError, 'error');
      });
    });

    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.btn-unfollow');
      if (!btn) return;
      var segId = btn.dataset.segId;
      var item  = document.querySelector('.lm-watch-item[data-seg-id="' + segId + '"]');
      if (!confirm((I18N.confirm && I18N.confirm.unfollow) || '')) return;
      api('/api/alerts/watchlist/' + segId + '/eliminar', {}).then(function (r) {
        if (r.ok && item) { item.style.opacity = '0'; setTimeout(function () { item.remove(); }, 300); }
        else showToast(T.unfollowError, 'error');
      });
    });

    document.addEventListener('change', function (e) {
      var chk = e.target.closest('.watch-cambio-toggle');
      if (!chk) return;
      api('/api/alerts/watchlist/' + chk.dataset.segId + '/config',
          { notif_cambio_estado: chk.checked });
    });

    document.addEventListener('change', function (e) {
      var sel = e.target.closest('.lm-watch-dias-select');
      if (!sel) return;
      var val = sel.value === 'None' || sel.value === '' ? null : parseInt(sel.value, 10);
      api('/api/alerts/watchlist/' + sel.dataset.segId + '/config',
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
        var f    = LMFilters.get();
        var wrap = document.getElementById('form-alerta-wrap');
        if (!wrap) return;

        // Abrir formulario y resetear
        wrap.style.display = '';
        document.getElementById('alerta-edit-id').value    = '';
        document.getElementById('al-nombre').value         = '';
        document.getElementById('al-keywords').value       = '';
        document.getElementById('al-cpv').value            = '';
        document.getElementById('al-solo-activas').checked = false;
        var freqSel2 = document.getElementById('al-frecuencia');
        if (freqSel2) freqSel2.value = 'diaria';
        document.getElementById('al-dia').value  = '0';
        document.getElementById('al-hora').value = '8';
        var diaCol2 = document.getElementById('al-dia-col');
        if (diaCol2) diaCol2.style.display = 'none';

        // Aplicar chips de filtros activos
        clearChips('al-ccaa'); clearChips('al-tipo'); clearChips('al-estado');
        setChipVals('al-tipo',   f.tipo   ? f.tipo.split('|').filter(Boolean)   : []);
        setChipVals('al-ccaa',   f.ccaa   ? f.ccaa.split('|').filter(Boolean)   : []);
        setChipVals('al-estado', f.estado ? f.estado.split('|').filter(Boolean) : []);

        // Provincia + municipio del sidebar (valores únicos en la búsqueda).
        // Stasheamos en data-selected y en el input de municipio; el fetch
        // de provincias-by-ccaa rehidrata los chips tras el render.
        var provEl = document.getElementById('al-provincia');
        if (provEl) provEl.dataset.selected = f.provincia || '';
        var munEl = document.getElementById('al-municipio');
        if (munEl) munEl.value = f.municipio || '';
        updateProvChipsFromCcaa('al');

        // Traducir prange → presmin/presmax
        var PRANGE = { '5k': [null, 5000], '15k': [5000, 15000],
                       '100k': [15000, 100000], '1m': [100000, 1000000], '1m+': [1000000, null] };
        var pranges = f.prange ? f.prange.split('|').filter(Boolean) : [];
        var pmin = null, pmax = null;
        pranges.forEach(function (p) {
          var r = PRANGE[p]; if (!r) return;
          if (r[0] !== null && (pmin === null || r[0] < pmin)) pmin = r[0];
          if (r[1] !== null && (pmax === null || r[1] > pmax)) pmax = r[1];
        });
        document.getElementById('al-presmin').value = pmin !== null ? pmin : '';
        document.getElementById('al-presmax').value = pmax !== null ? pmax : '';

        wrap.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
    }
  }

  // ── Filtro watchlist ──────────────────────────────────────────────────────
  function initWatchlistFilter() {
    var input = document.getElementById('watchlist-filter');
    if (!input) return;
    input.addEventListener('input', function () {
      var q = input.value.trim().toLowerCase();
      document.querySelectorAll('#watchlist .lm-watch-item').forEach(function (item) {
        var titulo = (item.querySelector('.lm-watch-titulo') || {}).textContent || '';
        item.style.display = (!q || titulo.toLowerCase().indexOf(q) >= 0) ? '' : 'none';
      });
    });
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    initChipPickers();
    initGlobalSidebar();
    initNl();
    initAlertaForm();
    initSubForm();
    initActions();
    initWatchlistFilter();
    // Progressive disclosure CCAA → provincia → municipio en newsletter y
    // custom alert. Se engancha después de initChipPickers para evitar que
    // el listener de toggle corra antes que el nuestro.
    initGeoDisclosure('nl');
    initGeoDisclosure('al');
  });

})();
