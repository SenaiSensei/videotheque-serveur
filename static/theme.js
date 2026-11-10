const themeButton = document.querySelector(".theme-toggle");

if (themeButton) {
  const root = document.documentElement;
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)");

  const currentTheme = () => root.dataset.theme || (systemDark.matches ? "dark" : "light");

  const updateLabel = () => {
    const label = currentTheme() === "dark" ? "Passer au thème clair" : "Passer au thème sombre";
    themeButton.title = label;
    themeButton.setAttribute("aria-label", label);
  };

  themeButton.addEventListener("click", () => {
    const theme = currentTheme() === "dark" ? "light" : "dark";
    root.dataset.theme = theme;
    try { localStorage.setItem("theme", theme); } catch (e) {}
    updateLabel();
  });

  systemDark.addEventListener("change", updateLabel);
  themeButton.hidden = false; // le bouton n'apparaît que si JavaScript fonctionne
  updateLabel();
}