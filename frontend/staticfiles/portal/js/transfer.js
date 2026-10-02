// ============================================================
// MOCK DATA CONTRACT — unchanged. Replace mockScoreTransfer() with
// a real fetch() to Devesh's FastAPI /score endpoint once it's live.
// Expected response shape from backend:
// { risk_score: 0-100, decision: "approve"|"challenge"|"block", reasons: [...] }
// ============================================================
function mockScoreTransfer(payload){
  return new Promise(resolve => {
    setTimeout(() => {
      resolve({
        risk_score: 82,
        decision: "challenge",
        reasons: ["submission_velocity_ms: 41", "ip_geo_drift: true"]
      });
    }, 900); // slightly longer so the loading state is visible in the demo
  });
}

// Once Devesh's endpoint is ready, swap the function above for:
//
// async function scoreTransfer(payload) {
//   const res = await fetch("/api/score/", {
//     method: "POST",
//     headers: {
//       "Content-Type": "application/json",
//       "X-CSRFToken": getCookie('csrftoken')  // Django CSRF
//     },
//     body: JSON.stringify(payload)
//   });
//   return await res.json();
// }

const form = document.getElementById('transferForm');
const otpOverlay = document.getElementById('otpOverlay');
const fraudOverlay = document.getElementById('fraudOverlay');
const reviewBtn = document.getElementById('reviewBtn');
const submitOtpBtn = document.getElementById('submitOtp');
const trustPulse = document.getElementById('trustPulse');

if (form) {
  form.addEventListener('submit', e => {
    e.preventDefault();
    window.location.href = form.getAttribute('action') || '/transfer/';
  });
}

const otpInputs = [...otpOverlay.querySelectorAll('.otp-boxes input')];
otpInputs.forEach((box, i) => {
  box.addEventListener('input', () => {
    if (box.value && otpInputs[i+1]) otpInputs[i+1].focus();
  });
});

submitOtpBtn.addEventListener('click', async () => {
  setLoading(submitOtpBtn, true);
  const payload = {
    payee: document.getElementById('payee').value,
    recipient: document.getElementById('recipient').value,
    amount: document.getElementById('amount').value,
  };
  const result = await mockScoreTransfer(payload);
  setLoading(submitOtpBtn, false);
  hideOverlay(otpOverlay);

  if (result.decision === "challenge") {
    setPulseState('review');
    showOverlay(fraudOverlay);
    showTyping();
  } else {
    showToast(`Transfer approved · risk ${result.risk_score}/100`, 'safe');
  }
});

document.getElementById('confirmBtn').addEventListener('click', () => {
  disableChatActions();
  showTyping(() => {
    addBotMsg("Thanks — verified. Releasing your transfer now.");
    document.getElementById('chatHead').classList.add('verified');
    document.getElementById('chatHeadTitle').textContent = 'Verified';
    setPulseState('safe');
    setTimeout(() => {
      hideOverlay(fraudOverlay);
      showToast('Transfer verified and sent', 'safe');
    }, 1200);
  });
});

document.getElementById('denyBtn').addEventListener('click', () => {
  disableChatActions();
  setPulseState('blocked');
  showTyping(() => {
    addBotMsg("Understood. We've blocked this transfer and frozen the account as a precaution. Our security team will call you shortly.");
    showToast('Transfer blocked · account frozen', 'blocked');
  });
});

// ---------- UI helpers ----------
function showOverlay(el){ el.classList.add('show'); }
function hideOverlay(el){ el.classList.remove('show'); }

function setLoading(btn, isLoading){
  btn.classList.toggle('loading', isLoading);
  btn.disabled = isLoading;
}

function disableChatActions(){
  document.getElementById('confirmBtn').disabled = true;
  document.getElementById('denyBtn').disabled = true;
}

function addBotMsg(text){
  const body = document.getElementById('chatBody');
  const div = document.createElement('div');
  div.className = 'msg bot';
  div.innerHTML = `<div class="bubble">${text}</div>`;
  body.appendChild(div);
  body.scrollTop = body.scrollHeight;
}

function showTyping(done){
  const body = document.getElementById('chatBody');
  const typing = document.createElement('div');
  typing.className = 'msg bot typing';
  typing.innerHTML = `<div class="bubble"><span></span><span></span><span></span></div>`;
  body.appendChild(typing);
  body.scrollTop = body.scrollHeight;
  setTimeout(() => {
    typing.remove();
    if (done) done();
  }, 700);
}

function setPulseState(state){
  trustPulse.classList.remove('state-review', 'state-blocked');
  if (state === 'review') trustPulse.classList.add('state-review');
  if (state === 'blocked') trustPulse.classList.add('state-blocked');
  // 'safe' just clears back to default gradient
}

let toastTimer;
function showToast(msg, kind){
  const toast = document.getElementById('toast');
  document.getElementById('toastMsg').textContent = msg;
  toast.querySelector('.dot').style.background =
    kind === 'blocked' ? 'var(--blocked)' : 'var(--safe)';
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3200);
}

// ---------- Filter tabs (transactions) ----------
const filterTabs = document.querySelectorAll('.filter-tab');
const txItems = document.querySelectorAll('.tx-item');
const txEmpty = document.getElementById('txEmpty');

filterTabs.forEach(tab => {
  tab.addEventListener('click', () => {
    filterTabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const filter = tab.dataset.filter;
    let visibleCount = 0;
    txItems.forEach(item => {
      const show = filter === 'all' || item.dataset.status === filter;
      item.style.display = show ? '' : 'none';
      if (show) visibleCount++;
    });
    txEmpty.style.display = visibleCount === 0 ? '' : 'none';
  });
});

// ---------- Recipient quick-chips + live summary ----------
const amountInput = document.getElementById('amount');
const payeeInput = document.getElementById('payee');
const recipientInput = document.getElementById('recipient');

document.querySelectorAll('.r-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    recipientInput.value = chip.dataset.name;
    payeeInput.value = chip.dataset.acc;
    syncSummary();
  });
});

function syncSummary(){
  const sumAmount = document.getElementById('sumAmount');
  const sumRecipient = document.getElementById('sumRecipient');
  const rpName = document.getElementById('rpName');
  const rpAcc = document.getElementById('rpAcc');
  const rpAvatar = document.getElementById('rpAvatar');
  if (!sumAmount) return;
  const amt = Number(amountInput.value || 0).toLocaleString('en-IN');
  sumAmount.textContent = '₹' + amt;
  sumRecipient.textContent = recipientInput.value || '—';
  rpName.textContent = recipientInput.value || '—';
  rpAcc.textContent = payeeInput.value || '—';
  const initials = (recipientInput.value || '').trim().split(/\s+/).map(w => w[0]).join('').slice(0,2).toUpperCase();
  rpAvatar.textContent = initials || '—';
}

if (amountInput) amountInput.addEventListener('input', syncSummary);
if (recipientInput) recipientInput.addEventListener('input', syncSummary);
if (payeeInput) payeeInput.addEventListener('input', syncSummary);
syncSummary();

// ============================================================
// SIDEBAR NAVIGATION — mobile drawer toggle
// Scope: sidebar/navbar only. Does not touch any other logic in this file.
// ============================================================
const sidebarEl = document.getElementById('sidebar');
const hamburgerBtn = document.getElementById('hamburgerBtn');
const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');

function openSidebar(){
  sidebarEl.classList.add('open');
  sidebarBackdrop.classList.add('show');
}
function closeSidebar(){
  sidebarEl.classList.remove('open');
  sidebarBackdrop.classList.remove('show');
}
if (hamburgerBtn) hamburgerBtn.addEventListener('click', openSidebar);
if (sidebarCloseBtn) sidebarCloseBtn.addEventListener('click', closeSidebar);
if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);

// The real balance lives in data-value, sourced from the Django `balance`
// context variable if the view provides one (falls back to the mock figure
// below if it doesn't — no backend change required for this to work now).
const balanceEl = document.getElementById('balanceAmount');
const eyeToggle = document.getElementById('eyeToggle');
const eyeIcon = document.getElementById('eyeIcon');
let balanceVisible = false;

if (eyeToggle) {
  eyeToggle.addEventListener('click', () => {
    balanceVisible = !balanceVisible;
    balanceEl.style.opacity = 0;
    setTimeout(() => {
      balanceEl.textContent = balanceVisible ? '₹ ' + balanceEl.dataset.value : balanceEl.dataset.hiddenText;
      balanceEl.style.opacity = 1;
    }, 120);
    eyeToggle.setAttribute('aria-label', balanceVisible ? 'Hide balance' : 'Show balance');
    // swap slashed-eye <-> open-eye icon
    eyeIcon.innerHTML = balanceVisible
      ? '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>'
      : '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/><path d="M4 4l16 16" stroke-linecap="round"/>';
  });
}


let t = 58;
const timerEl = document.getElementById('otpTimer');
setInterval(() => {
  if (t <= 0) return;
  t -= 1;
  timerEl.textContent = `Expires in 0:${t.toString().padStart(2,'0')}`;
}, 1000);

// Helper for CSRF cookie (needed once you connect to real Django POST endpoints)
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
