(() => {
  if (!CSS.supports("color", "light-dark(white, black)")) return;

  const root = document.documentElement;
  const system = window.matchMedia("(prefers-color-scheme: dark)");
  const storageKey = "personalportfolio-theme";

  try {
    const saved = localStorage.getItem(storageKey);
    if (saved === "light" || saved === "dark") root.dataset.theme = saved;
  } catch {
    // A browser can disable storage while still allowing a theme for this page.
  }

  document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector("[data-theme-toggle]");
    if (!toggle) return;

    function isDark() {
      return root.dataset.theme ? root.dataset.theme === "dark" : system.matches;
    }

    function updateToggle() {
      toggle.setAttribute("aria-pressed", String(isDark()));
    }

    toggle.addEventListener("click", () => {
      root.dataset.theme = isDark() ? "light" : "dark";
      updateToggle();
      try {
        localStorage.setItem(storageKey, root.dataset.theme);
      } catch {
        // The selected theme still applies to this page.
      }
    });

    system.addEventListener("change", updateToggle);
    updateToggle();
    toggle.hidden = false;
  });
})();
