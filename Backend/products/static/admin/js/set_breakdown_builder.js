(function () {
  'use strict';

  // ── Master size order ─────────────────────────────────────────────────────
  const ALL_SIZES = [
    'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL', '5XL',
    '26', '28', '30', '32', '34', '36', '38', '40', '42', '44', '46',
  ];

  function getMembersBetween(fromSize, toSize) {
    const fromIdx = ALL_SIZES.indexOf(fromSize);
    const toIdx   = ALL_SIZES.indexOf(toSize);
    if (fromIdx === -1 || toIdx === -1 || fromIdx > toIdx) return [];
    return ALL_SIZES.slice(fromIdx, toIdx + 1);
  }

  // ── Breakdown string helpers ──────────────────────────────────────────────
  function buildBreakdownString(builderEl) {
    const parts = [];
    builderEl.querySelectorAll('.sb-item').forEach(function (item) {
      const qty  = parseInt(item.querySelector('.sb-qty').value, 10);
      const size = item.dataset.size;
      if (qty > 0) parts.push(qty + 'x' + size);
    });
    return parts.join(', ');
  }

  function syncToInput(builderEl, inputEl) {
    inputEl.value = buildBreakdownString(builderEl);
  }

  function parseBreakdown(str) {
    const map = {};
    if (!str) return map;
    str.split(',').forEach(function (part) {
      const m = part.trim().match(/^(\d+)x(.+)$/);
      if (m) map[m[2].trim()] = parseInt(m[1], 10);
    });
    return map;
  }

  // ── Render quantity picker pills into a hidden text input ─────────────────
  function renderBuilderIntoInput(inputEl, members) {
    if (!inputEl) return;
    const existing = inputEl.parentNode.querySelector('.sb-builder');
    if (existing) existing.remove();
    if (!members || members.length === 0) {
      inputEl.style.display = '';
      return;
    }
    inputEl.style.display = 'none';
    const existing_qtys = parseBreakdown(inputEl.value);
    const builder = document.createElement('div');
    builder.className = 'sb-builder';
    builder.style.cssText = 'display:inline-flex;flex-wrap:wrap;gap:6px;align-items:center;padding:4px 0;';
    members.forEach(function (size) {
      const item = document.createElement('span');
      item.className    = 'sb-item';
      item.dataset.size = size;
      item.style.cssText = 'display:inline-flex;align-items:center;gap:3px;background:#f3f4f6;border:1px solid #d1d5db;border-radius:6px;padding:2px 6px;font-size:12px;';
      const lbl = document.createElement('span');
      lbl.textContent   = size + ':';
      lbl.style.cssText = 'font-weight:600;color:#374151;white-space:nowrap;';
      const qtySelect = document.createElement('select');
      qtySelect.className = 'sb-qty';
      qtySelect.style.cssText = 'border:none;background:transparent;font-size:12px;font-weight:700;color:#111827;cursor:pointer;padding:0 2px;outline:none;';
      for (let i = 0; i <= 5; i++) {
        const opt       = document.createElement('option');
        opt.value       = i;
        opt.textContent = i;
        if (i === (existing_qtys[size] !== undefined ? existing_qtys[size] : 1)) opt.selected = true;
        qtySelect.appendChild(opt);
      }
      qtySelect.addEventListener('change', function () { syncToInput(builder, inputEl); });
      item.appendChild(lbl);
      item.appendChild(qtySelect);
      builder.appendChild(item);
    });
    inputEl.parentNode.insertBefore(builder, inputEl.nextSibling);
    syncToInput(builder, inputEl);
  }

  // ── Refresh all breakdown_string inputs with current members ──────────────
  function getCurrentMembers() {
    const fromSel = document.getElementById('sb-from-select');
    const toSel   = document.getElementById('sb-to-select');
    if (!fromSel || !toSel) return [];
    return getMembersBetween(fromSel.value, toSel.value);
  }

  function refreshAllBreakdownBuilders() {
    const members = getCurrentMembers();
    document.querySelectorAll(
      'input[id*="breakdown_string"], input[name*="breakdown_string"]'
    ).forEach(function (inputEl) {
      delete inputEl.dataset.sbAttached;
      renderBuilderIntoInput(inputEl, members);
      inputEl.dataset.sbAttached = '1';
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // MODE: SizeSet add/edit page
  // ═══════════════════════════════════════════════════════════════════════════

  function isSizeSetPage() {
    return window.location.href.includes('/products/sizeset/');
  }

  function updateNameField() {
    const nameInput = document.getElementById('id_name');
    const fromSel   = document.getElementById('sb-from-select');
    const toSel     = document.getElementById('sb-to-select');
    if (!nameInput || !fromSel || !toSel) return;
    if (fromSel.value && toSel.value) {
      nameInput.value = fromSel.value + ' TO ' + toSel.value;
    } else {
      nameInput.value = '';
    }
  }

  function injectFromToDropdowns() {
    const nameInput = document.getElementById('id_name');
    if (!nameInput || document.getElementById('sb-from-select')) return;

    // Make name read-only
    nameInput.readOnly = true;
    nameInput.style.cssText += 'background:#f9fafb;color:#6b7280;cursor:not-allowed;';

    // Parse existing name to pre-select From/To when editing
    const existingName = nameInput.value.trim();
    let existingFrom = '', existingTo = '';
    const match = existingName.match(/^(.+)\s+TO\s+(.+)$/i);
    if (match) {
      existingFrom = match[1].trim();
      existingTo   = match[2].trim();
    }

    // Build wrapper
    const wrapper = document.createElement('div');
    wrapper.style.cssText = 'display:inline-flex;align-items:center;gap:8px;margin-bottom:8px;';

    function makeSelect(id, preselect) {
      const sel = document.createElement('select');
      sel.id = id;
      sel.style.cssText = 'border:1px solid #d1d5db;border-radius:6px;padding:4px 10px;font-size:13px;background:#fff;cursor:pointer;';
      const blank = document.createElement('option');
      blank.value       = '';
      blank.textContent = '— select —';
      sel.appendChild(blank);
      ALL_SIZES.forEach(function (size) {
        const opt       = document.createElement('option');
        opt.value       = size;
        opt.textContent = size;
        if (size === preselect) opt.selected = true;
        sel.appendChild(opt);
      });
      return sel;
    }

    function makeLabel(text) {
      const lbl = document.createElement('span');
      lbl.textContent   = text;
      lbl.style.cssText = 'font-weight:600;font-size:13px;color:#374151;';
      return lbl;
    }

    const fromSel = makeSelect('sb-from-select', existingFrom);
    const toSel   = makeSelect('sb-to-select',   existingTo);

    fromSel.addEventListener('change', function () {
      updateNameField();
      refreshAllBreakdownBuilders();
    });
    toSel.addEventListener('change', function () {
      updateNameField();
      refreshAllBreakdownBuilders();
    });

    wrapper.appendChild(makeLabel('From:'));
    wrapper.appendChild(fromSel);
    wrapper.appendChild(makeLabel('To:'));
    wrapper.appendChild(toSel);

    // Insert the From/To row above the name input
    nameInput.parentNode.insertBefore(wrapper, nameInput);
  }

  function observeForNewBreakdownRows() {
    // Watch the whole page for new breakdown_string inputs
    // (added when admin clicks "Add another Size Set Breakdown")
    const observer = new MutationObserver(function () {
      refreshAllBreakdownBuilders();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function initSizeSetPage() {
    injectFromToDropdowns();
    refreshAllBreakdownBuilders();
    observeForNewBreakdownRows();
  }

  // ── Boot ──────────────────────────────────────────────────────────────────
  function init() {
    if (isSizeSetPage()) {
      initSizeSetPage();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();