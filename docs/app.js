// app.js — keyboard-driven navigation over the inline <section class="slide">
// elements in index.html. No fetch, no build step: everything the deck needs
// is already in the DOM, so this works when the file is opened directly from
// disk in any browser, including Chrome's strict file:// origin policy.

(function () {
  const slides = SLIDE_MANIFEST.map((id) => document.getElementById(id)).filter(Boolean);
  if (slides.length !== SLIDE_MANIFEST.length) {
    console.warn(
      "app.js: manifest/DOM mismatch —", SLIDE_MANIFEST.length, "in manifest,",
      slides.length, "found in the document. Check slide ids match manifest.js."
    );
  }

  let current = 0;

  function slideIndexFromHash() {
    const id = location.hash.replace(/^#/, "");
    const idx = SLIDE_MANIFEST.indexOf(id);
    return idx === -1 ? 0 : idx;
  }

  function render() {
    slides.forEach((s, i) => s.classList.toggle("active", i === current));
    const progress = document.getElementById("progress");
    if (progress) {
      progress.style.width = ((current + 1) / slides.length) * 100 + "%";
    }
    const indexLabel = document.getElementById("slide-index");
    if (indexLabel) {
      indexLabel.textContent = `${current + 1} / ${slides.length}`;
    }
    history.replaceState(null, "", "#" + SLIDE_MANIFEST[current]);
  }

  function goTo(i) {
    current = Math.max(0, Math.min(slides.length - 1, i));
    render();
  }

  function next() { goTo(current + 1); }
  function prev() { goTo(current - 1); }

  document.addEventListener("keydown", (e) => {
    switch (e.key) {
      case "ArrowRight":
      case "ArrowDown":
      case "PageDown":
      case " ":
        next();
        e.preventDefault();
        break;
      case "ArrowLeft":
      case "ArrowUp":
      case "PageUp":
        prev();
        e.preventDefault();
        break;
      case "Home":
        goTo(0);
        break;
      case "End":
        goTo(slides.length - 1);
        break;
      case "f":
      case "F":
        if (document.fullscreenElement) {
          document.exitFullscreen();
        } else {
          document.documentElement.requestFullscreen().catch(() => {});
        }
        break;
    }
  });

  // Click the right/left thirds of the deck to navigate, for a mouse-only
  // presenter setup.
  document.getElementById("deck").addEventListener("click", (e) => {
    const third = window.innerWidth / 3;
    if (e.clientX > third * 2) next();
    else if (e.clientX < third) prev();
  });

  current = slideIndexFromHash();
  window.addEventListener("hashchange", () => { current = slideIndexFromHash(); render(); });
  render();
})();
