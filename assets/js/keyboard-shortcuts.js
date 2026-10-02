// Open & focus the Material search box on Cmd-K (macOS) / Ctrl-K (Windows/Linux),
// in addition to Material's built-in "/" shortcut.
document.addEventListener("keydown", function (e) {
  if ((e.metaKey || e.ctrlKey) && !e.altKey && !e.shiftKey && e.key.toLowerCase() === "k") {
    const input = document.querySelector(".md-search__input");
    if (!input) return;            // search not present on this page
    e.preventDefault();
    const toggle = document.getElementById("__search");  // Material's search toggle (mobile overlay)
    if (toggle && !toggle.checked) toggle.checked = true;
    input.focus();
    input.select();
  }
});
