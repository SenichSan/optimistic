// bestsellers-tilt.js
// Cursor-follow 3D tilt for product cards, analogous to categories-glass.js
// Targets: .tm-featured-grid > article.tm-product-card

(function(){
  document.addEventListener('DOMContentLoaded', function(){
    // Disable tilt on touch/coarse pointers and small screens
    try {
      const isCoarse = window.matchMedia('(pointer: coarse)').matches;
      const noHover = window.matchMedia('(hover: none)').matches;
      const isSmall = window.matchMedia('(max-width: 768px)').matches;
      if (isCoarse || noHover || isSmall) {
        // Mark root for CSS if needed and skip binding
        document.documentElement.classList.add('tilt-disabled');
        return;
      }
    } catch(_) { /* no-op */ }

    const cards = document.querySelectorAll('.tm-featured-grid article.tm-product-card');
    if (!cards.length) return;

    const maxTilt = 8;     // degrees
    const maxTrans = 10;   // px for image parallax

    function onMove(e, card){
      const rect = card.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      const px = (clientX - rect.left) / rect.width;   // 0..1
      const py = (clientY - rect.top) / rect.height;   // 0..1

      const rotateY = (px - 0.5) * (maxTilt * 2) * -1; // left/right
      const rotateX = (py - 0.5) * (maxTilt * 2);      // up/down

      // mark active to disable CSS hover transform
      card.setAttribute('data-tilt-active', '1');

      // combine perspective + tilt + slight scale
      card.style.transform = `perspective(900px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale(1.03)`;
      card.style.willChange = 'transform';

      // parallax image
      const img = card.querySelector('.tm-card-img');
      if (img) {
        const tx = (px - 0.5) * maxTrans;
        const ty = (py - 0.5) * maxTrans * -1;
        img.style.transform = `translate(${tx.toFixed(1)}px, ${ty.toFixed(1)}px) scale(1.04)`;
        img.style.willChange = 'transform';
      }
    }

    function onLeave(card){
      // smooth return
      card.style.transition = 'transform 420ms cubic-bezier(.2,.9,.25,1)';
      card.style.transform = '';
      const img = card.querySelector('.tm-card-img');
      if (img) {
        img.style.transition = 'transform 420ms cubic-bezier(.2,.9,.25,1)';
        img.style.transform = '';
      }
      setTimeout(() => {
        card.removeAttribute('data-tilt-active');
        card.style.transition = '';
        card.style.willChange = '';
        if (img) { img.style.transition = ''; img.style.willChange = ''; }
      }, 450);
    }

    cards.forEach(card => {
      card.addEventListener('mousemove', (e) => onMove(e, card));
      card.addEventListener('mouseleave', () => onLeave(card));
      // Touch interactions are disabled on non-coarse devices by the early return above
    });
  });
})();
