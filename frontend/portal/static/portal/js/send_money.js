// ============================================================
// SEND MONEY FLOW — Centralized Fraud Service Integration
// ============================================================

const screens = ['screenInput','screenReview','screenSecurityCheck','screenLowRisk','screenHighRisk','screenVerifiedSuccess'];
function showScreen(id){
  screens.forEach(s => {
    const el = document.getElementById(s);
    if (el) el.classList.toggle('active', s === id);
  });
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
// SCREEN 1 — INPUT FORM & VALIDATION
// ============================================================
const tfPayee = document.getElementById('tfPayee');
const tfRecipient = document.getElementById('tfRecipient');
const tfAmount = document.getElementById('tfAmount');
const tfNote = document.getElementById('tfNote');
const verifyCheck = document.getElementById('verifyCheck');

function refreshSummary(){
  if (tfRecipient) document.getElementById('sumRecipient').textContent = tfRecipient.value || '—';
  const amt = Number(tfAmount.value || 0).toLocaleString('en-IN');
  if (tfAmount) document.getElementById('sumAmount').textContent = '₹' + amt;
}
[tfPayee, tfRecipient, tfAmount, tfNote].forEach(el => {
  if (el) el.addEventListener('input', refreshSummary);
});
refreshSummary();

let verifyTimer;
function maybeShowVerified(){
  clearTimeout(verifyTimer);
  if (!verifyCheck) return;
  verifyCheck.classList.remove('show');
  if (tfPayee.value.trim() && tfRecipient.value.trim()) {
    verifyTimer = setTimeout(() => verifyCheck.classList.add('show'), 450);
  }
}
if (tfPayee) tfPayee.addEventListener('input', maybeShowVerified);
if (tfRecipient) tfRecipient.addEventListener('input', maybeShowVerified);
maybeShowVerified();

// Balance Eye Toggle
const tfBalance = document.getElementById('tfBalance');
const tfEyeToggle = document.getElementById('tfEyeToggle');
const tfEyeIcon = document.getElementById('tfEyeIcon');
let tfBalanceVisible = false;
if (tfEyeToggle) {
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
}

// FORM VALIDATION & CONTINUE
let isSubmitting = false;

document.getElementById('continueBtn').addEventListener('click', () => {
  const payeeVal = tfPayee.value.trim();
  const recipientVal = tfRecipient.value.trim();
  const amountVal = Number(tfAmount.value);

  // Form validations
  if (!payeeVal) {
    showToast('Please enter a recipient account number', 'blocked');
    tfPayee.focus();
    return;
  }
  if (!recipientVal) {
    showToast('Please enter a recipient name', 'blocked');
    tfRecipient.focus();
    return;
  }
  if (isNaN(amountVal) || amountVal <= 0) {
    showToast('Please enter a valid transfer amount (> 0)', 'blocked');
    tfAmount.focus();
    return;
  }

  // Populate review screen
  document.getElementById('rvSender').textContent = 'Account •••• 8842';
  document.getElementById('rvRecipient').textContent = recipientVal;
  const accClean = payeeVal.replace(/\s/g,'');
  document.getElementById('rvAccount').textContent = accClean.length > 4 ? '•••• ' + accClean.slice(-4) : payeeVal;
  document.getElementById('rvAmount').textContent = '₹' + amountVal.toLocaleString('en-IN');
  document.getElementById('rvNote').textContent = tfNote.value.trim() || '—';

  setStep(2);
  showScreen('screenReview');
});

// ============================================================
// SCREEN 2 — REVIEW & CONFIRMATION
// ============================================================
document.getElementById('backBtn').addEventListener('click', () => {
  setStep(1);
  showScreen('screenInput');
});

document.getElementById('confirmBtn').addEventListener('click', async () => {
  if (isSubmitting) return; // Prevent double submission
  isSubmitting = true;

  setLoading('confirmBtn', true);
  setTimeout(() => {
    setLoading('confirmBtn', false);
    setStep(3);
    showScreen('screenSecurityCheck');
    runSecurityCheck();
  }, 400);
});

// ============================================================
// SCREEN 3 — SECURITY CHECK (Calling fraudService)
// ============================================================
let currentTxResult = null;

async function runSecurityCheck(){
  const items = document.querySelectorAll('.check-item');
  items.forEach(i => i.classList.remove('done'));
  const progressFill = document.getElementById('secProgressFill');
  if (progressFill) progressFill.style.width = '0%';

  items.forEach((item, i) => {
    setTimeout(() => {
      item.classList.add('done');
      if (progressFill) progressFill.style.width = ((i+1) / items.length * 100) + '%';
    }, (i + 1) * 450);
  });

  const transactionData = {
    sender_account: "Account •••• 8842",
    recipient_account: tfPayee.value.trim(),
    recipient_name: tfRecipient.value.trim(),
    amount: Number(tfAmount.value || 0),
    transaction_type: "TRANSFER"
  };

  const minDelay = new Promise(res => setTimeout(res, items.length * 450 + 200));

  try {
    const [result] = await Promise.all([
      window.fraudService.checkTransaction(transactionData),
      minDelay
    ]);

    isSubmitting = false;
    currentTxResult = result;

    const txId = result.transaction_id || ("TX-" + Math.floor(100000 + Math.random() * 900000));
    const nowIso = new Date().toISOString();

    // Standardized transaction object stored in transactionService
    const newTxRecord = {
      tx_id: txId,
      sender_account: transactionData.sender_account,
      recipient_account: transactionData.recipient_account,
      recipient_name: transactionData.recipient_name,
      amount: -transactionData.amount,
      transaction_type: "TRANSFER",
      risk_score: result.risk_score,
      fraud_probability: result.fraud_probability,
      decision: result.decision,
      status: result.status,
      fraud_reason: result.fraud_reason,
      reasons: result.reasons || [],
      category: "Transfer",
      label: `Transfer — ${transactionData.recipient_name}`,
      created_at: nowIso
    };

    if (window.transactionService) {
      window.transactionService.addTransaction(newTxRecord);
    }

    if (result.decision === "APPROVE" || result.status === "APPROVED") {
      renderApprovedResult(result, transactionData, txId);
      setStep(4);
      showScreen('screenLowRisk');
    } else {
      renderQuarantineResult(result, transactionData, txId);
      setStep(4);
      showScreen('screenHighRisk');
    }
  } catch (err) {
    isSubmitting = false;
    console.error("Fraud check error:", err);
    showToast(err.message || "Error assessing transaction security", "blocked");
    setStep(1);
    showScreen('screenInput');
  }
}

// ============================================================
// SCREEN 4A — APPROVED RESULT SCREEN
// ============================================================
function renderApprovedResult(result, txData, txId){
  const amtFormatted = '₹' + Number(txData.amount).toLocaleString('en-IN');
  document.getElementById('lrAmount').textContent = amtFormatted;
  document.getElementById('lrRecipient').textContent = txData.recipient_name;
  document.getElementById('lrScore').textContent = result.risk_score;

  const lrTxId = document.getElementById('lrTxId');
  if (lrTxId) lrTxId.textContent = txId;

  const lrRiskScoreDisplay = document.getElementById('lrRiskScoreDisplay');
  if (lrRiskScoreDisplay) lrRiskScoreDisplay.textContent = `${result.risk_score} / 100`;

  const lrProb = document.getElementById('lrProb');
  if (lrProb) lrProb.textContent = `${result.fraud_probability}%`;

  const lrReason = document.getElementById('lrReason');
  if (lrReason) lrReason.textContent = result.fraud_reason || "Transaction classified as low risk";
}

// ============================================================
// SCREEN 4B — QUARANTINE / ON-HOLD RESULT SCREEN
// ============================================================
const WARNING_ICON_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l9.5 17H2.5L12 3z"/><path d="M12 10v4"/><circle cx="12" cy="17.3" r="0.6" fill="currentColor" stroke="none"/></svg>';

function renderQuarantineResult(result, txData, txId){
  const amtFormatted = '₹' + Number(txData.amount).toLocaleString('en-IN');
  document.getElementById('hrAmount').textContent = amtFormatted;
  document.getElementById('hrRecipient').textContent = txData.recipient_name;
  document.getElementById('hrScore').textContent = result.risk_score;

  const hrTxId = document.getElementById('hrTxId');
  if (hrTxId) hrTxId.textContent = txId;

  const hrProb = document.getElementById('hrProb');
  if (hrProb) hrProb.textContent = `${result.fraud_probability}%`;

  const hrReason = document.getElementById('hrReason');
  if (hrReason) hrReason.textContent = result.fraud_reason || "High risk transaction detected";

  const list = document.getElementById('hrReasons');
  if (list) {
    const reasons = result.reasons && result.reasons.length > 0
      ? result.reasons
      : ["Unusual transaction velocity", "New device detected", "Recipient differs from usual activity"];
    list.innerHTML = reasons.map(r => `<li>${WARNING_ICON_SVG}${r}</li>`).join('');
  }
}

document.getElementById('verifyMeBtn').addEventListener('click', () => {
  showOverlay('otpOverlay');
  const hint = document.getElementById('otpDemoHint');
  if (hint) {
    const code = currentTxResult && currentTxResult.dev_debug_otp ? currentTxResult.dev_debug_otp : '123456';
    hint.textContent = 'Demo OTP: ' + code + ' (or 123456)';
    hint.style.display = 'block';
  }
  startOtpTimer();
});

document.getElementById('cancelTransferBtn').addEventListener('click', async () => {
  const txId = currentTxResult && currentTxResult.transaction_id;
  if (txId && window.fraudService && window.fraudService.refundEscrow) {
    try {
      await window.fraudService.refundEscrow(txId);
    } catch (err) {
      console.warn('Refund request failed:', err);
    }
  }
  showToast('Transfer cancelled', 'blocked');
  resetFlow();
});

// ============================================================
// OTP MODAL — VERIFICATION BEHAVIOR (Requirement 15)
// Frontend-only OTP entry CANNOT change QUARANTINE -> APPROVED.
// ============================================================
const otpOverlay = document.getElementById('otpOverlay');
const otpInputs = otpOverlay ? [...otpOverlay.querySelectorAll('.otp-boxes input')] : [];
otpInputs.forEach((box, i) => {
  box.addEventListener('input', () => {
    if (box.value && otpInputs[i+1]) otpInputs[i+1].focus();
  });
});

document.getElementById('otpCancelBtn').addEventListener('click', () => {
  hideOverlay('otpOverlay');
});

document.getElementById('otpVerifyBtn').addEventListener('click', async () => {
  const code = otpInputs.map(el => el.value).join('');
  if (code.length < 6) {
    showToast('Enter the 6-digit OTP', 'blocked');
    return;
  }
  const txId = currentTxResult && (currentTxResult.transaction_id || currentTxResult.tx_id);
  if (!txId) {
    showToast('Missing transaction id for OTP', 'blocked');
    return;
  }
  setLoading('otpVerifyBtn', true);
  try {
    await window.fraudService.verifyOtp(txId, code);
    setLoading('otpVerifyBtn', false);
    hideOverlay('otpOverlay');
    if (window.transactionService) {
      window.transactionService.updateTransaction(txId, {
        status: 'APPROVED',
        decision: 'APPROVE',
        fraud_reason: 'Step-up authentication successful. Escrow released.'
      });
    }
    const vsAmount = document.getElementById('vsAmount');
    const vsRecipient = document.getElementById('vsRecipient');
    if (vsAmount) vsAmount.textContent = '₹' + Number(tfAmount.value || 0).toLocaleString('en-IN');
    if (vsRecipient) vsRecipient.textContent = tfRecipient.value.trim();
    setStep(4);
    showScreen('screenVerifiedSuccess');
    showToast('Identity verified · funds released', 'safe');
  } catch (err) {
    setLoading('otpVerifyBtn', false);
    showToast(err.message || 'Invalid OTP', 'blocked');
  }
});

let otpTimerInterval;
function startOtpTimer(){
  let t = 60;
  const el = document.getElementById('otpTimer');
  if (!el) return;
  clearInterval(otpTimerInterval);
  el.textContent = `Code expires in ${t}s`;
  otpTimerInterval = setInterval(() => {
    t -= 1;
    el.textContent = `Code expires in ${t}s`;
    if (t <= 0) clearInterval(otpTimerInterval);
  }, 1000);
}

// ============================================================
// RESET FLOW
// ============================================================
function resetFlow(){
  isSubmitting = false;
  setStep(1);
  showScreen('screenInput');
}

const doneBtn2 = document.getElementById('doneBtn2');
if (doneBtn2) {
  doneBtn2.addEventListener('click', () => resetFlow());
}

// ============================================================
// SHARED UI HELPERS
// ============================================================
function setLoading(btnId, isLoading){
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.classList.toggle('loading', isLoading);
  btn.disabled = isLoading;
}
function showOverlay(id){
  const el = document.getElementById(id);
  if (el) el.classList.add('show');
}
function hideOverlay(id){
  const el = document.getElementById(id);
  if (el) el.classList.remove('show');
}

let toastTimer;
function showToast(msg, kind){
  const toast = document.getElementById('toast');
  if (!toast) return;
  document.getElementById('toastMsg').textContent = msg;
  toast.querySelector('.dot').style.background = kind === 'blocked' ? 'var(--blocked)' : 'var(--safe)';
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3500);
}

// ============================================================
// SIDEBAR DRAWER
// ============================================================
const sidebarEl = document.getElementById('sidebar');
const hamburgerBtn = document.getElementById('hamburgerBtn');
const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');
function openSidebar(){ if (sidebarEl) sidebarEl.classList.add('open'); if (sidebarBackdrop) sidebarBackdrop.classList.add('show'); }
function closeSidebar(){ if (sidebarEl) sidebarEl.classList.remove('open'); if (sidebarBackdrop) sidebarBackdrop.classList.remove('show'); }
if (hamburgerBtn) hamburgerBtn.addEventListener('click', openSidebar);
if (sidebarCloseBtn) sidebarCloseBtn.addEventListener('click', closeSidebar);
if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);
