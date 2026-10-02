// SOC shared behaviour: toast, investigation panel, analyst actions.
// Data is rendered with textContent via el(); nothing from the server is parsed as HTML.
(function () {
  const csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || '';
  const $ = (id) => document.getElementById(id);

  function el(tag, props, ...children) {
    const node = document.createElement(tag);
    Object.entries(props || {}).forEach(([k, v]) => {
      if (k === 'class') node.className = v;
      else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v);
    });
    children.flat(Infinity).forEach((c) => { if (c != null && c !== false) node.append(c instanceof Node ? c : String(c)); });
    return node;
  }

  function toast(msg, type) {
    const t = el('div', { class: `soc-toast ${type || 'info'}` }, msg);
    $('soc-toast-container').append(t);
    setTimeout(() => t.remove(), 3800);
  }

  async function api(path, body) {
    const res = await fetch(path, body === undefined ? { credentials: 'same-origin' } : {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof data.error === 'string' ? data.error : `Request failed (${res.status})`);
    return data;
  }

  const levelClass = (level) => (level || 'low').toLowerCase();

  function renderPanel(t) {
    const rows = (pairs) => el('div', { class: 'soc-detail-grid' }, pairs.map(([label, value, full]) =>
      el('div', { class: 'soc-detail-item' + (full ? ' full' : '') },
        el('div', { class: 'label' }, label), el('div', { class: 'value' }, value))));

    const why = t.why.length
      ? el('div', { class: 'soc-shap-list' }, t.why.map((w) => el('div', { class: 'soc-shap-item' },
          el('div', { class: 'soc-shap-row' }, el('span', { class: 'soc-shap-name' }, w.name),
            el('span', { class: 'soc-shap-pct' }, `+${w.points} pts`)),
          el('div', { class: 'soc-shap-bar-bg' }, el('div', { class: 'soc-shap-bar-fill', style: `width:${Math.min(100, w.points * 3)}%` })))))
      : el('p', { class: 'soc-empty' }, 'No rule signals fired.');

    const context = el('div', { class: 'soc-context' }, t.context.map(([k, v, risky]) =>
      [el('span', { class: 'k' }, k), el('span', { class: 'v' + (risky ? ' risky' : '') }, v)]));

    const held = t.status === 'ESCROW_HELD';
    const note = el('textarea', { class: 'soc-note', id: 'panelNote', placeholder: 'Note for the audit log (e.g. called customer, confirmed)', 'aria-label': 'Analyst note' });
    const actions = el('div', { class: 'soc-action-row' },
      held && el('button', { class: 'soc-btn soc-btn-success soc-btn-sm', onclick: () => act(t.id, 'RELEASE') }, 'Release to recipient'),
      held && el('button', { class: 'soc-btn soc-btn-danger soc-btn-sm', onclick: () => act(t.id, 'REFUND') }, 'Block & refund sender'),
      el('button', { class: 'soc-btn soc-btn-purple soc-btn-sm', onclick: () => act(t.id, 'CASE') }, 'Open case'));

    $('panelBody').replaceChildren(
      el('div', { class: `soc-risk-large ${levelClass(t.risk_level)}` },
        el('div', {},
          el('div', { class: 'label' }, 'RISK SCORE'),
          el('div', { class: 'score' }, String(t.score), el('span', { class: 'of' }, ' / 100'))),
        el('div', { style: 'margin-left:auto;text-align:right;' },
          el('span', { class: `soc-badge ${levelClass(t.risk_level)}` }, t.risk_level),
          el('div', { class: 'label', style: 'margin-top:6px;' }, `model ${Math.round((t.nn_score || 0) * 100)} · rules ${Math.round((t.rule_score || 0) * 100)}`))),
      rows([
        ['Transaction', t.id], ['Status', t.status_label],
        ['From', `${t.sender_name} (${t.sender_id})`], ['To', `${t.recipient_name} (${t.recipient_id})`],
        ['Amount', t.amount_display], ['When', new Date(t.created_at).toLocaleString('en-IN')],
        t.resolved_by ? ['Resolved by', `${t.resolved_by}${t.resolution_note ? ' — ' + t.resolution_note : ''}`, true] : null,
      ].filter(Boolean)),
      t.simulated ? el('p', { class: 'soc-honest' }, 'Created with the demo Simulate panel: some signals were injected.') : null,
      el('div', { class: 'soc-divider' }),
      el('h3', { class: 'soc-section-label' }, 'Why it scored this way (rule points)'),
      why,
      el('div', { class: 'soc-divider' }),
      el('h3', { class: 'soc-section-label' }, 'Signals'),
      context,
      el('div', { class: 'soc-divider' }),
      note,
      actions);
  }

  async function openPanel(txId) {
    $('panelBody').replaceChildren(el('div', { class: 'soc-empty' }, 'Loading…'));
    $('investigationPanel').classList.add('open');
    $('panelOverlay').classList.add('open');
    try {
      renderPanel(await api(`/soc/api/transaction/${encodeURIComponent(txId)}/`));
      $('panelClose').focus();
    } catch (err) {
      $('panelBody').replaceChildren(el('div', { class: 'soc-empty' }, err.message));
    }
  }

  function closePanel() {
    $('investigationPanel').classList.remove('open');
    $('panelOverlay').classList.remove('open');
  }

  async function act(txId, action) {
    const noteEl = $('panelNote');
    const note = noteEl ? noteEl.value.trim() : '';
    const verbs = { RELEASE: 'release these funds to the recipient', REFUND: 'block this transfer and refund the sender' };
    if (verbs[action] && !window.confirm(`Are you sure you want to ${verbs[action]}? This moves real balances.`)) return;
    try {
      const res = await api(`/soc/api/transaction/${encodeURIComponent(txId)}/action/`, { action, note });
      toast(action === 'CASE' ? `Opened ${res.case_id}` : `${txId}: ${res.status_label}`, 'success');
      closePanel();
      setTimeout(() => window.location.reload(), 600);
    } catch (err) {
      toast(err.message, 'error');
    }
  }

  $('panelOverlay').addEventListener('click', closePanel);
  $('panelClose').addEventListener('click', closePanel);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closePanel(); });
  // Any element with data-open-tx="<id>" opens the panel (rows, buttons).
  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('[data-open-tx]');
    if (trigger) openPanel(trigger.dataset.openTx);
  });
  document.addEventListener('keydown', (e) => {
    const trigger = e.target.closest && e.target.closest('tr[data-open-tx]');
    if (trigger && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); openPanel(trigger.dataset.openTx); }
  });

  window.soc = { el, toast, api, openPanel, act };
})();
