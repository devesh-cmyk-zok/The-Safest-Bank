// Shared by every customer page. All data comes from Django's same-origin /api/ gateway;
// the browser never sees the fraud engine or its key. Text is always set with
// textContent / el() so nothing from the server is parsed as HTML.
(function () {
  const csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || '';

  function detailText(detail) {
    if (!detail) return '';
    if (typeof detail === 'string') return detail;
    if (detail.message) return detail.message;
    if (Array.isArray(detail)) return detail.map((d) => d.msg || String(d)).join('; ');
    return 'Request failed';
  }

  async function request(method, path, body) {
    const res = await fetch('/api/' + path, {
      method,
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 401) {
      window.location.href = '/login/?next=' + encodeURIComponent(window.location.pathname);
    }
    if (!res.ok) {
      const err = new Error(detailText(data.detail) || `Request failed (${res.status})`);
      err.status = res.status;
      err.detail = data.detail;
      throw err;
    }
    return data;
  }

  // Engine status -> what the customer sees. tone matches the CSS classes safe/review/blocked.
  const STATUS = {
    SETTLED: { label: 'Completed', tone: 'safe' },
    ESCROW_HELD: { label: 'On hold', tone: 'review' },
    AUTO_ABORTED: { label: 'Declined', tone: 'blocked' },
    CANCELLED: { label: 'Cancelled', tone: 'review' },
    BLOCKED_BY_SOC: { label: 'Blocked by security', tone: 'blocked' },
  };

  // el('div', {class: 'x'}, 'text', childNode) — safe DOM builder (strings become text nodes).
  function el(tag, props, ...children) {
    const node = document.createElement(tag);
    Object.entries(props || {}).forEach(([k, v]) => {
      if (k === 'class') node.className = v;
      else if (k === 'dataset') Object.assign(node.dataset, v);
      else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v);
    });
    children.flat(Infinity).forEach((c) => { if (c != null) node.append(c instanceof Node ? c : String(c)); });
    return node;
  }

  const inr = (n) => '₹' + Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const signedInr = (tx) => (tx.direction === 'in' ? '+' : '−') + inr(tx.amount);
  const counterparty = (tx) => (tx.direction === 'in' ? tx.sender_name : tx.recipient_name);
  const when = (iso) => {
    const d = new Date(iso);
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) + ' · ' +
      d.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' });
  };
  const accountMask = (userId) => 'Account •••• ' + String(userId || '').replace(/\D/g, '').slice(-4);

  let toastTimer;
  function toast(msg, tone) {
    const t = document.getElementById('toast');
    if (!t) return;
    document.getElementById('toastMsg').textContent = msg;
    const colors = { blocked: 'var(--blocked)', review: 'var(--review)' };
    t.querySelector('.dot').style.background = colors[tone] || 'var(--safe)';
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 3800);
  }

  // Balance show/hide: <span data-balance> + <button data-balance-toggle> (hidden by default).
  const EYE = '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>';
  let balanceVisible = false;
  function renderBalances() {
    document.querySelectorAll('[data-balance]').forEach((node) => {
      node.textContent = balanceVisible && node.dataset.value ? node.dataset.value : '₹ ••••••••';
    });
    document.querySelectorAll('[data-balance-toggle]').forEach((btn) => {
      btn.setAttribute('aria-label', balanceVisible ? 'Hide balance' : 'Show balance');
      const svg = btn.querySelector('svg');
      if (svg) svg.innerHTML = balanceVisible ? EYE : EYE + '<path d="M4 4l16 16" stroke-linecap="round"/>';
    });
  }
  document.querySelectorAll('[data-balance-toggle]').forEach((btn) => btn.addEventListener('click', () => {
    balanceVisible = !balanceVisible;
    renderBalances();
  }));

  // Mobile drawer
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  const setDrawer = (open) => {
    if (sidebar) sidebar.classList.toggle('open', open);
    if (backdrop) backdrop.classList.toggle('show', open);
  };
  const on = (id, fn) => { const n = document.getElementById(id); if (n) n.addEventListener('click', fn); };
  on('hamburgerBtn', () => setDrawer(true));
  on('sidebarCloseBtn', () => setDrawer(false));
  on('sidebarBackdrop', () => setDrawer(false));

  const bank = {
    get: (path) => request('GET', path),
    post: (path, body) => request('POST', path, body || {}),
    STATUS, el, inr, signedInr, counterparty, when, accountMask, toast,
    demoMode: document.body.dataset.demoMode === 'true',
    me: null,
  };
  // Every page shows the balance; load the profile once and fill [data-balance].
  bank.ready = bank.get('me/').then((me) => {
    bank.me = me;
    document.querySelectorAll('[data-balance]').forEach((node) => { node.dataset.value = inr(me.balance); });
    document.querySelectorAll('[data-account-mask]').forEach((node) => { node.textContent = accountMask(me.user_id); });
    renderBalances();
    return me;
  });
  bank.ready.catch((err) => toast(err.message, 'blocked'));
  bank.refreshBalance = () => bank.get('me/').then((me) => {
    bank.me = me;
    document.querySelectorAll('[data-balance]').forEach((node) => { node.dataset.value = inr(me.balance); });
    renderBalances();
    return me;
  });
  window.bank = bank;
  renderBalances();
})();
