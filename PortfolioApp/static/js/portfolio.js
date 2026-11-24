(() => {
  const allowPortraitMotion = window.matchMedia(
    "(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)"
  );
  let activePortrait;
  let readingArticle;
  let readingProgress;
  let progressFrame;

  function resetPortrait() {
    if (!activePortrait) return;
    activePortrait.style.removeProperty("--portrait-x");
    activePortrait.style.removeProperty("--portrait-y");
    activePortrait.removeAttribute("data-tracking");
    activePortrait = undefined;
  }

  document.addEventListener("pointermove", (event) => {
    if (!allowPortraitMotion.matches || event.pointerType !== "mouse") return;
    const portrait = event.target instanceof Element && event.target.closest("[data-portrait]");
    if (!portrait) return;

    const bounds = portrait.getBoundingClientRect();
    portrait.style.setProperty("--portrait-x", `${(event.clientX - bounds.left) / bounds.width * 100}%`);
    portrait.style.setProperty("--portrait-y", `${(event.clientY - bounds.top) / bounds.height * 100}%`);
    portrait.setAttribute("data-tracking", "");
    activePortrait = portrait;
  });

  document.addEventListener("pointerout", (event) => {
    const destination = event.relatedTarget;
    const stayedInside = destination instanceof Node && activePortrait?.contains(destination);
    if (activePortrait?.contains(event.target) && !stayedInside) {
      resetPortrait();
    }
  });
  allowPortraitMotion.addEventListener("change", resetPortrait);

  function updateProgress() {
    progressFrame = undefined;
    const articleEnd = readingArticle.getBoundingClientRect().bottom + window.scrollY;
    const availableScroll = Math.min(articleEnd, document.documentElement.scrollHeight) - window.innerHeight;
    const progress = availableScroll > 0 ? Math.min(1, Math.max(0, window.scrollY / availableScroll)) : 0;
    readingProgress.style.setProperty("--reading-progress", progress);
  }

  function scheduleProgress() {
    if (readingArticle && progressFrame === undefined) {
      progressFrame = window.requestAnimationFrame(updateProgress);
    }
  }

  function findReadingArticle() {
    if (progressFrame !== undefined) {
      window.cancelAnimationFrame(progressFrame);
      progressFrame = undefined;
    }
    readingArticle = document.querySelector("[data-reading-article]");
    readingProgress = document.querySelector("[data-reading-progress]");
    if (readingArticle && readingProgress) {
      readingProgress.hidden = false;
      scheduleProgress();
    }
  }

  findReadingArticle();
  window.addEventListener("scroll", scheduleProgress, { passive: true });
  window.addEventListener("resize", scheduleProgress);
  window.addEventListener("hashchange", findReadingArticle);
})();
