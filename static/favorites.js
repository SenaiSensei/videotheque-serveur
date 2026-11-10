document.addEventListener("submit", async (event) => {
  const form = event.target;
  const button = form.querySelector("button.fav");
  if (!button) return;

  event.preventDefault();
  if (button.disabled) return;
  button.disabled = true;

  try {
    const response = await fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      headers: { "X-Requested-With": "fetch" },
      credentials: "same-origin",
    });
    const type = response.headers.get("Content-Type") || "";
    if (!type.includes("application/json")) throw new Error("réponse inattendue");

    const data = await response.json();
    showToast(data.message, data.category);
    if (response.ok) updateFavorite(form, button, data.favorite);
  } catch (error) {
    form.submit();  // session expirée, API indisponible... : comportement classique
    return;
  } finally {
    button.disabled = false;
  }
});

function updateFavorite(form, button, isFavorite) {
  // Sur la page des favoris, un film retiré disparaît de la liste
  const grid = form.closest("[data-remove-on-unfavorite]");
  if (grid && !isFavorite) {
    form.closest(".film-card").remove();
    if (!grid.querySelector(".film-card")) window.location.reload();
    return;
  }

  form.action = form.action.replace(/\/(add|remove)$/, isFavorite ? "/remove" : "/add");
  const label = isFavorite ? "Retirer des favoris" : "Ajouter aux favoris";
  button.classList.toggle("active", isFavorite);
  button.title = label;
  button.setAttribute("aria-label", label);
  button.setAttribute("aria-pressed", String(isFavorite));
}

function showToast(message, category = "success") {
  let toast = document.querySelector(".toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "toast";
    toast.setAttribute("role", "status");
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.className = `toast flash ${category} visible`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => toast.classList.remove("visible"), 2500);
}