// Centralized API configuration — talks to the FastAPI fraud engine.
(function () {
  const apiBase = (window.FASTAPI_BASE_URL || "http://127.0.0.1:8001").replace(/\/$/, "");
  const userId = window.PORTAL_USER_ID || "usr_1001";

  window.config = {
    USE_MOCK_API: false,
    API_BASE: apiBase,
    USER_ID: userId,
    DISPLAY_ACCOUNT: "Account •••• 8842",
    TRUSTED_DEVICE_HASH: "a9f4c3d2e1b0",
    API_URLS: {
      transfer: apiBase + "/api/v1/transfer",
      user: apiBase + "/api/v1/users/" + userId,
      transactions: apiBase + "/api/v1/transactions/" + userId,
      users: apiBase + "/api/v1/admin/users",
      checkFraud: apiBase + "/api/v1/transfer",
      verifyOtp: apiBase + "/api/v1/transactions/verify-otp",
      escrowRelease: apiBase + "/api/v1/escrow/release",
      escrowRefund: apiBase + "/api/v1/escrow/refund",
    }
  };

  window.portalApi = {
    formatInr(amount) {
      return Number(amount || 0).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      });
    },
    applyBalance(amount) {
      const formatted = this.formatInr(amount);
      const balanceEl = document.getElementById("balanceAmount");
      if (balanceEl) balanceEl.dataset.value = formatted;
      const tfBalance = document.getElementById("tfBalance");
      if (tfBalance) tfBalance.dataset.value = formatted;
      const acBalance = document.getElementById("acBalance");
      if (acBalance) acBalance.dataset.value = formatted;
    },
    async loadUser() {
      const url = window.config.API_URLS.user;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error("Unable to load account profile");
      }
      const user = await response.json();
      this.applyBalance(user.account_balance);
      return user;
    }
  };

  window.portalApi.loadUser().catch((err) => {
    console.warn("Could not load live account profile:", err);
  });
})();
