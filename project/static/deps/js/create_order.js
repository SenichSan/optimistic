/* create_order.js: behaviors for the checkout page */
(function() {
  // Lightweight logger (enable via window.__NP_DEBUG=true)
  function npLog() { try { if (window.__NP_DEBUG) console.log.apply(console, arguments); } catch(_) {} }
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function formatCurrency(n) {
    const val = Math.round(Number(n) || 0).toString();
    return val + ' ₴';
  }

  function parseNum(val) {
    if (val == null) return 0;
    if (typeof val === 'number') return val;
    const s = String(val)
      .replace(/[^0-9,\.\-]/g, '') // strip currency, spaces, nbsp
      .replace(',', '.');
    const n = parseFloat(s);
    return isNaN(n) ? 0 : n;
  }

  function initCommentPlaceholder() {
    const ta = document.getElementById('order_comment');
    if (!ta) return;
    // keep original placeholder
    const original = ta.getAttribute('placeholder') || '';
    ta.dataset.placeholder = original;
    ta.addEventListener('focus', function() {
      // hide placeholder immediately on focus
      ta.setAttribute('placeholder', '');
    });
    ta.addEventListener('blur', function() {
      if (!ta.value.trim()) {
        ta.setAttribute('placeholder', ta.dataset.placeholder || original);
      }
    });
  }

  function formatUaPhone(digits) {
    // Normalize to UA format starting with 380 and total 12 digits (380 + 9)
    if (!digits) return '';
    // Convert common inputs to 380XXXXXXXXX
    if (digits[0] === '0' && digits.length >= 10) {
      digits = '380' + digits.slice(1);
    } else if (digits.startsWith('80') && digits.length >= 11) {
      digits = '3' + digits; // 380...
    } else if (!digits.startsWith('380')) {
      // If user started typing without country code, prepend progressively
      if (digits.length <= 9) digits = '380' + digits.padStart(9, '');
    }
    // Keep only first 12 digits
    digits = digits.replace(/\D/g, '').slice(0, 12);
    // If we still don't have 380 prefix, bail with raw
    if (!digits.startsWith('380')) return '+' + digits;

    // Build +380 XX XXX XX XX
    const c = '+380';
    const op = digits.slice(3, 5);
    const p1 = digits.slice(5, 8);
    const p2 = digits.slice(8, 10);
    const p3 = digits.slice(10, 12);
    let out = c;
    if (op) out += ' ' + op;
    if (p1) out += ' ' + p1;
    if (p2) out += ' ' + p2;
    if (p3) out += ' ' + p3;
    return out;
  }

  function isValidUaPhone(val) {
    return /^\+?380\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}$/.test(val.trim());
  }

  function initPhoneMask() {
    const input = document.getElementById('id_phone_number');
    if (!input) return;
    const err = document.getElementById('phone_number_error');

    function updateMaskFromRaw() {
      const rawDigits = input.value.replace(/\D/g, '');
      const formatted = formatUaPhone(rawDigits);
      input.value = formatted;
    }

    function showError(show) {
      if (!err) return;
      err.style.display = show ? '' : 'none';
      if (show) input.classList.add('is-invalid'); else input.classList.remove('is-invalid');
    }

    input.addEventListener('input', function() {
      const pos = input.selectionStart;
      updateMaskFromRaw();
      // Best-effort caret keep near end
      input.setSelectionRange(input.value.length, input.value.length);
      if (isValidUaPhone(input.value)) showError(false);
    });

    input.addEventListener('blur', function() {
      if (!input.value.trim()) { showError(false); return; }
      if (!isValidUaPhone(input.value)) showError(true); else showError(false);
    });

    const form = document.getElementById('create_order_form');
    if (form) {
      form.addEventListener('submit', function(e) {
        if (!isValidUaPhone(input.value)) {
          showError(true);
          e.preventDefault();
          e.stopPropagation();
          input.focus();
        }
      });
    }

    // Initialize once on load
    updateMaskFromRaw();
  }

  function initEmailValidation() {
    const email = document.getElementById('id_email');
    if (!email) return;
    function toggle() {
      if (!email.value) { email.classList.remove('is-invalid'); return; }
      if (email.checkValidity()) email.classList.remove('is-invalid');
      else email.classList.add('is-invalid');
    }
    email.addEventListener('blur', toggle);
    email.addEventListener('input', function(){ if (email.classList.contains('is-invalid')) toggle(); });
  }

  function recalcTotals() {
    let total = 0;
    let totalDiscount = 0;

    document.querySelectorAll('.order-item-row').forEach(function(row) {
      const qtyEl = row.querySelector('.qty-value');
      const qty = parseNum(qtyEl ? qtyEl.textContent.trim() : row.dataset.quantity);
      const unit = parseNum(row.dataset.unitPrice || row.getAttribute('data-unit-price'));
      let sell = parseNum(row.dataset.sellPrice || row.getAttribute('data-sell-price'));
      if (!sell) {
        // try to read from DOM new price
        const newPriceEl = row.querySelector('.unit-price .new-price');
        if (newPriceEl) sell = parseNum(newPriceEl.textContent);
      }
      if (!sell) {
        const discountPct = parseNum(row.dataset.discount || row.getAttribute('data-discount'));
        if (discountPct) sell = Math.max(0, unit - unit * (discountPct / 100));
        else sell = unit;
      }
      const lineSum = sell * qty;
      const perUnitDiscount = Math.max(0, unit - sell);
      total += lineSum;
      totalDiscount += perUnitDiscount * qty;
      const lineSumCell = row.querySelector('.line-sum');
      if (lineSumCell) lineSumCell.textContent = formatCurrency(lineSum);
    });

    const totalCell = document.querySelector('.table-total td.text-end:last-child, .table-total td:last-child');
    if (totalCell) {
      const strong = totalCell.querySelector('strong');
      const val = formatCurrency(total);
      if (strong) strong.textContent = val; else totalCell.textContent = val;
    }

    const discountEl = document.getElementById('order-total-discount');
    if (discountEl) discountEl.textContent = formatCurrency(totalDiscount);
  }

  function bindQtyButtons() {
    const container = document.querySelector('.checkout-order-summary');
    if (!container) return;
    const changeUrl = container.getAttribute('data-cart-change-url');
    if (!changeUrl) return;

    container.addEventListener('click', function(e) {
      const incBtn = e.target.closest('.order-qty-inc');
      const decBtn = e.target.closest('.order-qty-dec');
      if (!incBtn && !decBtn) return;
      const row = e.target.closest('.order-item-row');
      if (!row) return;
      const cartId = row.getAttribute('data-cart-id');
      if (!cartId) return;

      const action = incBtn ? 'increment' : 'decrement';
      const csrftoken = getCookie('csrftoken');
      fetch(changeUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
          'X-CSRFToken': csrftoken
        },
        body: new URLSearchParams({ cart_id: cartId, action })
      }).then(function(res) { return res.json(); })
        .then(function(_data) {
          // Update UI locally based on action
          const qtyEl = row.querySelector('.qty-value');
          let qty = Number(qtyEl.textContent.trim()) || 0;
          if (action === 'increment') qty += 1; else qty -= 1;
          if (qty <= 0) {
            row.remove();
          } else {
            qtyEl.textContent = String(qty);
            row.setAttribute('data-quantity', String(qty));
          }
          recalcTotals();
        })
        .catch(function() {
          // no-op; keep UI unchanged on error
        });
    });
  }

  function initNovaPoshta() {
    const $ = window.jQuery;
    if (!$) return;
    const ENDPOINT_SEARCH_CITY = "/orders/ajax/search-city/";
    const ENDPOINT_GET_WAREHOUSES = "/orders/ajax/get-warehouses/";
    let selectedCity = "";
    let inflightSearch = null; // ссылка на активный поиск города
    let lastQueryId = 0;       // идентификатор последнего запроса (anti-race)
    let inflightWarehouses = null;

    function debounce(fn, wait) { let t=null; return function(){ const ctx=this,args=arguments; clearTimeout(t); t=setTimeout(function(){ fn.apply(ctx,args); }, wait); }; }

    function requestCities(term, responseCb) {
      const q = String(term || '').trim();
      if (q.length < 2) { responseCb([]); return; }
      const queryId = ++lastQueryId;
      // Abort previous city search to avoid dangling network on mobile
      if (inflightSearch && inflightSearch.readyState !== 4) {
        try { inflightSearch.abort(); } catch(_) {}
      }
      inflightSearch = $.ajax({
        url: ENDPOINT_SEARCH_CITY,
        method: "GET",
        dataType: "json",
        timeout: 12000,
        cache: true,
        data: { q }
      }).done(function(res, textStatus, jqXHR){
        npLog('[NP][DEV] city search ok:', q, 'status=', textStatus, 'id=', queryId);
        if (queryId !== lastQueryId) { npLog('[NP][DEV] skip stale city result id=', queryId); return; }
        let list = [];
        // Формат A (backend DEV): простой массив объектов [{label, ref}] или строк
        if (Array.isArray(res)) {
          list = res.map(function(it){
            if (typeof it === 'string') return { label: it, value: it, ref: '' };
            const label = it.label || it.Present || it.name || '';
            return { label, value: label, ref: it.ref || it.Ref || it.SettlementRef || '' };
          });
        }
        // Формат B (альтернативный): { success: true, cities: [...] }
        else if (res && res.success && Array.isArray(res.cities)) {
          list = res.cities.map(function(it){
            if (typeof it === 'string') return { label: it, value: it, ref: '' };
            const label = it.label || it.Present || it.name || '';
            return { label, value: label, ref: it.ref || it.Ref || it.SettlementRef || '' };
          });
        }
        responseCb(list);
      }).fail(function(jqXHR, textStatus, errorThrown){
        // Если был abort браузером — это нормально при быстрым вводе; пропускаем
        npLog('[NP][DEV] city search fail:', 'status=', textStatus, 'err=', errorThrown, 'id=', queryId);
        if (queryId !== lastQueryId) { return; }
        responseCb([]);
      });
    }
    const fetchCitiesDebounced = debounce(requestCities, 250);
    window.__NP_fetchCitiesDebounced = fetchCitiesDebounced; // for console tests

    $(function() {
      npLog('[NP][DEV] init start');
      $("#nova_city").autocomplete({
        minLength: 2,
        source: function(request, response) {
          const term = String(request.term || '').trim();
          npLog('[NP][DEV] ac.source term=', term);
          if (term.length < 2) { response([]); return; }
          fetchCitiesDebounced(term, response);
        },
        select: function(event, ui) {
          npLog('[NP][DEV] ac.select item=', ui && ui.item);
          $('#nova_city_ref').val(ui.item.ref);
          selectedCity = ui.item.label;
          $('#nova_city').val(selectedCity);

          const $w = $('#warehouse_display');
          if ($w.hasClass('select2-hidden-accessible')) { try { $w.select2('destroy'); } catch(_) {} }
          // plain select in loading state; select2 будет инициализирован ТОЛЬКО после успешной загрузки
          $w.empty().prop('disabled', true).append(new Option('Завантаження...', ''));

          if (inflightWarehouses && inflightWarehouses.readyState !== 4) { try { inflightWarehouses.abort(); } catch(_) {} }

          // Helper: do a robust warehouses fetch with retry and longer timeout
          function loadWarehousesWithRetry(settlementRef, attempt) {
            const tries = attempt || 1;
            const timeoutMs = tries === 1 ? 15000 : 20000; // чуть больше на первой загрузке Киева
            inflightWarehouses = $.ajax({
              url: ENDPOINT_GET_WAREHOUSES,
              method: "GET",
              dataType: "json",
              timeout: timeoutMs,
              cache: false,
              data: { settlement_ref: settlementRef, _ts: Date.now() } // cache-bust for first Kyiv
            }).done(function(res){
              npLog('[NP][DEV] warehouses ok:', res);
              const list = (res && res.success && Array.isArray(res.warehouses)) ? res.warehouses : [];
              $w.empty();
              if (list.length === 0 && tries === 1 && /^київ$/i.test(selectedCity)) {
                // Special-case: try to refine ref for Kyiv and retry once
                npLog('[NP][DEV] empty list for Kyiv, refining ref...');
                if (inflightSearch && inflightSearch.readyState !== 4) { try { inflightSearch.abort(); } catch(_){} }
                inflightSearch = $.ajax({
                  url: ENDPOINT_SEARCH_CITY,
                  method: 'GET', dataType: 'json', timeout: 10000, cache: false,
                  data: { q: selectedCity }
                }).done(function(r){
                  const arr = Array.isArray(r) ? r : (r && r.cities) || [];
                  const norm = (s)=>String(s||'').trim().toLowerCase();
                  // Prefer exact 'Київ' or startsWith 'Київ,'
                  let foundRef = '';
                  for (let i=0;i<arr.length;i++){
                    const it = arr[i]; const label = it && (it.label || it.Present || it.name || '');
                    if (norm(label) === 'київ' || norm(label).startsWith('київ,')) { foundRef = it.ref || it.Ref || it.SettlementRef || '';
                      break; }
                  }
                  if (foundRef) {
                    $('#nova_city_ref').val(foundRef);
                    return loadWarehousesWithRetry(foundRef, tries + 1);
                  }
                  // fallback — show empty state
                  $w.append(new Option('Відділення не знайдені', ''));
                  $w.prop('disabled', false);
                }).fail(function(){
                  $w.append(new Option('Відділення не знайдені', ''));
                  $w.prop('disabled', false);
                });
                return; // stop normal flow; retry will handle
              }
              if (list.length === 0) { $w.append(new Option('Відділення не знайдені', '')); }
              else { list.forEach(function(desc){ $w.append(new Option(desc, desc)); }); }
              $w.prop('disabled', false);

              // Инициализируем select2 только сейчас, чтобы избежать 'no results found' до прихода данных
              $w.off('change');
              $w.select2({
                placeholder: 'Оберіть відділення',
                width: '100%',
                language: { noResults: function(){ return 'Відділення не знайдені'; } }
              });
              $w.on('change', function () {
                const warehouseText = $(this).find('option:selected').text();
                $('#id_delivery_address').val(`${selectedCity}, ${warehouseText}`);
              });
            }).fail(function(err){
              npLog('[NP][DEV] warehouses fail attempt', tries, err);
              if (tries < 2) {
                // retry once after brief delay — фикс «первого Киева»
                setTimeout(function(){ loadWarehousesWithRetry(settlementRef, tries + 1); }, 450);
              } else {
                // remove select2 to avoid lingering 'no results found', show plain error option
                if ($w.hasClass('select2-hidden-accessible')) { try { $w.select2('destroy'); } catch(_) {} }
                $w.empty().prop('disabled', false).append(new Option('Помилка завантаження відділень', ''));
              }
            });
          }

          // Ensure we have a settlement_ref; if missing (иногда по Киеву), resolve by exact match
          let ref = ui.item && (ui.item.ref || ui.item.Ref || ui.item.SettlementRef || '');
          if (!ref) {
            npLog('[NP][DEV] missing settlement_ref, resolving by exact match for', selectedCity);
            // Try to resolve the ref via search endpoint with exact label
            if (inflightSearch && inflightSearch.readyState !== 4) { try { inflightSearch.abort(); } catch(_){} }
            inflightSearch = $.ajax({
              url: ENDPOINT_SEARCH_CITY,
              method: 'GET', dataType: 'json', timeout: 10000, cache: false,
              data: { q: selectedCity }
            }).done(function(res){
              let foundRef = '';
              const arr = Array.isArray(res) ? res : (res && res.cities) || [];
              const norm = function(s){ return String(s||'').trim().toLowerCase(); };
              const target = norm(selectedCity);
              for (var i=0;i<arr.length;i++){
                const it = arr[i];
                const label = (it && (it.label || it.Present || it.name || ''));
                if (norm(label) === target || norm(label).includes(target)) { foundRef = it.ref || it.Ref || it.SettlementRef || ''; break; }
              }
              if (!foundRef && arr.length>0) {
                const it = arr[0];
                foundRef = it.ref || it.Ref || it.SettlementRef || '';
              }
              if (foundRef) {
                $('#nova_city_ref').val(foundRef);
                loadWarehousesWithRetry(foundRef, 1);
              } else {
                if ($w.hasClass('select2-hidden-accessible')) { try { $w.select2('destroy'); } catch(_) {} }
                $w.empty().prop('disabled', false).append(new Option('Відділення не знайдені', ''));
              }
            }).fail(function(){
              if ($w.hasClass('select2-hidden-accessible')) { try { $w.select2('destroy'); } catch(_) {} }
              $w.empty().prop('disabled', false).append(new Option('Помилка завантаження відділень', ''));
            });
          } else {
            loadWarehousesWithRetry(ref, 1);
          }
        }
      });
      npLog('[NP][DEV] autocomplete bound');

      $('#create_order_form').on('submit', function() {
        const city = $('#nova_city').val();
        const wh = $('#warehouse_display option:selected').text();
        if (city && wh) { $('#id_delivery_address').val(`${city}, ${wh}`); }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function() {
    bindQtyButtons();
    recalcTotals();
    initNovaPoshta();
    initCommentPlaceholder();
    initPhoneMask();
    initEmailValidation();
  });
})();
