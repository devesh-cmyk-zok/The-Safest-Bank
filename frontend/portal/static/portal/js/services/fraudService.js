// Fraud Detection Service — maps portal payloads onto the FastAPI transfer engine.
window.fraudService = {
  resolveRecipientId(account, name) {
    const raw = (account || "").toString().trim();
    if (raw.startsWith("usr_")) return raw;
    const nameL = (name || "").toString().toLowerCase();
    const compact = raw.toUpperCase().replace(/\s/g, "");
    if (nameL.includes("unknown") || compact === "ACC888" || compact === "ACC999") return "usr_9999";
    if (nameL.includes("rohan")) return "usr_1003";
    if (nameL.includes("priya")) return "usr_1002";
    if (nameL.includes("ananya")) return "usr_1004";
    if (nameL.includes("vikram")) return "usr_1005";
    return "usr_1002";
  },

  normalizeEngineResult(raw, fallbackAmount) {
    const statusVal = (raw.status || "").toString();
    const decisionRaw = (raw.decision || "").toString().toUpperCase();
    const held = statusVal === "ESCROW_HELD" || decisionRaw === "ESCROW_HELD" || decisionRaw === "QUARANTINE";
    const aborted = statusVal === "AUTO_ABORTED" || statusVal === "BLOCKED_BY_SOC" || decisionRaw === "AUTO_ABORT" || decisionRaw === "BLOCK";
    const scoreRaw = Number(raw.risk_score || 0);
    const score100 = scoreRaw <= 1 ? Number((scoreRaw * 100).toFixed(2)) : scoreRaw;
    const fraudPct = raw.fraud_probability != null ? Number(raw.fraud_probability) : score100;
    const reason = raw.fraud_reason || raw.user_message || raw.message || (held || aborted ? "High risk transaction detected" : "Transaction classified as low risk");
    return {
      transaction_id: raw.transaction_id,
      risk_score: score100,
      fraud_probability: fraudPct,
      decision: aborted ? "BLOCK" : (held ? "QUARANTINE" : "APPROVE"),
      status: aborted ? "BLOCKED" : (held ? "ON_HOLD" : "APPROVED"),
      engine_status: statusVal,
      fraud_reason: reason,
      reasons: raw.reasons || [],
      user_message: raw.user_message || reason,
      xai_breakdown: raw.xai_breakdown || null,
      dev_debug_otp: raw.dev_debug_otp || null,
      amount: fallbackAmount
    };
  },

  async checkTransaction(transactionData) {
    if (window.config && window.config.USE_MOCK_API) {
      return this._mockCheckTransaction(transactionData);
    }
    return this._realCheckTransaction(transactionData);
  },

  async _mockCheckTransaction(data) {
    return new Promise(resolve => {
      setTimeout(() => {
        const amt = Number(data.amount || 0);
        const recipientAcc = (data.recipient_account || "").toString().trim().toUpperCase();
        const senderAcc = (data.sender_account || "").toString().trim().toUpperCase();
        const recipientName = (data.recipient_name || "").toString().toLowerCase();
        const isHighRisk = amt >= 100000 ||
          recipientAcc === "ACC888" ||
          senderAcc === "ACC999" ||
          recipientName.includes("unknown") ||
          data.forceHighRisk === true;

        if (isHighRisk) {
          resolve({
            fraud_probability: 84.99,
            risk_score: 84.99,
            decision: "QUARANTINE",
            status: "ON_HOLD",
            fraud_reason: "High risk transaction detected",
            reasons: [
              "Unusual transaction velocity",
              "New device detected",
              "Recipient differs from usual activity"
            ],
            dev_debug_otp: "123456"
          });
        } else {
          resolve({
            fraud_probability: 3.0,
            risk_score: 3.0,
            decision: "APPROVE",
            status: "APPROVED",
            fraud_reason: "Transaction classified as low risk",
            reasons: []
          });
        }
      }, 1400);
    });
  },

  async _realCheckTransaction(data) {
    const cfg = window.config || {};
    const amount = Number(data.amount || 0);
    const recipientName = data.recipient_name || "";
    const recipientAccount = data.recipient_account || "";
    const highRisk = amount >= 100000 ||
      recipientName.toLowerCase().includes("unknown") ||
      recipientAccount.toUpperCase().replace(/\s/g, "") === "ACC888" ||
      data.forceHighRisk === true;

    const payload = {
      user_id: cfg.USER_ID || "usr_1001",
      recipient_id: this.resolveRecipientId(recipientAccount, recipientName),
      recipient_name: recipientName,
      amount: amount,
      delta_t_ms: highRisk ? 18 : 145,
      ip_distance_km: highRisk ? 1850 : 12,
      device_hash: highRisk ? "untrusted_demo_device" : (cfg.TRUSTED_DEVICE_HASH || "a9f4c3d2e1b0")
    };

    const response = await fetch(cfg.API_URLS.transfer, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const raw = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = raw.detail || raw.message || "Transfer request failed";
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    const normalized = this.normalizeEngineResult(raw, amount);
    if (window.portalApi && window.portalApi.loadUser) {
      window.portalApi.loadUser().catch(() => {});
    }
    return normalized;
  },

  async verifyOtp(transactionId, otp) {
    const cfg = window.config || {};
    const response = await fetch((cfg.API_BASE || "") + "/api/v1/transactions/verify-otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transaction_id: transactionId, otp: otp })
    });
    const raw = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = raw.detail || "Invalid or expired OTP";
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    if (window.portalApi && window.portalApi.loadUser) {
      window.portalApi.loadUser().catch(() => {});
    }
    return raw;
  },

  async refundEscrow(transactionId) {
    const cfg = window.config || {};
    const response = await fetch((cfg.API_BASE || "") + "/api/v1/escrow/refund", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transaction_id: transactionId,
        admin_or_agent_id: cfg.USER_ID || "usr_1001",
        reason: "Customer cancelled transfer"
      })
    });
    const raw = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(raw.detail || "Unable to cancel held transfer");
    }
    if (window.portalApi && window.portalApi.loadUser) {
      window.portalApi.loadUser().catch(() => {});
    }
    return raw;
  }
};
