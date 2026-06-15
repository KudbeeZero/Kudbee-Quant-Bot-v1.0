// Login: POST the password as JSON, set the session cookie, go to the dashboard.
// External file (no inline script) so the page stays CSP-clean (script-src 'self').
(function () {
  const form = document.getElementById("login-form");
  const msg = document.getElementById("msg");
  const btn = document.getElementById("submit");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    msg.textContent = "";
    btn.disabled = true;
    btn.textContent = "Signing in…";
    try {
      const password = document.getElementById("password").value;
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (res.ok) {
        window.location.href = "/dashboard";
        return;
      }
      if (res.status === 503) {
        msg.textContent = "Login is not configured yet (no dashboard password set).";
      } else if (res.status === 429) {
        msg.textContent = "Too many attempts — wait a minute and try again.";
      } else {
        msg.textContent = "Incorrect password.";
      }
    } catch (err) {
      msg.textContent = "Network error — try again.";
    } finally {
      btn.disabled = false;
      btn.textContent = "Sign in";
    }
  });
})();
