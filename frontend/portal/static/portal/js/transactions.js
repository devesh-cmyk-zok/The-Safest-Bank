// ============================================================
// TRANSACTION HISTORY — Centralized Transaction Service Integration
// Reads dynamic stored transactions from transactionService
// ============================================================
function hoursAgo(h){ return new Date(Date.now() - h*3600*1000).toISOString(); }

const MOCK_TRANSACTIONS = [
  { tx_id:"TX-9001", amount:-1240, payee_account:"BigBasket", status:"APPROVED", decision:"APPROVE", risk_score:2.1, fraud_probability:2.1, created_at:hoursAgo(2), label:"BigBasket", category:"Grocery" },
  { tx_id:"TX-8836", amount:-500000, payee_account:"9981 2234 1123", status:"ON_HOLD", decision:"QUARANTINE", risk_score:84.99, fraud_probability:84.99, fraud_reason:"High risk transaction detected", created_at:hoursAgo(3.5), label:"Transfer — Unknown Recipient", category:"Transfer" },
  { tx_id:"TX-8790", amount:-649, payee_account:"Netflix", status:"APPROVED", decision:"APPROVE", risk_score:1.5, fraud_probability:1.5, created_at:hoursAgo(20), label:"Netflix", category:"Subscription" },
  { tx_id:"TX-8770", amount:-12500, payee_account:"4521 8890 1123", status:"APPROVED", decision:"APPROVE", risk_score:3.0, fraud_probability:3.0, created_at:hoursAgo(28), label:"Transfer — Rohan Mehta", category:"Transfer" },
  { tx_id:"TX-8755", amount:-3200, payee_account:"Amazon Pay", status:"APPROVED", decision:"APPROVE", risk_score:4.2, fraud_probability:4.2, created_at:hoursAgo(31), label:"Amazon", category:"Shopping" },
];

function getTransactionsList() {
  if (window.transactionService) {
    return window.transactionService.getTransactions();
  }
  return MOCK_TRANSACTIONS;
}

// ============================================================
// STATE + RENDERING
// ============================================================
let searchTerm = '';
const filterState = {
  status: new Set(),   // e.g. {'APPROVED','ON_HOLD','safe','blocked'} — empty = all
  amount: null,        // one of: under1000, 1000-10000, 10000-50000, above50000
  date: null,          // one of: today, week, month, last3months, custom
  customDate: null
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
  const txSt = (tx.status || 'safe').toUpperCase();
  if (filterState.status.size > 0) {
    let hasMatch = false;
    filterState.status.forEach(st => {
      const s = st.toUpperCase();
      if (s === txSt) hasMatch = true;
      if ((s === 'SAFE' || s === 'APPROVED' || s === 'SETTLED') && (txSt === 'SAFE' || txSt === 'APPROVED' || txSt === 'SETTLED')) hasMatch = true;
      if ((s === 'BLOCKED' || s === 'ON_HOLD' || s === 'QUARANTINED' || s === 'ESCROW_HELD') && (txSt === 'BLOCKED' || txSt === 'ON_HOLD' || txSt === 'QUARANTINED' || txSt === 'ESCROW_HELD')) hasMatch = true;
      if ((s === 'REVIEW' || s === 'REVIEWED') && (txSt === 'REVIEW' || txSt === 'REVIEWED')) hasMatch = true;
    });
    if (!hasMatch) return false;
  }

  if (filterState.amount && !inAmountRange(tx.amount, filterState.amount)) return false;
  if (filterState.date && !inDateRange(tx.created_at, filterState.date, filterState.customDate)) return false;
  if (searchTerm){
    const hay = ((tx.label || '') + ' ' + (tx.recipient_name || '') + ' ' + (tx.recipient_account || tx.payee_account || '') + ' ' + tx.tx_id).toLowerCase();
    if (!hay.includes(searchTerm.toLowerCase())) return false;
  }
  return true;
}

function renderList(){
  const allTx = getTransactionsList();
  const filtered = allTx.filter(matchesFilters);
  const container = document.getElementById('txListContainer');
  const empty = document.getElementById('txEmptyState');

  if (filtered.length === 0){
    container.style.display = 'none';
    empty.style.display = '';
    return;
  }
  empty.style.display = 'none';
  container.style.display = '';

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
  const isApproved = tx.status === 'APPROVED' || tx.status === 'safe' || tx.status === 'SETTLED';
  const isQuarantine = tx.status === 'ON_HOLD' || tx.status === 'QUARANTINED' || tx.status === 'blocked' || tx.status === 'ESCROW_HELD' || tx.status === 'BLOCKED';
  
  const statusClass = isApproved ? 'safe' : (isQuarantine ? 'blocked' : 'review');
  const badgeText = isApproved ? 'APPROVED' : (tx.status === 'QUARANTINED' ? 'QUARANTINED' : (tx.status === 'ON_HOLD' ? 'ON_HOLD' : 'Blocked'));

  return `
    <div class="tx-row ${statusClass}" data-txid="${tx.tx_id}">
      <div class="tx-row-left">
        <div class="tx-row-icon ${statusClass}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${icon}</svg></div>
        <div style="min-width:0;">
          <div class="tx-row-name">${tx.label || ('Transfer — ' + (tx.recipient_name || tx.tx_id))}</div>
          <div class="tx-row-meta">${tx.category || 'Transfer'} · ${groupLabel(tx.created_at)} · ${formatTime(tx.created_at)}</div>
        </div>
      </div>
      <div class="tx-row-right">
        <div class="tx-row-amt">${formatMoney(tx.amount)}</div>
        <span class="tx-badge ${statusClass}"><span class="dot"></span>${badgeText}</span>
      </div>
    </div>`;
}

// ============================================================
// DETAIL DRAWER
// ============================================================
function openDetail(txId){
  const allTx = getTransactionsList();
  const tx = allTx.find(t => t.tx_id === txId);
  if (!tx) return;

  const isApproved = tx.status === 'APPROVED' || tx.status === 'safe';
  const statusText = tx.status || (isApproved ? 'APPROVED' : 'ON_HOLD');
  const badgeClass = isApproved ? 'safe' : 'blocked';

  document.getElementById('ddType').textContent = tx.transaction_type || tx.category || 'TRANSFER';
  document.getElementById('ddAmount').textContent = formatMoney(tx.amount);
  document.getElementById('ddTxId').textContent = tx.tx_id;

  const senderEl = document.getElementById('ddSender');
  if (senderEl) senderEl.textContent = tx.sender_account || 'Account •••• 8842';

  const payeeText = tx.recipient_name
    ? `${tx.recipient_name} (${tx.recipient_account || ''})`
    : (tx.recipient_account || tx.payee_account || '—');
  document.getElementById('ddPayee').textContent = payeeText;

  const txTypeEl = document.getElementById('ddTxType');
  if (txTypeEl) txTypeEl.textContent = tx.transaction_type || 'TRANSFER';

  document.getElementById('ddDate').textContent = new Date(tx.created_at).toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' }) + ' · ' + formatTime(tx.created_at);

  const badge = document.getElementById('ddBadge');
  badge.className = 'tx-badge ' + badgeClass;
  badge.innerHTML = `<span class="dot"></span>${statusText}`;
  document.getElementById('ddStatus').textContent = statusText;

  const fraudSection = document.getElementById('ddFraudSection');
  if (fraudSection) {
    fraudSection.style.display = '';
    document.getElementById('ddRiskScore').textContent = (tx.risk_score !== undefined ? tx.risk_score : (isApproved ? 3 : 84.99)) + ' / 100';
    
    const probEl = document.getElementById('ddFraudProb');
    if (probEl) probEl.textContent = (tx.fraud_probability !== undefined ? tx.fraud_probability : (isApproved ? 3 : 84.99)) + '%';
    
    const decEl = document.getElementById('ddDecision');
    if (decEl) decEl.textContent = tx.decision || (isApproved ? 'APPROVE' : 'QUARANTINE');

    document.getElementById('ddReason').textContent = tx.fraud_reason || (isApproved ? 'Transaction classified as low risk' : 'High risk transaction detected');
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
// TOOLBAR SEARCH & FILTERS
// ============================================================
document.getElementById('txSearch').addEventListener('input', (e) => {
  searchTerm = e.target.value.trim();
  renderList();
});

const popoverBackdrop = document.getElementById('filterPopoverBackdrop');
const popovers = {
  status: document.getElementById('statusPopover'),
  amount: document.getElementById('amountPopover'),
  date: document.getElementById('datePopover'),
};

function closeAllPopovers(){
  Object.values(popovers).forEach(p => p && p.classList.remove('show'));
  if (popoverBackdrop) popoverBackdrop.classList.remove('show');
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
if (popoverBackdrop) popoverBackdrop.addEventListener('click', closeAllPopovers);

function updateFilterLabels(){
  const statusBtn = document.getElementById('statusFilterBtn');
  const statusLabel = document.getElementById('statusFilterLabel');
  if (filterState.status.size === 0){ statusLabel.textContent = 'Status'; statusBtn.classList.remove('filled'); }
  else if (filterState.status.size === 1){ statusLabel.textContent = 'Status: ' + [...filterState.status][0]; statusBtn.classList.add('filled'); }
  else { statusLabel.textContent = 'Status · ' + filterState.status.size; statusBtn.classList.add('filled'); }

  const amountBtn = document.getElementById('amountFilterBtn');
  const amountLabel = document.getElementById('amountFilterLabel');
  const amountText = { 'under1000':'Under ₹1,000', '1000-10000':'₹1,000–₹10,000', '10000-50000':'₹10,000–₹50,000', 'above50000':'Above ₹50,000' };
  if (filterState.amount){ amountLabel.textContent = amountText[filterState.amount]; amountBtn.classList.add('filled'); }
  else { amountLabel.textContent = 'Amount'; amountBtn.classList.remove('filled'); }

  const dateBtn = document.getElementById('dateFilterBtn');
  const dateLabel = document.getElementById('dateFilterLabel');
  const dateText = { 'today':'Today', 'week':'This week', 'month':'This month', 'last3months':'Last 3 months', 'custom':'Custom date' };
  if (filterState.date){ dateLabel.textContent = dateText[filterState.date]; dateBtn.classList.add('filled'); }
  else { dateLabel.textContent = 'Date'; dateBtn.classList.remove('filled'); }
}

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

document.getElementById('exportBtn').addEventListener('click', () => {
  alert('Export feature will download transaction history CSV once connected to backend API.');
});

// SKELETON LOADING
function renderSkeleton(){
  const sk = document.getElementById('txListSkeleton');
  if (!sk) return;
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
  const sk = document.getElementById('txListSkeleton');
  if (sk) sk.style.display = 'none';
  renderList();
  if (window.transactionService && window.transactionService.refreshFromApi) {
    window.transactionService.refreshFromApi()
      .then(() => renderList())
      .catch((err) => console.warn('Live transactions unavailable:', err));
  }
}, 450);

// SPENDING OVERVIEW
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

  const spMonthLabel = document.getElementById('spMonthLabel');
  if (spMonthLabel) spMonthLabel.textContent = current.label + ' ' + new Date().getFullYear();
  const spMonthAmount = document.getElementById('spMonthAmount');
  if (spMonthAmount) spMonthAmount.textContent = '₹' + current.total.toLocaleString('en-IN');
  const spCompareVal = document.getElementById('spCompareVal');
  if (spCompareVal) spCompareVal.textContent = '₹' + current.total.toLocaleString('en-IN');

  const pctChange = ((current.total - previous.total) / previous.total) * 100;
  const trendEl = document.getElementById('spCompareTrend');
  if (trendEl) {
    const arrow = pctChange >= 0 ? '↑' : '↓';
    trendEl.textContent = `${arrow} ${Math.abs(pctChange).toFixed(1)}% vs ${previous.label}`;
    trendEl.className = 'sp-compare-trend ' + (pctChange >= 0 ? 'up' : 'down');
  }

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
  const spChart = document.getElementById('spChart');
  if (spChart) {
    spChart.innerHTML = bars;
    spChart.setAttribute('viewBox', `0 0 ${chartW} ${chartH}`);
  }

  const spChartLabels = document.getElementById('spChartLabels');
  if (spChartLabels) {
    spChartLabels.innerHTML = MONTHLY_SPENDING.map(m => `<span>${m.label}</span>`).join('');
  }
}
renderSpendingOverview();

// SIDEBAR DRAWER
const sidebarEl = document.getElementById('sidebar');
const hamburgerBtn = document.getElementById('hamburgerBtn');
const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');
function openSidebar(){ if (sidebarEl) sidebarEl.classList.add('open'); if (sidebarBackdrop) sidebarBackdrop.classList.add('show'); }
function closeSidebar(){ if (sidebarEl) sidebarEl.classList.remove('open'); if (sidebarBackdrop) sidebarBackdrop.classList.remove('show'); }
if (hamburgerBtn) hamburgerBtn.addEventListener('click', openSidebar);
if (sidebarCloseBtn) sidebarCloseBtn.addEventListener('click', closeSidebar);
if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);
