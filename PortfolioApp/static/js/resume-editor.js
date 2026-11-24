const editor = document.querySelector(".resume-editor");

if (editor) {
  function updateControls(section) {
    const entries = Array.from(section.querySelector("[data-entries]").children);
    section.querySelector('[data-entry-action="add"]').disabled = entries.length >= Number(section.dataset.maxEntries);
    for (const [index, entry] of entries.entries()) {
      entry.querySelector('[data-entry-action="up"]').disabled = index === 0;
      entry.querySelector('[data-entry-action="down"]').disabled = index === entries.length - 1;
    }
    for (const control of section.querySelectorAll("[data-entry-action]")) {
      control.hidden = false;
    }
  }

  for (const section of editor.querySelectorAll("[data-edit-section]")) {
    updateControls(section);
  }

  editor.addEventListener("click", (event) => {
    const control = event.target.closest("[data-entry-action]");
    if (!control) return;
    const section = control.closest("[data-edit-section]");
    const entries = section.querySelector("[data-entries]");
    const entry = control.closest("[data-entry]");

    let focusTarget = control;
    switch (control.dataset.entryAction) {
      case "add": {
        const fragment = section.querySelector("template").content.cloneNode(true);
        focusTarget = fragment.querySelector("input:not([type=hidden]), textarea, select");
        entries.append(fragment);
        break;
      }
      case "up":
        if (entry.previousElementSibling) entries.insertBefore(entry, entry.previousElementSibling);
        break;
      case "down":
        if (entry.nextElementSibling) entries.insertBefore(entry.nextElementSibling, entry);
        break;
      case "remove":
        focusTarget = (entry.nextElementSibling || entry.previousElementSibling)?.querySelector("summary")
          || section.querySelector('[data-entry-action="add"]');
        entry.remove();
        break;
    }

    updateControls(section);
    if (focusTarget.disabled) focusTarget = entry.querySelector("summary");
    focusTarget.focus();
  });

  editor.addEventListener("input", (event) => {
    if (event.target.matches("[data-entry-title]")) {
      const label = event.target.closest("[data-entry]").querySelector("[data-entry-label]");
      label.textContent = event.target.value.trim() || "New entry";
    }
  });
}
