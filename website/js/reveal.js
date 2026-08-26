// Progressive-enhancement fade-up for elements marked .reveal. Runs only if
// IntersectionObserver exists and the visitor hasn't asked for reduced
// motion; otherwise .reveal elements stay exactly as they render, fully
// visible, so a blocked or failed script never hides content.
(function () {
  if (!("IntersectionObserver" in window)) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var items = document.querySelectorAll(".reveal");
  if (!items.length) return;

  var io = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15 }
  );

  items.forEach(function (el, i) {
    el.classList.add("js-armed");
    el.style.transitionDelay = Math.min(i * 40, 200) + "ms";
    io.observe(el);
  });
})();
