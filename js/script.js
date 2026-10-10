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

// Demo videos of slide 05. Each column has a .ver-demo button and, right after it, an empty .paso-video
// fragment: the "next" press that reaches that fragment pops the column's video up, and the following press
// (or going back) closes it. The button opens the same video by hand. One shared <dialog id="video-modal">
// and one <video>; opening only swaps the src, so repeated use creates nothing new.
const videoModal = document.getElementById('video-modal');
const modalVideo = videoModal.querySelector('video');
const modalTitulo = videoModal.querySelector('.video-modal-titulo');
const modalEstado = videoModal.querySelector('.video-modal-estado');

function openVideoModal(button) {
  closeVideoModal();
  modalTitulo.textContent = button.dataset.title;
  modalEstado.textContent = '';
  modalVideo.muted = false;
  modalVideo.src = button.dataset.video;
  videoModal.showModal();
  // Focus the dialog, not its close button or the video: Space and the arrows then still reach Reveal,
  // so the clicker keeps driving the slide while the video plays.
  videoModal.focus();
  playWithFallback();
}

// Autoplay with sound is normally allowed right after a click or key press. If the browser blocks it, retry
// muted and say so; if that is blocked too, leave the native controls and ask for a click. Never claim it plays.
function playWithFallback() {
  modalVideo.play().catch((error) => {
    if (error.name !== 'NotAllowedError' || !videoModal.open) return;   // AbortError: closed while starting
    modalVideo.muted = true;
    modalVideo.play()
      .then(() => { modalEstado.textContent = 'Reproduciendo sin sonido: actívalo en los controles del video.'; })
      .catch(() => { modalEstado.textContent = 'El navegador bloqueó la reproducción automática: pulsa reproducir.'; });
  });
}

// Stop playback and drop the source, so nothing keeps playing or downloading behind the slides. Focus is
// released rather than handed back to a .ver-demo button: a focused button would also take the next Space press
// and reopen the video while Reveal advances.
function closeVideoModal() {
  if (!videoModal.open) return;
  modalVideo.pause();
  modalVideo.removeAttribute('src');
  modalVideo.load();
  videoModal.close();
  if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
}

document.querySelectorAll('.ver-demo').forEach((button) => {
  button.addEventListener('click', () => openVideoModal(button));
});

videoModal.querySelector('.video-modal-cerrar').addEventListener('click', closeVideoModal);

// Only a click on the backdrop reaches the <dialog> itself; clicks on the video or its controls do not.
videoModal.addEventListener('click', (event) => {
  if (event.target === videoModal) closeVideoModal();
});

// Escape only closes the video. Caught on the document in the capture phase and stopped there, so Reveal
// does not also open its overview (Escape's default in Reveal).
document.addEventListener('keydown', (event) => {
  if (videoModal.open && event.key === 'Escape') {
    event.preventDefault();
    event.stopPropagation();
    closeVideoModal();
  }
}, true);

// The clicker flow. A single shown fragment that is a .paso-video opens its column's video; any other step,
// forwards or back, closes it. Entering the slide backwards shows all its fragments at once
// (event.fragments.length > 1), which must not pop a video up.
Reveal.on('fragmentshown', (event) => {
  if (event.fragment.classList.contains('paso-video') && event.fragments.length === 1) {
    openVideoModal(event.fragment.closest('figure').querySelector('.ver-demo'));
  } else {
    closeVideoModal();
  }
});
Reveal.on('fragmenthidden', closeVideoModal);

// Any way out of the slide (keys, controls, touch, speaker view, Reveal.next()) closes the video too.
Reveal.on('slidechanged', closeVideoModal);

modalVideo.addEventListener('loadedmetadata', () => {
  modalVideo.style.aspectRatio = `${modalVideo.videoWidth} / ${modalVideo.videoHeight}`;
});

modalVideo.addEventListener('error', () => {
  if (modalVideo.getAttribute('src')) modalEstado.textContent = `No se pudo cargar ${modalVideo.getAttribute('src')}.`;
});
