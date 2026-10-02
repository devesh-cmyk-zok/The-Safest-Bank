// ============================================================
// MOCK TRANSACTION DATA — frontend/demo only.
//
// Fields matching the known backend schema: tx_id, amount, payee_account,
// status, created_at. `label` and `category` are additional display-only
// mock fields (not assumed backend columns) used purely for a readable UI.
//
// FUTURE INTEGRATION POINT: replace MOCK_TRANSACTIONS with a real fetch()
// to a Django/DB-backed endpoint once the backend team provides one.
// created_at is generated relative to page-load time here so the Today/
// Yesterday grouping always looks correct in a live demo, regardless of
// which day it's presented on — a real backend would send absolute
// timestamps instead.
// ============================================================
function hoursAgo(h){ return new Date(Date.now() - h*3600*1000).toISOString(); }

const MOCK_TRANSACTIONS = [
  { tx_id:"TX-9001", amount:-1240, payee_account:"BigBasket", status:"safe", created_at:hoursAgo(2), label:"BigBasket", category:"Grocery" },
  { tx_id:"TX-8836", amount:-98000, payee_account:"9981 2234 1123", status:"blocked", created_at:hoursAgo(3.5), label:"Transfer — tx_8836", category:"Transfer" },
  { tx_id:"TX-8790", amount:-649, payee_account:"Netflix", status:"safe", created_at:hoursAgo(20), label:"Netflix", category:"Subscription" },
  { tx_id:"TX-8770", amount:-12500, payee_account:"4521 8890 1123", status:"review", created_at:hoursAgo(28), label:"Transfer — Rohan Mehta", category:"Transfer" },
  { tx_id:"TX-8755", amount:-3200, payee_account:"Amazon", status:"safe", created_at:hoursAgo(31), label:"Amazon", category:"Shopping" },
];

// Mock fraud detail shown only for review/blocked transactions in the
// drawer. Structured so risk_score/decision/reasons can be swapped for
// a real backend response later without changing the UI shape.
const MOCK_FRAUD_DETAIL = {
  "TX-8836": { risk_score: 92, reason: "Unusual transaction velocity" },
  "TX-8770": { risk_score: 61, reason: "Recipient differs from usual activity" },
};

// ============================================================
// STATE + RENDERING
// ============================================================
let searchTerm = '';
const filterState = {
  status: new Set(),   // e.g. {'safe','blocked'} — empty = all
  amount: null,        // one of: under1000, 1000-10000, 10000-50000, above50000
  date: null,          // one of: today, week, month, last3months, custom
  customDate: null      // yyyy-mm-dd string, used when date === 'custom'
};

function isToday(d){
  const now = new Date();
  return d.toDateString() === now.toDateString();
}
function isYesterday(d){
  const y = new Date(Date.now() - 86400000);
  return d.toDateString() === y.toDateString();
}
function groupLabel(dateStr){
  const d = new Date(dateStr);
  if (isToday(d)) return 'Today';
  if (isYesterday(d)) return 'Yesterday';
  return d.toLocaleDateString('en-IN', { day:'numeric', month:'short' });
}
function formatTime(dateStr){
  return new Date(dateStr).toLocaleTimeString('en-IN', { hour:'numeric', minute:'2-digit', hour12:true });
}
function formatMoney(n){
  const sign = n < 0 ? '−' : '+';
  return sign + '₹' + Math.abs(n).toLocaleString('en-IN');
}

const ICONS = {
  Grocery: '<path d="M4 5h2l2.4 11.4a2 2 0 0 0 2 1.6h7.2a2 2 0 0 0 2-1.6L21 9H6"/><circle cx="9" cy="20" r="1"/><circle cx="17" cy="20" r="1"/>',
  Transfer: '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 20c0-3.6 3.1-6.5 7-6.5s7 2.9 7 6.5"/>',
  Subscription: '<circle cx="12" cy="12" r="9"/><path d="M10 8.5l6 3.5-6 3.5v-7z" fill="currentColor" stroke="none"/>',
  Shopping: '<path d="M6 8h12l-1 12H7L6 8z"/><path d="M9 8V6a3 3 0 016 0v2"/>',
};

function inAmountRange(amount, range){
  const abs = Math.abs(amount);
  if (range === 'under1000') return abs < 1000;
  if (range === '1000-10000') return abs >= 1000 && abs <= 10000;
  if (range === '10000-50000') return abs > 10000 && abs <= 50000;
  if (range === 'above50000') return abs > 50000;
  return true;
}
function inDateRange(dateStr, range, customDate){
  const d = new Date(dateStr);
  const now = new Date();
  if (range === 'today') return isToday(d);
  if (range === 'week') return (now - d) <= 7 * 86400000;
  if (range === 'month') return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
  if (range === 'last3months') return (now - d) <= 90 * 86400000;
  if (range === 'custom' && customDate) return d.toISOString().slice(0,10) === customDate;
  return true;
}

function matchesFilters(tx){
  if (filterState.status.size > 0 && !filterState.status.has(tx.status)) return false;
  if (filterState.amount && !inAmountRange(tx.amount, filterState.amount)) return false;
  if (filterState.date && !inDateRange(tx.created_at, filterState.date, filterState.customDate)) return false;
  if (searchTerm){
    const hay = (tx.label + ' ' + tx.payee_account + ' ' + tx.tx_id).toLowerCase();
    if (!hay.includes(searchTerm.toLowerCase())) return false;
  }
  return true;
}

function renderList(){
  const filtered = MOCK_TRANSACTIONS.filter(matchesFilters);
  const container = document.getElementById('txListContainer');
  const empty = document.getElementById('txEmptyState');

  if (filtered.length === 0){
    container.style.display = 'none';
    empty.style.display = '';
    return;
  }
  empty.style.display = 'none';
  container.style.display = '';

  // Group by date label, preserving recency order
  const groups = {};
  filtered
    .slice()
    .sort((a,b) => new Date(b.created_at) - new Date(a.created_at))
    .forEach(tx => {
      const g = groupLabel(tx.created_at);
      if (!groups[g]) groups[g] = [];
      groups[g].push(tx);
    });

  let html = '';
  Object.keys(groups).forEach(g => {
    html += `<div class="date-group-label">${g}</div>`;
    groups[g].forEach(tx => { html += renderRow(tx); });
  });
  container.innerHTML = html;

  container.querySelectorAll('.tx-row').forEach(row => {
    row.addEventListener('click', () => openDetail(row.dataset.txid));
  });
}

function renderRow(tx){
  const icon = ICONS[tx.category] || ICONS.Transfer;
  const blockedClass = tx.status === 'blocked' ? ' blocked' : '';
  const badgeLabel = tx.status === 'safe' ? 'Safe' : tx.status === 'review' ? 'Reviewed' : 'Blocked';
  return `
    <div class="tx-row${blockedClass}" data-txid="${tx.tx_id}">
      <div class="tx-row-left">
        <div class="tx-row-icon ${tx.status}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${icon}</svg></div>
        <div style="min-width:0;">
          <div class="tx-row-name">${tx.label}</div>
          <div class="tx-row-meta">${tx.category} · ${groupLabel(tx.created_at)} · ${formatTime(tx.created_at)}</div>
        </div>
      </div>
      <div class="tx-row-right">
        <div class="tx-row-amt">${formatMoney(tx.amount)}</div>
        <span class="tx-badge ${tx.status}"><span class="dot"></span>${badgeLabel}</span>
      </div>
    </div>`;
}

// ============================================================
// DETAIL DRAWER
// ============================================================
function openDetail(txId){
  const tx = MOCK_TRANSACTIONS.find(t => t.tx_id === txId);
  if (!tx) return;

  document.getElementById('ddType').textContent = tx.category;
  document.getElementById('ddAmount').textContent = formatMoney(tx.amount);
  document.getElementById('ddTxId').textContent = tx.tx_id;
  document.getElementById('ddPayee').textContent = /^\d/.test(tx.payee_account.replace(/\s/g,''))
    ? '•••• ' + tx.payee_account.replace(/\s/g,'').slice(-4)
    : tx.payee_account;
  document.getElementById('ddDate').textContent = new Date(tx.created_at).toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' }) + ' · ' + formatTime(tx.created_at);

  const badgeLabel = tx.status === 'safe' ? 'Safe' : tx.status === 'review' ? 'Reviewed' : 'Blocked';
  const badge = document.getElementById('ddBadge');
  badge.className = 'tx-badge ' + tx.status;
  badge.innerHTML = `<span class="dot"></span>${badgeLabel}`;
  document.getElementById('ddStatus').textContent = badgeLabel;

  // Fraud Shield section only shown for review/blocked — never assumed for safe transactions.
  const fraudSection = document.getElementById('ddFraudSection');
  const fraudInfo = MOCK_FRAUD_DETAIL[tx.tx_id];
  if ((tx.status === 'review' || tx.status === 'blocked') && fraudInfo){
    fraudSection.style.display = '';
    document.getElementById('ddFraudDesc').textContent = tx.status === 'blocked'
      ? 'Transaction flagged and held for security review.'
      : 'Transaction flagged for security review.';
    document.getElementById('ddRiskScore').textContent = fraudInfo.risk_score + ' / 100';
    document.getElementById('ddReason').textContent = fraudInfo.reason;
  } else {
    fraudSection.style.display = 'none';
  }

  document.getElementById('txDetailPanel').classList.add('open');
  document.getElementById('txDetailBackdrop').classList.add('show');
}
function closeDetail(){
  document.getElementById('txDetailPanel').classList.remove('open');
  document.getElementById('txDetailBackdrop').classList.remove('show');
}
document.getElementById('txDetailClose').addEventListener('click', closeDetail);
document.getElementById('txDetailBackdrop').addEventListener('click', closeDetail);

// ============================================================
// TOOLBAR: search
// ============================================================
document.getElementById('txSearch').addEventListener('input', (e) => {
  searchTerm = e.target.value.trim();
  renderList();
});

// ============================================================
// FILTER POPOVERS: Status / Amount / Date
// ============================================================
const popoverBackdrop = document.getElementById('filterPopoverBackdrop');
const popovers = {
  status: document.getElementById('statusPopover'),
  amount: document.getElementById('amountPopover'),
  date: document.getElementById('datePopover'),
};

function closeAllPopovers(){
  Object.values(popovers).forEach(p => p.classList.remove('show'));
  popoverBackdrop.classList.remove('show');
}
function openPopover(key){
  const wasOpen = popovers[key].classList.contains('show');
  closeAllPopovers();
  if (!wasOpen){
    popovers[key].classList.add('show');
    popoverBackdrop.classList.add('show');
  }
}
document.getElementById('statusFilterBtn').addEventListener('click', () => openPopover('status'));
document.getElementById('amountFilterBtn').addEventListener('click', () => openPopover('amount'));
document.getElementById('dateFilterBtn').addEventListener('click', () => openPopover('date'));
popoverBackdrop.addEventListener('click', closeAllPopovers);

function updateFilterLabels(){
  // Status
  const statusBtn = document.getElementById('statusFilterBtn');
  const statusLabel = document.getElementById('statusFilterLabel');
  if (filterState.status.size === 0){ statusLabel.textContent = 'Status'; statusBtn.classList.remove('filled'); }
  else if (filterState.status.size === 1){ statusLabel.textContent = 'Status: ' + [...filterState.status][0]; statusBtn.classList.add('filled'); }
  else { statusLabel.textContent = 'Status · ' + filterState.status.size; statusBtn.classList.add('filled'); }

  // Amount
  const amountBtn = document.getElementById('amountFilterBtn');
  const amountLabel = document.getElementById('amountFilterLabel');
  const amountText = { 'under1000':'Under ₹1,000', '1000-10000':'₹1,000–₹10,000', '10000-50000':'₹10,000–₹50,000', 'above50000':'Above ₹50,000' };
  if (filterState.amount){ amountLabel.textContent = amountText[filterState.amount]; amountBtn.classList.add('filled'); }
  else { amountLabel.textContent = 'Amount'; amountBtn.classList.remove('filled'); }

  // Date
  const dateBtn = document.getElementById('dateFilterBtn');
  const dateLabel = document.getElementById('dateFilterLabel');
  const dateText = { 'today':'Today', 'week':'This week', 'month':'This month', 'last3months':'Last 3 months', 'custom':'Custom date' };
  if (filterState.date){ dateLabel.textContent = dateText[filterState.date]; dateBtn.classList.add('filled'); }
  else { dateLabel.textContent = 'Date'; dateBtn.classList.remove('filled'); }
}

// Apply buttons — read current popover selections into filterState
document.querySelector('[data-apply="status"]').addEventListener('click', () => {
  filterState.status = new Set(
    [...popovers.status.querySelectorAll('input[type=checkbox]:checked')].map(el => el.value)
  );
  updateFilterLabels(); renderList(); closeAllPopovers();
});
document.querySelector('[data-apply="amount"]').addEventListener('click', () => {
  const checked = popovers.amount.querySelector('input[name=amountRange]:checked');
  filterState.amount = checked ? checked.value : null;
  updateFilterLabels(); renderList(); closeAllPopovers();
});
document.querySelector('[data-apply="date"]').addEventListener('click', () => {
  const checked = popovers.date.querySelector('input[name=dateRange]:checked');
  filterState.date = checked ? checked.value : null;
  filterState.customDate = document.getElementById('customDateInput').value || null;
  updateFilterLabels(); renderList(); closeAllPopovers();
});

// Clear all — per-popover reset
document.querySelector('[data-clear="status"]').addEventListener('click', () => {
  popovers.status.querySelectorAll('input[type=checkbox]').forEach(el => el.checked = false);
  filterState.status = new Set();
  updateFilterLabels(); renderList(); closeAllPopovers();
});
document.querySelector('[data-clear="amount"]').addEventListener('click', () => {
  popovers.amount.querySelectorAll('input[type=radio]').forEach(el => el.checked = false);
  filterState.amount = null;
  updateFilterLabels(); renderList(); closeAllPopovers();
});
document.querySelector('[data-clear="date"]').addEventListener('click', () => {
  popovers.date.querySelectorAll('input[type=radio]').forEach(el => el.checked = false);
  document.getElementById('customDateInput').value = '';
  filterState.date = null; filterState.customDate = null;
  updateFilterLabels(); renderList(); closeAllPopovers();
});

document.getElementById('clearFiltersBtn').addEventListener('click', () => {
  searchTerm = '';
  filterState.status = new Set();
  filterState.amount = null;
  filterState.date = null;
  filterState.customDate = null;
  document.getElementById('txSearch').value = '';
  document.querySelectorAll('.filter-popover input[type=checkbox], .filter-popover input[type=radio]').forEach(el => el.checked = false);
  document.getElementById('customDateInput').value = '';
  updateFilterLabels();
  renderList();
});

// Export is visual-only for now — no export API exists yet.
document.getElementById('exportBtn').addEventListener('click', () => {
  alert('Export will be available once connected to the backend.');
});

// ============================================================
// SKELETON LOADING — purely visual, no real async fetch happens.
// ============================================================
function renderSkeleton(){
  const sk = document.getElementById('txListSkeleton');
  let rows = '';
  for (let i=0; i<5; i++){
    rows += `
      <div class="tx-skeleton-row">
        <div class="sk-block sk-icon"></div>
        <div class="sk-lines">
          <div class="sk-block sk-line1"></div>
          <div class="sk-block sk-line2"></div>
        </div>
        <div class="sk-block sk-amt"></div>
      </div>`;
  }
  sk.innerHTML = rows;
}
renderSkeleton();
setTimeout(() => {
  document.getElementById('txListSkeleton').style.display = 'none';
  renderList();
}, 550);

// ============================================================
// SPENDING OVERVIEW — mock month totals only (no categories).
// FUTURE INTEGRATION POINT: replace MONTHLY_SPENDING with real
// aggregated transaction totals from the backend, keyed the same way.
// ============================================================
const MONTHLY_SPENDING = [
  { label: 'Jan', total: 21240 },
  { label: 'Feb', total: 24890 },
  { label: 'Mar', total: 19430 },
  { label: 'Apr', total: 27120 },
  { label: 'May', total: 23850 },
  { label: 'Jun', total: 31420 },
  { label: 'Jul', total: 26780 },
  { label: 'Aug', total: 28540 },
];

function renderSpendingOverview(){
  const current = MONTHLY_SPENDING[MONTHLY_SPENDING.length - 1];
  const previous = MONTHLY_SPENDING[MONTHLY_SPENDING.length - 2];

  document.getElementById('spMonthLabel').textContent = current.label + ' ' + new Date().getFullYear();
  document.getElementById('spMonthAmount').textContent = '₹' + current.total.toLocaleString('en-IN');
  document.getElementById('spCompareVal').textContent = '₹' + current.total.toLocaleString('en-IN');

  const pctChange = ((current.total - previous.total) / previous.total) * 100;
  const trendEl = document.getElementById('spCompareTrend');
  const arrow = pctChange >= 0 ? '↑' : '↓';
  trendEl.textContent = `${arrow} ${Math.abs(pctChange).toFixed(1)}% vs ${previous.label}`;
  trendEl.className = 'sp-compare-trend ' + (pctChange >= 0 ? 'up' : 'down');

  // Simple bar chart, no library — just SVG rects scaled to the max value.
  const maxVal = Math.max(...MONTHLY_SPENDING.map(m => m.total));
  const chartW = 240, chartH = 80, gap = 6;
  const barW = (chartW - gap * (MONTHLY_SPENDING.length - 1)) / MONTHLY_SPENDING.length;
  let bars = '';
  MONTHLY_SPENDING.forEach((m, i) => {
    const h = (m.total / maxVal) * chartH;
    const x = i * (barW + gap);
    const y = chartH - h;
    const isCurrent = i === MONTHLY_SPENDING.length - 1;
    bars += `<rect x="${x}" y="${y}" width="${barW}" height="${h}" rx="3" fill="${isCurrent ? 'var(--brand)' : 'var(--lavender)'}"/>`;
  });
  document.getElementById('spChart').innerHTML = bars;
  document.getElementById('spChart').setAttribute('viewBox', `0 0 ${chartW} ${chartH}`);

  document.getElementById('spChartLabels').innerHTML =
    MONTHLY_SPENDING.map(m => `<span>${m.label}</span>`).join('');
}
renderSpendingOverview();


const sidebarEl = document.getElementById('sidebar');
const hamburgerBtn = document.getElementById('hamburgerBtn');
const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');
function openSidebar(){ sidebarEl.classList.add('open'); sidebarBackdrop.classList.add('show'); }
function closeSidebar(){ sidebarEl.classList.remove('open'); sidebarBackdrop.classList.remove('show'); }
if (hamburgerBtn) hamburgerBtn.addEventListener('click', openSidebar);
if (sidebarCloseBtn) sidebarCloseBtn.addEventListener('click', closeSidebar);
if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);
