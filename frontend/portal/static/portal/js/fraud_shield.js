// ============================================================
// FRAUD SHIELD PAGE — intentionally minimal JS.
// This page is mostly static/informational per spec: no fake
// real-time WebSocket behavior, no backend calls. The only
// interactive pieces are the shared sidebar drawer and a
// placeholder for "View all security activity".
// ============================================================

// FUTURE INTEGRATION POINT: this should eventually navigate to
// the Security Activity page once that route exists.
document.getElementById('viewAllActivity').addEventListener('click', () => {
  alert('Security Activity page coming soon.');
});

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
