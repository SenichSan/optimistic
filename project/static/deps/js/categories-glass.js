// categories-glass.js
document.addEventListener('DOMContentLoaded', function () {
  const cards = document.querySelectorAll('.tm-paging-list .category-card');
  if (!cards.length) return;

  const maxTilt = 8;     // градусы наклона
  const maxTrans = 10;   // px для иконки параллакса

  function onMove(e, card) {
    const rect = card.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    const px = (clientX - rect.left) / rect.width;
    const py = (clientY - rect.top) / rect.height;

    const rotateY = (px - 0.5) * (maxTilt * 2) * -1;
    const rotateX = (py - 0.5) * (maxTilt * 2);

    card.style.transform = `perspective(900px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale(1.03)`;

    const img = card.querySelector('.category-icon');
    if (img) {
      const tx = (px - 0.5) * maxTrans;
      const ty = (py - 0.5) * maxTrans * -1;
      img.style.transform = `translate(${tx.toFixed(1)}px, ${ty.toFixed(1)}px) scale(1.04)`;
    }
  }

  function onLeave(card) {
    card.style.transition = 'transform 420ms cubic-bezier(.2,.9,.25,1)';
    card.style.transform = '';
    const img = card.querySelector('.category-icon');
    if (img) {
      img.style.transition = 'transform 420ms cubic-bezier(.2,.9,.25,1)';
      img.style.transform = '';
    }
    setTimeout(() => {
      card.style.transition = '';
      if (img) img.style.transition = '';
    }, 450);
  }

  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => onMove(e, card));
    card.addEventListener('mouseleave', () => onLeave(card));
    card.addEventListener('touchstart', (e) => onMove(e, card), {passive: true});
    card.addEventListener('touchmove', (e) => onMove(e, card), {passive: true});
    card.addEventListener('touchend', () => onLeave(card));
  });
});
