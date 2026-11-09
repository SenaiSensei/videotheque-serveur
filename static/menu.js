const userMenu = document.querySelector(".user-menu");

if (userMenu) {
  document.addEventListener("click", (event) => {
    if (!userMenu.contains(event.target)) userMenu.removeAttribute("open");
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") userMenu.removeAttribute("open");
  });
}