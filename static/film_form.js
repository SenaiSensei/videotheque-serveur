document.addEventListener("click", (event) => {
  const addButton = event.target.closest("[data-add]");
  if (addButton) {
    addRow(addButton.dataset.add);
    return;
  }

  const removeButton = event.target.closest("[data-remove]");
  if (removeButton) {
    const row = removeButton.closest(".row");
    const list = row.parentElement;
    row.remove();
    if (!list.querySelector(".row")) {
      addRow(list.id);
    }
  }
});

function addRow(listId) {
  const list = document.getElementById(listId);
  const template = document.getElementById(listId + "-template");
  list.appendChild(template.content.cloneNode(true));
  list.lastElementChild.querySelector("input, select").focus();
}