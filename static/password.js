const EYE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>';
const EYE_OFF = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/><path d="M3 3l18 18"/></svg>';

document.querySelectorAll('input[type="password"]').forEach((input) => {
  const wrapper = document.createElement("div");
  wrapper.className = "password-field";
  input.parentNode.insertBefore(wrapper, input);
  wrapper.appendChild(input);

  const button = document.createElement("button");
  button.type = "button";
  button.className = "password-toggle";
  wrapper.appendChild(button);

  const update = () => {
    const visible = input.type === "text";
    const label = visible ? "Masquer le mot de passe" : "Afficher le mot de passe";
    button.innerHTML = visible ? EYE_OFF : EYE;
    button.title = label;
    button.setAttribute("aria-label", label);
    button.setAttribute("aria-pressed", String(visible));
  };

  button.addEventListener("click", () => {
    input.type = input.type === "password" ? "text" : "password";
    update();
    input.focus();
  });

  // Remasque le mot de passe à l'envoi, pour que le navigateur le traite comme tel
  if (input.form) {
    input.form.addEventListener("submit", () => {
      input.type = "password";
      update();
    });
  }

  update();
});