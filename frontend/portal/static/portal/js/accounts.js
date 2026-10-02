// ============================================================
// BALANCE SHOW/HIDE — frontend only, nothing persisted or sent
// anywhere. Same pattern used on the dashboard and Transfer page.
// ============================================================
const acBalance = document.getElementById('acBalance');
const acEyeToggle = document.getElementById('acEyeToggle');
const acEyeIcon = document.getElementById('acEyeIcon');
let acBalanceVisible = false;

acEyeToggle.addEventListener('click', () => {
  acBalanceVisible = !acBalanceVisible;
  acBalance.style.opacity = 0;
  setTimeout(() => {
    acBalance.textContent = acBalanceVisible ? '₹ ' + acBalance.dataset.value : acBalance.dataset.hidden;
    acBalance.style.opacity = 1;
  }, 120);
  acEyeToggle.setAttribute('aria-label', acBalanceVisible ? 'Hide balance' : 'Show balance');
  acEyeIcon.innerHTML = acBalanceVisible
    ? '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>'
    : '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/><path d="M4 4l16 16" stroke-linecap="round"/>';
});

// ============================================================
// "COMING SOON" FEEDBACK — Add account, View details, Request
// statement are all visual/demo buttons per spec. No backend
// account creation, statement generation, or detail fetching exists.
// ============================================================
let acToastTimer;
function showComingSoon(msg){
  const toast = document.getElementById('acToast');
  toast.textContent = msg || 'Coming soon';
  toast.classList.add('show');
  clearTimeout(acToastTimer);
  acToastTimer = setTimeout(() => toast.classList.remove('show'), 2200);
}
document.getElementById('addAccountBtn').addEventListener('click', () => showComingSoon('Adding new accounts is coming soon'));
document.getElementById('viewDetailsBtn').addEventListener('click', () => showComingSoon('Detailed account view coming soon'));
document.getElementById('requestStatementBtn').addEventListener('click', () => showComingSoon('Statement requests coming soon'));

// FUTURE INTEGRATION POINT: once the Fraud Shield route exists and is
// wired into the sidebar app-wide, point this at {% url 'fraud_shield' %}
// instead of showing a toast.
document.getElementById('viewSecurityLink').addEventListener('click', () => showComingSoon('Opening Fraud Shield…'));

// ============================================================
// SIDEBAR DRAWER (same behavior as other pages)
// ============================================================
const sidebarEl = document.getElementById('sidebar');
const hamburgerBtn = document.getElementById('hamburgerBtn');
const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');
function openSidebar(){ sidebarEl.classList.add('open'); sidebarBackdrop.classList.add('show'); }
function closeSidebar(){ sidebarEl.classList.remove('open'); sidebarBackdrop.classList.remove('show'); }
if (hamburgerBtn) hamburgerBtn.addEventListener('click', openSidebar);
if (sidebarCloseBtn) sidebarCloseBtn.addEventListener('click', closeSidebar);
if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);
