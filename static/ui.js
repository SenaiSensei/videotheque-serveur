document.addEventListener("submit", (event) => {
  const form = event.target;
  const message = form.dataset.confirm;
  if (!message) return;
  const skip = form.dataset.confirmSkipIfChecked;
  if (skip && form.elements[skip] && form.elements[skip].checked) return;
  if (!window.confirm(message)) event.preventDefault();
});

function dropBrokenPoster(img) {
  img.addEventListener("error", () => img.remove());
  if (img.complete && img.naturalWidth === 0) img.remove();
}
document.querySelectorAll(".poster img").forEach(dropBrokenPoster);