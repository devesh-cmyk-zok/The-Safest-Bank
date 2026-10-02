// ============================================================
// DASHBOARD QUICK TRANSFER FLOW
// Centralized call to window.fraudService and window.transactionService
// ============================================================

const form = document.getElementById('transferForm');
const otpOverlay = document.getElementById('otpOverlay');
const fraudOverlay = document.getElementById('fraudOverlay');
const reviewBtn = document.getElementById('reviewBtn');
const submitOtpBtn = document.getElementById('submitOtp');
const trustPulse = document.getElementById('trustPulse');

if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payeeVal = document.getElementById('payee').value.trim();
    const recipientVal = document.getElementById('recipient').value.trim();
    const amountVal = Number(document.getElementById('amount').value);

    if (!payeeVal || !recipientVal || isNaN(amountVal) || amountVal <= 0) {
      showToast('Please fill out recipient details and valid amount (> 0)', 'blocked');
      return;
    }

    const payload = {
      sender_account: "Account •••• 8842",
      recipient_account: payeeVal,
      recipient_name: recipientVal,
      amount: amountVal,
      transaction_type: "TRANSFER"
    };

    const confirmTransferBtn = form.querySelector('button[type="submit"]');
    setLoading(confirmTransferBtn, true);
    try {
      const result = await window.fraudService.checkTransaction(payload);
      setLoading(confirmTransferBtn, false);
      window.__lastQuickTx = result;
      const txId = result.transaction_id || ("TX-" + Math.floor(100000 + Math.random() * 900000));
      if (window.transactionService) {
        window.transactionService.addTransaction({
          tx_id: txId,
          sender_account: payload.sender_account,
          recipient_account: payload.recipient_account,
          recipient_name: payload.recipient_name,
          amount: -payload.amount,
          transaction_type: "TRANSFER",
          risk_score: result.risk_score,
          fraud_probability: result.fraud_probability,
          decision: result.decision,
          status: result.status,
          fraud_reason: result.fraud_reason,
          reasons: result.reasons || [],
          category: "Transfer",
          label: `Transfer — ${payload.recipient_name}`,
          created_at: new Date().toISOString()
        });
      }

      if (result.decision === "QUARANTINE" || result.status === "ON_HOLD" || result.decision === "BLOCK") {
        setPulseState('review');
        const hint = document.getElementById('otpDemoHint');
        if (hint) {
          hint.textContent = 'Demo OTP: ' + (result.dev_debug_otp || '123456');
          hint.style.display = 'block';
        }
        showOverlay(otpOverlay);
        const firstInput = otpOverlay.querySelector('input');
        if (firstInput) firstInput.focus();
      } else {
        showToast(`Transfer settled · risk score ${result.risk_score}/100`, 'safe');
      }
    } catch (err) {
      setLoading(confirmTransferBtn, false);
      showToast(err.message || "Security evaluation error", "blocked");
    }
  });
}

const otpInputs = otpOverlay ? [...otpOverlay.querySelectorAll('.otp-boxes input')] : [];
otpInputs.forEach((box, i) => {
  box.addEventListener('input', () => {
    if (box.value && otpInputs[i+1]) otpInputs[i+1].focus();
  });
});

if (submitOtpBtn) {
  submitOtpBtn.addEventListener('click', async () => {
    const code = otpInputs.map(el => el.value).join('');
    if (code.length < 6) {
      showToast('Enter the 6-digit OTP', 'blocked');
      return;
    }
    const pending = window.__lastQuickTx || {};
    const txId = pending.transaction_id;
    if (!txId) {
      showToast('No held transaction to verify', 'blocked');
      return;
    }
    setLoading(submitOtpBtn, true);
    try {
      await window.fraudService.verifyOtp(txId, code);
      setLoading(submitOtpBtn, false);
      hideOverlay(otpOverlay);
      if (window.transactionService) {
        window.transactionService.updateTransaction(txId, {
          status: 'APPROVED',
          decision: 'APPROVE',
          fraud_reason: 'Step-up authentication successful. Escrow released.'
        });
      }
      setPulseState('safe');
      showToast('Identity verified · escrow released', 'safe');
    } catch (err) {
      setLoading(submitOtpBtn, false);
      showToast(err.message || 'Invalid OTP', 'blocked');
    }
  });
}

const confirmBtn = document.getElementById('confirmBtn');
if (confirmBtn) {
  confirmBtn.addEventListener('click', () => {
    disableChatActions();
    showTyping(() => {
      addBotMsg("Thanks — verification logged. Transfer remains ON HOLD for analyst review.");
      document.getElementById('chatHead').classList.add('verified');
      document.getElementById('chatHeadTitle').textContent = 'Identity Verified';
      setPulseState('safe');
      setTimeout(() => {
        hideOverlay(fraudOverlay);
        showToast('Verification logged · Status: ON_HOLD', 'blocked');
      }, 1200);
    });
  });
}

const denyBtn = document.getElementById('denyBtn');
if (denyBtn) {
  denyBtn.addEventListener('click', () => {
    disableChatActions();
    setPulseState('blocked');
    showTyping(() => {
      addBotMsg("Understood. We've blocked this transfer and frozen the account as a precaution. Our security team will call you shortly.");
      showToast('Transfer blocked · account frozen', 'blocked');
    });
  });
}

// ---------- UI HELPERS ----------
function showOverlay(el){ if (el) el.classList.add('show'); }
function hideOverlay(el){ if (el) el.classList.remove('show'); }

function setLoading(btn, isLoading){
  if (!btn) return;
  btn.classList.toggle('loading', isLoading);
  btn.disabled = isLoading;
}

function disableChatActions(){
  const c = document.getElementById('confirmBtn');
  const d = document.getElementById('denyBtn');
  if (c) c.disabled = true;
  if (d) d.disabled = true;
}

function addBotMsg(text){
  const body = document.getElementById('chatBody');
  if (!body) return;
  const div = document.createElement('div');
  div.className = 'msg bot';
  div.innerHTML = `<div class="bubble">${text}</div>`;
  body.appendChild(div);
  body.scrollTop = body.scrollHeight;
}

function showTyping(done){
  const body = document.getElementById('chatBody');
  if (!body) return;
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
  if (!trustPulse) return;
  trustPulse.classList.remove('state-review', 'state-blocked');
  if (state === 'review') trustPulse.classList.add('state-review');
  if (state === 'blocked') trustPulse.classList.add('state-blocked');
}

let toastTimer;
function showToast(msg, kind){
  const toast = document.getElementById('toast');
  if (!toast) return;
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
    if (txEmpty) txEmpty.style.display = visibleCount === 0 ? '' : 'none';
  });
});

// ---------- Recipient quick-chips + live summary ----------
const amountInput = document.getElementById('amount');
const payeeInput = document.getElementById('payee');
const recipientInput = document.getElementById('recipient');

document.querySelectorAll('.r-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    if (recipientInput) recipientInput.value = chip.dataset.name;
    if (payeeInput) payeeInput.value = chip.dataset.acc;
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
  const amt = Number(amountInput ? amountInput.value || 0 : 0).toLocaleString('en-IN');
  sumAmount.textContent = '₹' + amt;
  if (sumRecipient) sumRecipient.textContent = recipientInput ? recipientInput.value || '—' : '—';
  if (rpName) rpName.textContent = recipientInput ? recipientInput.value || '—' : '—';
  if (rpAcc) rpAcc.textContent = payeeInput ? payeeInput.value || '—' : '—';
  const initials = (recipientInput ? recipientInput.value || '' : '').trim().split(/\s+/).map(w => w[0]).join('').slice(0,2).toUpperCase();
  if (rpAvatar) rpAvatar.textContent = initials || '—';
}

if (amountInput) amountInput.addEventListener('input', syncSummary);
if (recipientInput) recipientInput.addEventListener('input', syncSummary);
if (payeeInput) payeeInput.addEventListener('input', syncSummary);
syncSummary();

// ---------- SIDEBAR DRAWER ----------
const sidebarEl = document.getElementById('sidebar');
const hamburgerBtn = document.getElementById('hamburgerBtn');
const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');

function openSidebar(){
  if (sidebarEl) sidebarEl.classList.add('open');
  if (sidebarBackdrop) sidebarBackdrop.classList.add('show');
}
function closeSidebar(){
  if (sidebarEl) sidebarEl.classList.remove('open');
  if (sidebarBackdrop) sidebarBackdrop.classList.remove('show');
}
if (hamburgerBtn) hamburgerBtn.addEventListener('click', openSidebar);
if (sidebarCloseBtn) sidebarCloseBtn.addEventListener('click', closeSidebar);
if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);

const balanceEl = document.getElementById('balanceAmount');
const eyeToggle = document.getElementById('eyeToggle');
const eyeIcon = document.getElementById('eyeIcon');
let balanceVisible = false;

if (eyeToggle && balanceEl) {
  eyeToggle.addEventListener('click', () => {
    balanceVisible = !balanceVisible;
    balanceEl.style.opacity = 0;
    setTimeout(() => {
      balanceEl.textContent = balanceVisible ? '₹ ' + balanceEl.dataset.value : balanceEl.dataset.hiddenText;
      balanceEl.style.opacity = 1;
    }, 120);
    eyeToggle.setAttribute('aria-label', balanceVisible ? 'Hide balance' : 'Show balance');
    if (eyeIcon) {
      eyeIcon.innerHTML = balanceVisible
        ? '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>'
        : '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/><path d="M4 4l16 16" stroke-linecap="round"/>';
    }
  });
}

let t = 58;
const timerEl = document.getElementById('otpTimer');
if (timerEl) {
  setInterval(() => {
    if (t <= 0) return;
    t -= 1;
    timerEl.textContent = `Expires in 0:${t.toString().padStart(2,'0')}`;
  }, 1000);
}

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
