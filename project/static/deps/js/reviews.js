(function(){
  const root = document.querySelector('.reviews-section');
  if (!root) return;

  const modal = root.querySelector('#image-modal') || document.getElementById('image-modal');
  if (!modal) return;
  const modalImg   = modal.querySelector('.image-modal__img');
  const modalClose = modal.querySelector('.image-modal__close');
  const modalBg    = modal.querySelector('.image-modal__backdrop');

  function showModal(src, alt){
    if (!src) return;
    modalImg.src = src;
    if (alt) modalImg.alt = alt;
    modal.style.display = 'block';
    document.body.classList.add('modal-open');
    document.body.style.overflow = 'hidden';
  }
  function hideModal(){
    modal.style.display = 'none';
    modalImg.src = '';
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
  }

  root.querySelectorAll('.review-img').forEach(img => {
    img.style.cursor = 'zoom-in';
    img.addEventListener('click', () => showModal(img.currentSrc || img.src, img.alt));
  });

  if (modalClose) modalClose.addEventListener('click', hideModal);
  if (modalBg) modalBg.addEventListener('click', hideModal);
  document.addEventListener('keydown', (e) => {
    if (modal.style.display !== 'block') return;
    if (e.key === 'Escape') hideModal();
  });
})();
