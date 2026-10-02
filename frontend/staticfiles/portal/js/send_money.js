// ============================================================
// DEMO SCENARIO CONFIG — frontend-only mock data.
//
// FUTURE INTEGRATION POINT: replace getScenarioResult() with a real
// call to Devesh's FastAPI /score endpoint. The backend is expected
// to return exactly this shape:
//   { risk_score: 0-100, decision: "approve"|"challenge"|"block", reasons: [...] }
// Everything below this comment block is UI/demo only — no real
// fraud detection happens here.
// ============================================================
const DEMO_SCENARIOS = {
  NORMAL: {
    risk_score: 12,
    decision: "approve",
    reasons: []
  },
  FRAUD_1: { // OTP / Session Hijacking
    risk_score: 91,
    decision: "challenge",
    reasons: ["Unusual OTP request pattern", "Session behavior differs from baseline", "Multiple verification attempts"]
  },
  FRAUD_2: { // Identity / Authentication
    risk_score: 84,
    decision: "challenge",
    reasons: ["Authentication pattern changed", "Device identity mismatch", "Unusual login context"]
  },
  FRAUD_3: { // Account Takeover
    risk_score: 96,
    decision: "hold",
    reasons: ["New device detected", "Unusual account activity", "High-risk transaction behavior"]
  },
  FRAUD_4: { // Behavioral Anomaly
    risk_score: 78,
    decision: "challenge",
    reasons: ["Unusual transaction velocity", "Unusual transaction amount", "Location deviation"]
  }
};

function getScenarioResult(){
  const key = document.getElementById('demoScenario').value;
  return DEMO_SCENARIOS[key] || DEMO_SCENARIOS.NORMAL;
}

// ============================================================
// SCREEN NAVIGATION
// ============================================================
const screens = ['screenInput','screenReview','screenSecurityCheck','screenLowRisk','screenHighRisk','screenVerifiedSuccess'];
function showScreen(id){
  screens.forEach(s => document.getElementById(s).classList.toggle('active', s === id));
}

function setStep(n){
  document.querySelectorAll('.step').forEach(step => {
    const stepNum = Number(step.dataset.step);
    step.classList.remove('active','done');
    if (stepNum < n) step.classList.add('done');
    if (stepNum === n) step.classList.add('active');
  });
}

// ============================================================
// SCREEN 1 — INPUT
// ============================================================
const tfPayee = document.getElementById('tfPayee');
const tfRecipient = document.getElementById('tfRecipient');
const tfAmount = document.getElementById('tfAmount');
const tfNote = document.getElementById('tfNote');
const verifyCheck = document.getElementById('verifyCheck');

function refreshSummary(){
  document.getElementById('sumRecipient').textContent = tfRecipient.value || '—';
  const amt = Number(tfAmount.value || 0).toLocaleString('en-IN');
  document.getElementById('sumAmount').textContent = '₹' + amt;
}
[tfPayee, tfRecipient, tfAmount, tfNote].forEach(el => el.addEventListener('input', refreshSummary));
refreshSummary();

// Simulated recognition check — UI/demo only, no real verification API.
let verifyTimer;
function maybeShowVerified(){
  clearTimeout(verifyTimer);
  verifyCheck.classList.remove('show');
  if (tfPayee.value.trim() && tfRecipient.value.trim()) {
    verifyTimer = setTimeout(() => verifyCheck.classList.add('show'), 450);
  }
}
tfPayee.addEventListener('input', maybeShowVerified);
tfRecipient.addEventListener('input', maybeShowVerified);
maybeShowVerified();

// Mini balance eye toggle (same pattern as dashboard, self-contained to this page)
const tfBalance = document.getElementById('tfBalance');
const tfEyeToggle = document.getElementById('tfEyeToggle');
const tfEyeIcon = document.getElementById('tfEyeIcon');
let tfBalanceVisible = false;
tfEyeToggle.addEventListener('click', () => {
  tfBalanceVisible = !tfBalanceVisible;
  tfBalance.style.opacity = 0;
  setTimeout(() => {
    tfBalance.textContent = tfBalanceVisible ? '₹ ' + tfBalance.dataset.value : tfBalance.dataset.hidden;
    tfBalance.style.opacity = 1;
  }, 120);
  tfEyeIcon.innerHTML = tfBalanceVisible
    ? '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>'
    : '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/><path d="M4 4l16 16" stroke-linecap="round"/>';
});

document.getElementById('continueBtn').addEventListener('click', () => {
  // Populate review screen from input
  document.getElementById('rvRecipient').textContent = tfRecipient.value || '—';
  const acc = tfPayee.value.replace(/\s/g,'');
  document.getElementById('rvAccount').textContent = '•••• ' + acc.slice(-4);
  document.getElementById('rvAmount').textContent = '₹' + Number(tfAmount.value || 0).toLocaleString('en-IN');
  document.getElementById('rvNote').textContent = tfNote.value || '—';
  setStep(2);
  showScreen('screenReview');
});

// ============================================================
// SCREEN 2 — REVIEW
// ============================================================
document.getElementById('backBtn').addEventListener('click', () => {
  setStep(1);
  showScreen('screenInput');
});

document.getElementById('confirmBtn').addEventListener('click', () => {
  setLoading('confirmBtn', true);
  setTimeout(() => {
    setLoading('confirmBtn', false);
    setStep(3);
    showScreen('screenSecurityCheck');
    runSecurityCheck();
  }, 500);
});

// ============================================================
// SCREEN 3 — SECURITY CHECK (animated, frontend demo state only)
// ============================================================
function runSecurityCheck(){
  const items = document.querySelectorAll('.check-item');
  items.forEach(i => i.classList.remove('done'));
  document.getElementById('secProgressFill').style.width = '0%';

  items.forEach((item, i) => {
    setTimeout(() => {
      item.classList.add('done');
      document.getElementById('secProgressFill').style.width = ((i+1) / items.length * 100) + '%';
    }, (i + 1) * 480);
  });

  setTimeout(() => {
    const result = getScenarioResult();
    if (result.decision === 'approve') {
      renderLowRisk(result);
      setStep(4);
      showScreen('screenLowRisk');
    } else {
      renderHighRisk(result);
      showScreen('screenHighRisk');
    }
  }, items.length * 480 + 500);
}

// ============================================================
// SCREEN 4A — LOW RISK
// ============================================================
function renderLowRisk(result){
  document.getElementById('lrAmount').textContent = '₹' + Number(tfAmount.value || 0).toLocaleString('en-IN');
  document.getElementById('lrRecipient').textContent = tfRecipient.value || '—';
  document.getElementById('lrScore').textContent = result.risk_score;
}
document.getElementById('doneBtn1').addEventListener('click', () => resetFlow());

// ============================================================
// SCREEN 4B — HIGH RISK
// ============================================================
const WARNING_ICON_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l9.5 17H2.5L12 3z"/><path d="M12 10v4"/><circle cx="12" cy="17.3" r="0.6" fill="currentColor" stroke="none"/></svg>';

function renderHighRisk(result){
  document.getElementById('hrScore').textContent = result.risk_score;
  const list = document.getElementById('hrReasons');
  list.innerHTML = result.reasons.map(r => `<li>${WARNING_ICON_SVG}${r}</li>`).join('');
}

document.getElementById('verifyMeBtn').addEventListener('click', () => {
  showOverlay('otpOverlay');
  startOtpTimer();
});

document.getElementById('cancelTransferBtn').addEventListener('click', () => {
  showToast('Transfer cancelled', 'blocked');
  resetFlow();
});

// ============================================================
// OTP MODAL — UI simulation only, no SMS, no real OTP service.
// Any 6 digits entered are accepted as a demo "verify" action.
// ============================================================
const otpOverlay = document.getElementById('otpOverlay');
const otpInputs = [...otpOverlay.querySelectorAll('.otp-boxes input')];
otpInputs.forEach((box, i) => {
  box.addEventListener('input', () => {
    if (box.value && otpInputs[i+1]) otpInputs[i+1].focus();
  });
});

document.getElementById('otpCancelBtn').addEventListener('click', () => {
  hideOverlay('otpOverlay');
  // Transaction remains HELD — user stays on the high-risk screen.
});

document.getElementById('otpVerifyBtn').addEventListener('click', () => {
  setLoading('otpVerifyBtn', true);
  setTimeout(() => {
    setLoading('otpVerifyBtn', false);
    hideOverlay('otpOverlay');
    document.getElementById('vsAmount').textContent = '₹' + Number(tfAmount.value || 0).toLocaleString('en-IN');
    document.getElementById('vsRecipient').textContent = tfRecipient.value || '—';
    setStep(4);
    showScreen('screenVerifiedSuccess');
    showToast('Transaction verified', 'safe');
  }, 700);
});

let otpTimerInterval;
function startOtpTimer(){
  let t = 60;
  const el = document.getElementById('otpTimer');
  clearInterval(otpTimerInterval);
  el.textContent = `Code expires in ${t}s`;
  otpTimerInterval = setInterval(() => {
    t -= 1;
    el.textContent = `Code expires in ${t}s`;
    if (t <= 0) clearInterval(otpTimerInterval);
  }, 1000);
}

document.getElementById('doneBtn2').addEventListener('click', () => resetFlow());

// ============================================================
// RESET — back to screen 1 for the next demo run
// ============================================================
function resetFlow(){
  setStep(1);
  showScreen('screenInput');
}

// ============================================================
// SHARED UI HELPERS
// ============================================================
function setLoading(btnId, isLoading){
  const btn = document.getElementById(btnId);
  btn.classList.toggle('loading', isLoading);
  btn.disabled = isLoading;
}
function showOverlay(id){ document.getElementById(id).classList.add('show'); }
function hideOverlay(id){ document.getElementById(id).classList.remove('show'); }

let toastTimer;
function showToast(msg, kind){
  const toast = document.getElementById('toast');
  document.getElementById('toastMsg').textContent = msg;
  toast.querySelector('.dot').style.background = kind === 'blocked' ? 'var(--blocked)' : 'var(--safe)';
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
}

// ============================================================
// SIDEBAR DRAWER (identical behavior to dashboard, self-contained here)
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
