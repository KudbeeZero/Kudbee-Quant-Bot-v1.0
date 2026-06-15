/** @type {import('tailwindcss').Config} */
// Scans BOTH the Netlify-served marketing HTML and the FastAPI-served
// dashboard/login (kudbee_quant/static) + the JS that builds DOM, so utility
// classes used only from JS are not purged.
module.exports = {
  content: [
    "./*.html",
    "./blog/**/*.html",
    "./assets/js/**/*.js",
    "./kudbee_quant/static/*.html",
    "./kudbee_quant/static/*.js",
  ],
  theme: {
    extend: {
      colors: {
        // Mission-control palette (carried over from the old dashboard tokens).
        ink:    "#07071a",
        panel:  "#0e0e2a",
        edge:   "#1e1e4a",
        honey:  "#ffd700",
        mint:   "#00ff88",
        danger: "#ff4560",
        sky:    "#3a86ff",
        muted:  "#5a6080",
        body:   "#c8d0e8",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "'Courier New'", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
