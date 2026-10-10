const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Showcase videos loop on their own (data-autoplay); with reduced motion they stay on their poster frame.
if (prefersReducedMotion) {
  document.querySelectorAll('video[data-autoplay]').forEach((v) => v.removeAttribute('data-autoplay'));
}

Reveal.initialize({
  // DESIGN.md §4: fixed 1280x720 stage; Reveal scales it to any screen.
  width: 1280,
  height: 720,
  margin: 0,
  minScale: 0.2,
  maxScale: 2.0,
  center: false,
  display: 'flex',

  hash: true,
  controls: true,
  progress: true,
  slideNumber: 'c/t',

  transition: prefersReducedMotion ? 'none' : 'fade',
  transitionSpeed: 'default',
  backgroundTransition: prefersReducedMotion ? 'none' : 'fade',

  // Code excerpts step through their lines (data-line-numbers="1|2-3"); math is KaTeX: \( ... \) and \[ ... \].

  plugins: [RevealNotes, RevealHighlight, RevealMath.KaTeX],
});
