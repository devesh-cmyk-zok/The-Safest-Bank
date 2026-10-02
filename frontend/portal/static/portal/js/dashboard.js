// Dashboard: Fraud Shield summary + recent transactions, all from /api/.
(function () {
  const { el, STATUS } = window.bank;
  const ICON = {
    safe: '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 20c0-3.6 3.1-6.5 7-6.5s7 2.9 7 6.5"/>',
    review: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    blocked: '<path d="M12 3l9.5 17H2.5L12 3z"/><path d="M12 10v4"/><circle cx="12" cy="17.3" r="0.6" fill="currentColor" stroke="none"/>',
  };
  let rows = [];
  let filter = 'all';

  function icon(tone) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.innerHTML = ICON[tone]; // static markup, no data
    return svg;
  }

  function render() {
    const list = document.getElementById('txList');
    const shown = rows.filter((tx) => filter === 'all' || STATUS[tx.status].tone === filter).slice(0, 6);
    list.replaceChildren(...shown.map((tx) => {
      const s = STATUS[tx.status];
      return el('a', { class: `tx-item ${s.tone}`, href: '/transactions/#' + tx.id },
        el('div', { class: 'tx-left' },
          el('div', { class: `tx-icon ${s.tone}` }, icon(s.tone)),
          el('div', {},
            el('div', { class: 'tx-name' }, (tx.direction === 'in' ? 'From ' : 'To ') + window.bank.counterparty(tx)),
            el('div', { class: 'tx-meta' }, window.bank.when(tx.created_at)))),
        el('div', { class: 'tx-right' },
          el('div', { class: 'tx-amt' }, window.bank.signedInr(tx)),
          el('span', { class: `badge ${s.tone}` }, el('span', { class: 'dot' }), s.label)));
    }));
    document.getElementById('txEmpty').style.display = shown.length ? 'none' : '';
  }

  document.querySelectorAll('.filter-tab').forEach((tab) => tab.addEventListener('click', () => {
    document.querySelectorAll('.filter-tab').forEach((t) => t.classList.toggle('active', t === tab));
    filter = tab.dataset.filter;
    render();
  }));

  Promise.all([window.bank.ready, window.bank.get('transactions/')]).then(([me, txs]) => {
    rows = txs;
    render();
    const held = txs.filter((t) => t.status === 'ESCROW_HELD').length;
    document.getElementById('scHeld').textContent = held ? `${held} awaiting you` : 'None';
    document.getElementById('scDevices').textContent = String(me.known_devices);
    const mine = txs.find((t) => t.direction === 'out');
    document.getElementById('scLast').textContent = mine ? window.bank.when(mine.created_at) : 'No transfers yet';
    if (held) {
      document.getElementById('shieldPillText').textContent = 'ACTION NEEDED';
      document.getElementById('shieldPill').classList.add('attention');
    }
  }).catch((err) => window.bank.toast(err.message, 'blocked'));
})();
