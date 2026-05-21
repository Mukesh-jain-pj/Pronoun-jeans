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

  function parseBreakdown(str) {
    const map = {};
    if (!str) return map;
    str.split(',').forEach(function (part) {
      const m = part.trim().match(/^(\d+)x(.+)$/);
      if (m) map[m[2].trim()] = parseInt(m[1], 10);
    });
    return map;
  }

  function buildBreakdownString(builderEl) {
    const parts = [];
    builderEl.querySelectorAll('.sb-pill').forEach(function (pill) {
      const qty  = parseInt(pill.querySelector('.sb-qty').value, 10);
      const size = pill.dataset.size;
      if (qty > 0) parts.push(qty + 'x' + size);
    });
    return parts.join(', ');
  }

  // ── Check if we are on the SizeSet page ───────────────────────────────────
  function isSizeSetPage() {
    return window.location.href.includes('/products/sizeset/');
  }

  // ── Update the read-only Name field ──────────────────────────────────────
  function updateNameField() {
    const nameInput = document.getElementById('id_name');
    const fromSel   = document.getElementById('sb-from-select');
    const toSel     = document.getElementById('sb-to-select');
    if (!nameInput || !fromSel || !toSel) return;
    nameInput.value = (fromSel.value && toSel.value)
      ? fromSel.value + ' TO ' + toSel.value
      : '';
  }

  function getCurrentMembers() {
    const fromSel = document.getElementById('sb-from-select');
    const toSel   = document.getElementById('sb-to-select');
    if (!fromSel || !toSel) return [];
    return getMembersBetween(fromSel.value, toSel.value);
  }

  // ── Render pill quantity selects into a breakdown_string input ────────────
  function renderBuilderIntoInput(inputEl, members) {
    if (!inputEl) return;

    // Remove existing builder
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
    builder.style.cssText = 'display:inline-flex;flex-wrap:wrap;gap:5px;align-items:center;padding:2px 0;';

    members.forEach(function (size) {
      const pill = document.createElement('span');
      pill.className    = 'sb-pill';
      pill.dataset.size = size;
      pill.style.cssText = [
        'display:inline-flex', 'align-items:center', 'gap:3px',
        'background:#f3f4f6', 'border:1px solid #d1d5db',
        'border-radius:6px', 'padding:2px 7px', 'font-size:12px',
      ].join(';');

      const lbl = document.createElement('span');
      lbl.textContent   = size + ':';
      lbl.style.cssText = 'font-weight:600;color:#374151;white-space:nowrap;';

      const sel = document.createElement('select');
      sel.className = 'sb-qty';
      sel.style.cssText = 'border:none;background:transparent;font-size:12px;font-weight:700;color:#111827;cursor:pointer;padding:0 2px;outline:none;max-width:40px;';

      for (let i = 0; i <= 5; i++) {
        const opt       = document.createElement('option');
        opt.value       = i;
        opt.textContent = i;
        const defaultQty = existing_qtys[size] !== undefined ? existing_qtys[size] : 1;
        if (i === defaultQty) opt.selected = true;
        sel.appendChild(opt);
      }

      sel.addEventListener('change', function () {
        // Sync to the hidden input
        const str = buildBreakdownString(builder);
        inputEl.value = str;
        // Also sync label field in the same row
        const row      = inputEl.closest('tr, .form-row, div');
        const labelInp = row ? row.querySelector('input[name*="label"]') : null;
        if (labelInp) labelInp.value = str;
      });

      pill.appendChild(lbl);
      pill.appendChild(sel);
      builder.appendChild(pill);
    });

    inputEl.parentNode.insertBefore(builder, inputEl.nextSibling);

    // Initial sync
    const str = buildBreakdownString(builder);
    inputEl.value = str;
    const row      = inputEl.closest('tr, .form-row, div');
    const labelInp = row ? row.querySelector('input[name*="label"]') : null;
    if (labelInp) labelInp.value = str;
  }

  // ── Refresh all breakdown_string inputs ───────────────────────────────────
  function refreshAllBreakdownBuilders() {
    const members = getCurrentMembers();
    document.querySelectorAll(
      'input[id*="breakdown_string"], input[name*="breakdown_string"]'
    ).forEach(function (inputEl) {
      renderBuilderIntoInput(inputEl, members);
    });
  }

  // ── Inject From/To dropdowns above the Name field ─────────────────────────
  function injectFromToDropdowns() {
    const nameInput = document.getElementById('id_name');
    if (!nameInput || document.getElementById('sb-from-select')) return;

    // Make name read-only
    nameInput.readOnly = true;
    nameInput.style.background = '#f9fafb';
    nameInput.style.color      = '#9ca3af';
    nameInput.style.cursor     = 'not-allowed';

    // Parse existing name to pre-select From/To when editing
    const existingName = nameInput.value.trim();
    let existingFrom = '', existingTo = '';
    const match = existingName.match(/^(.+)\s+TO\s+(.+)$/i);
    if (match) {
      existingFrom = match[1].trim();
      existingTo   = match[2].trim();
    }

    function makeSelect(id, preselect) {
      const sel = document.createElement('select');
      sel.id    = id;
      sel.style.cssText = [
        'border:1px solid #d1d5db', 'border-radius:6px',
        'padding:6px 10px', 'font-size:13px',
        'background:#fff', 'cursor:pointer',
        'min-width:100px', 'font-family:inherit',
      ].join(';');
      const blank       = document.createElement('option');
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
      const lbl = document.createElement('label');
      lbl.textContent   = text;
      lbl.style.cssText = 'font-weight:600;font-size:13px;color:#374151;margin-right:4px;';
      return lbl;
    }

    const wrapper = document.createElement('div');
    wrapper.style.cssText = 'display:inline-flex;align-items:center;gap:8px;margin-bottom:8px;';

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

    nameInput.parentNode.insertBefore(wrapper, nameInput);
  }

  // ── Watch for new inline rows added via "Add another" ────────────────────
  function observeNewRows() {
    const observer = new MutationObserver(function () {
      const members = getCurrentMembers();
      document.querySelectorAll(
        'input[id*="breakdown_string"], input[name*="breakdown_string"]'
      ).forEach(function (inputEl) {
        if (inputEl.dataset.sbAttached) return;
        inputEl.dataset.sbAttached = '1';
        renderBuilderIntoInput(inputEl, members);
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  // ── Boot ──────────────────────────────────────────────────────────────────
  function initSizeSetPage() {
    injectFromToDropdowns();
    refreshAllBreakdownBuilders();
    observeNewRows();
  }

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