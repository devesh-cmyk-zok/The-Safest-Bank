// Transaction Service — maintains transaction history state for customer portal
(function() {
  const STORAGE_KEY = 'safest_bank_transactions_v1';

  function hoursAgo(h) {
    return new Date(Date.now() - h * 3600 * 1000).toISOString();
  }

  const DEFAULT_TRANSACTIONS = [
    {
      tx_id: "TX-9001",
      sender_account: "Account •••• 8842",
      recipient_account: "BigBasket",
      recipient_name: "BigBasket Supermarket",
      amount: -1240,
      transaction_type: "PAYMENT",
      risk_score: 2.1,
      fraud_probability: 2.1,
      decision: "APPROVE",
      status: "APPROVED",
      fraud_reason: "Transaction classified as low risk",
      reasons: [],
      category: "Grocery",
      label: "BigBasket",
      created_at: hoursAgo(2)
    },
    {
      tx_id: "TX-8836",
      sender_account: "ACC999",
      recipient_account: "ACC888",
      recipient_name: "Unknown Recipient",
      amount: -500000,
      transaction_type: "TRANSFER",
      risk_score: 84.99,
      fraud_probability: 84.99,
      decision: "QUARANTINE",
      status: "ON_HOLD",
      fraud_reason: "High risk transaction detected",
      reasons: ["Unusual transaction velocity", "New device detected", "Recipient differs from usual activity"],
      category: "Transfer",
      label: "Transfer — Unknown Recipient",
      created_at: hoursAgo(3.5)
    },
    {
      tx_id: "TX-8790",
      sender_account: "Account •••• 8842",
      recipient_account: "Netflix",
      recipient_name: "Netflix Entertainment",
      amount: -649,
      transaction_type: "PAYMENT",
      risk_score: 1.5,
      fraud_probability: 1.5,
      decision: "APPROVE",
      status: "APPROVED",
      fraud_reason: "Transaction classified as low risk",
      reasons: [],
      category: "Subscription",
      label: "Netflix",
      created_at: hoursAgo(20)
    },
    {
      tx_id: "TX-8770",
      sender_account: "Account •••• 8842",
      recipient_account: "4521 8890 1123",
      recipient_name: "Rohan Mehta",
      amount: -12500,
      transaction_type: "TRANSFER",
      risk_score: 3.0,
      fraud_probability: 3.0,
      decision: "APPROVE",
      status: "APPROVED",
      fraud_reason: "Transaction classified as low risk",
      reasons: [],
      category: "Transfer",
      label: "Transfer — Rohan Mehta",
      created_at: hoursAgo(28)
    },
    {
      tx_id: "TX-8755",
      sender_account: "Account •••• 8842",
      recipient_account: "Amazon Pay",
      recipient_name: "Amazon Pay",
      amount: -3200,
      transaction_type: "PAYMENT",
      risk_score: 4.2,
      fraud_probability: 4.2,
      decision: "APPROVE",
      status: "APPROVED",
      fraud_reason: "Transaction classified as low risk",
      reasons: [],
      category: "Shopping",
      label: "Amazon",
      created_at: hoursAgo(31)
    }
  ];

  window.transactionService = {
    getTransactions() {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
          return JSON.parse(stored);
        }
      } catch (e) {
        console.error("Error reading stored transactions:", e);
      }
      return DEFAULT_TRANSACTIONS;
    },

    mapEngineTransaction(tx) {
      const userId = (window.config && window.config.USER_ID) || "usr_1001";
      const statusRaw = (tx.status || "").toString();
      const held = statusRaw === "ESCROW_HELD";
      const aborted = statusRaw === "AUTO_ABORTED" || statusRaw === "BLOCKED_BY_SOC";
      const scoreRaw = Number(tx.risk_score || 0);
      const score100 = scoreRaw <= 1 ? Number((scoreRaw * 100).toFixed(2)) : scoreRaw;
      const outgoing = tx.user_id === userId;
      return {
        tx_id: tx.transaction_id || tx.id,
        sender_account: tx.user_id,
        recipient_account: tx.recipient_id,
        recipient_name: tx.recipient_id,
        amount: outgoing ? -Number(tx.amount || 0) : Number(tx.amount || 0),
        transaction_type: "TRANSFER",
        risk_score: score100,
        fraud_probability: score100,
        decision: aborted ? "BLOCK" : (held ? "QUARANTINE" : "APPROVE"),
        status: aborted ? "BLOCKED" : (held ? "ON_HOLD" : "APPROVED"),
        fraud_reason: (tx.reasons && tx.reasons[0]) || (held ? "High risk transaction detected" : "Transaction classified as low risk"),
        reasons: tx.reasons || [],
        category: "Transfer",
        label: "Transfer — " + (tx.recipient_id || "Beneficiary"),
        created_at: tx.timestamp || tx.created_at || new Date().toISOString()
      };
    },

    async refreshFromApi() {
      if (!window.config || !window.config.API_URLS || !window.config.API_URLS.transactions) {
        return this.getTransactions();
      }
      const response = await fetch(window.config.API_URLS.transactions);
      if (!response.ok) {
        throw new Error("Unable to load transactions");
      }
      const rows = await response.json();
      const mapped = (rows || []).map((tx) => this.mapEngineTransaction(tx));
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(mapped));
      } catch (e) {}
      return mapped;
    },

    addTransaction(tx) {
      const current = this.getTransactions();
      const updated = [tx, ...current];
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      } catch (e) {
        console.error("Error saving transaction:", e);
      }
      return updated;
    },

    updateTransaction(txId, patch) {
      const updated = this.getTransactions().map((tx) => tx.tx_id === txId ? { ...tx, ...patch } : tx);
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      } catch (e) {}
      return updated;
    },

    clearHistory() {
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch (e) {}
    }
  };
})();
