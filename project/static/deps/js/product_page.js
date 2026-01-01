document.addEventListener('DOMContentLoaded', function () {
    // Бургер-меню
    const burger = document.querySelector('.header-button-hamburger');
    if (burger) {
        burger.addEventListener('click', function () {
            document.querySelector('.header-menu').classList.toggle('is-show');
            this.classList.toggle('is-show');
        });
    }

    // Кнопки «Избранное»
    document.querySelectorAll('.product-content-favorite-button').forEach(function (item) {
        item.addEventListener('click', function () {
            this.classList.toggle('is-fav');
        });
    });

    // Увеличение количества
    document.querySelectorAll('.product-quantity-input-increase').forEach(function (item) {
        item.addEventListener('click', function () {
            const input = this.parentElement.querySelector('.product-quantity-input-number');
            const currentValue = parseInt(input.value, 10) || 0;
            const maxValue = parseInt(input.getAttribute('max'), 10);
            if (!isNaN(maxValue) && currentValue >= maxValue) {
                input.value = maxValue;
            } else {
                input.value = currentValue + 1;
            }
        });
    });

    // Уменьшение количества
    document.querySelectorAll('.product-quantity-input-decrease').forEach(function (item) {
        item.addEventListener('click', function () {
            const input = this.parentElement.querySelector('.product-quantity-input-number');
            const currentValue = parseInt(input.value, 10) || 0;
            const minValue = parseInt(input.getAttribute('min'), 10);
            if (!isNaN(minValue) && currentValue <= minValue) {
                input.value = minValue;
            } else {
                input.value = currentValue - 1;
            }
        });
    });

    // Кнопка поиска в шапке
    const searchBtn = document.querySelector('.header-button-search');
    if (searchBtn) {
        searchBtn.addEventListener('click', function () {
            document.querySelector('.header-button').classList.toggle('is-show');
            this.classList.toggle('is-show');
        });
    }

    // Инициализация Swiper на странице товара
    if (document.querySelector('.product-swiper')) {
        // Миниатюры
        const productThumbs = new Swiper('.product-thumb-swiper', {
            spaceBetween: 12,
            slidesPerView: 'auto',
            watchSlidesVisibility: true,
            watchSlidesProgress: true,
            breakpoints: {
                768: {
                    spaceBetween: 24,
                }
            }
        });

        // Основной слайдер
        const productSwiper = new Swiper('.product-swiper', {
            loop: false,
            rewind: true,
            slidesPerView: 1,
            spaceBetween: 0,
            centeredSlides: false,
            watchOverflow: true,
            thumbs: { swiper: productThumbs },
        });

        // Счётчик слайдов на главном слайдере был удалён

        // Кнопки «Вперёд/Назад»
        const nextBtn = document.querySelector('.product-image-order-next');
        const prevBtn = document.querySelector('.product-image-order-previous');

        if (nextBtn) {
            nextBtn.addEventListener('click', function () {
                productSwiper.slideNext();
            });
        }
        if (prevBtn) {
            prevBtn.addEventListener('click', function () {
                productSwiper.slidePrev();
            });
        }
    }
});

    // Lightbox
    const modal      = document.getElementById('image-modal');
    const modalImg   = modal.querySelector('.image-modal__img');
    const modalClose = modal.querySelector('.image-modal__close');
    const modalBg    = modal.querySelector('.image-modal__backdrop');
    const modalPrev  = modal.querySelector('.image-modal__prev');
    const modalNext  = modal.querySelector('.image-modal__next');

    // Collect gallery images (from main swiper). Use currentSrc to prefer chosen source
    const galleryImgs = Array.from(document.querySelectorAll('.product-swiper .swiper-slide img'));
    let currentIndex = -1;

    function updateModalSrcByIndex(idx) {
        if (!galleryImgs.length) return;
        // clamp
        if (idx < 0) idx = galleryImgs.length - 1;
        if (idx >= galleryImgs.length) idx = 0;
        currentIndex = idx;
        const el = galleryImgs[currentIndex];
        // Use currentSrc (falls back to src) to pick the actually loaded source
        const src = el.currentSrc || el.src;
        modalImg.src = src;
    }

    function hideTawk(forceDom) {
        try { if (window.Tawk_API && typeof window.Tawk_API.hideWidget === 'function') { window.Tawk_API.hideWidget(); return; } } catch(e){}
        if (!forceDom) return;
        // Fallback: try to hide common containers
        const candidates = document.querySelectorAll('iframe[src*="tawk.to"], iframe[id^="tawk"], div[id^="tawk"], div[class^="tawk"], #tawkchat-minified-wrapper, #tawkchat-status-text-container, #tawkchat-container, #tawkchat-iframe-container');
        candidates.forEach(n=>{ n.style.setProperty('display','none'); n.style.setProperty('visibility','hidden'); n.style.setProperty('opacity','0'); n.style.setProperty('pointer-events','none'); });
    }
    function showTawk() {
        try { if (window.Tawk_API && typeof window.Tawk_API.showWidget === 'function') { window.Tawk_API.showWidget(); return; } } catch(e){}
        // Attempt to revert styles for fallback hidden nodes
        const candidates = document.querySelectorAll('iframe[src*="tawk.to"], iframe[id^="tawk"], div[id^="tawk"], div[class^="tawk"], #tawkchat-minified-wrapper, #tawkchat-status-text-container, #tawkchat-container, #tawkchat-iframe-container');
        candidates.forEach(n=>{ n.style.removeProperty('display'); n.style.removeProperty('visibility'); n.style.removeProperty('opacity'); n.style.removeProperty('pointer-events'); });
    }

    function showModalByIndex(idx) {
        updateModalSrcByIndex(idx);
        modal.style.display = 'block';
        // Hide header, cart button and chat via CSS hook
        document.body.classList.add('modal-open');
        hideTawk(true);
        // Prevent background scroll
        document.body.style.overflow = 'hidden';
    }
    function showModal(src) {
        // derive index by matching src among gallery, else keep direct src
        let idx = galleryImgs.findIndex(el => (el.currentSrc||el.src) === src);
        if (idx === -1) { modalImg.src = src; currentIndex = -1; }
        showModalByIndex(idx === -1 ? 0 : idx);
    }
    function hideModal() {
        modal.style.display = 'none';
        modalImg.src = '';
        document.body.classList.remove('modal-open');
        showTawk();
        // Restore background scroll
        document.body.style.overflow = '';
    }

document.querySelectorAll('.product-swiper .swiper-slide img').forEach(img => {
    img.style.cursor = 'zoom-in';
    img.addEventListener('click', () => showModal(img.src));
});
modalClose.addEventListener('click', hideModal);
modalBg.addEventListener('click', hideModal);
if (modalPrev) modalPrev.addEventListener('click', () => { if (galleryImgs.length) showModalByIndex(currentIndex - 1); });
if (modalNext) modalNext.addEventListener('click', () => { if (galleryImgs.length) showModalByIndex(currentIndex + 1); });

// Close on ESC
document.addEventListener('keydown', (e) => {
  if (!modal || modal.style.display !== 'block') return;
  if (e.key === 'Escape') { hideModal(); }
  else if (e.key === 'ArrowLeft') { if (galleryImgs.length) showModalByIndex(currentIndex - 1); }
  else if (e.key === 'ArrowRight') { if (galleryImgs.length) showModalByIndex(currentIndex + 1); }
});

document.addEventListener('DOMContentLoaded', () => {
  // …существующая инициализация product-swiper…

  // А потом, когда DOM гарантированно готов:
  if (document.querySelector('.tm-featured-carousel')) {
    new Swiper('.tm-featured-carousel', {
      slidesPerView: 4,
      navigation: {
        nextEl: '.swiper-button-next',
        prevEl: '.swiper-button-prev',
      },
      breakpoints: {
        320:  { slidesPerView: 1 },
        640:  { slidesPerView: 2 },
        1024: { slidesPerView: 4 },
      },
    });
  }
});

// Collapsible product description — init ASAP after DOM ready
document.addEventListener('DOMContentLoaded', () => {
  try { document.body.classList.add('js-ready'); } catch(e) {}
  const orig = document.querySelector('.product-content-explanation');
  if (!orig) return;

  // Single container: reuse existing shaded description as content
  const wrap = document.createElement('div');
  wrap.className = 'product-description';
  wrap.id = 'product-description';

  const content = orig; // reuse existing node to avoid double shading
  content.classList.add('product-description__content');
  if (!content.id) content.id = 'product-description-content';

  content.parentNode.insertBefore(wrap, content);
  wrap.appendChild(content);

  const MAX_HEIGHT = 500; // show up to 220px, collapse the rest
  const needCollapse = content.scrollHeight > MAX_HEIGHT;
  if (needCollapse) {
    wrap.classList.add('is-collapsible');
    content.style.maxHeight = MAX_HEIGHT + 'px';
    content.classList.add('is-collapsed');
  }

  const lang = (document.documentElement.getAttribute('lang') || 'uk').toLowerCase();
  const txtMore = lang.startsWith('ru') ? 'читать далее' : 'читати далі';
  const txtLess = lang.startsWith('ru') ? 'скрыть' : 'згорнути';

  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'product-description__toggle';
  btn.id = 'product-description-toggle';
  btn.setAttribute('aria-expanded', 'false');
  btn.setAttribute('aria-controls', 'product-description-content');
  btn.innerHTML = '<span class="product-description__arrow" aria-hidden="true"></span>'+
                  '<span class="product-description__text">'+txtMore+'</span>';
  // Place toggle as sibling after content so it's never clipped by overflow
  wrap.appendChild(btn);
  // Spacing and layout handled purely by CSS

  try { console.debug('[read-more] toggle created:', !!document.getElementById('product-description-toggle')); } catch(e) {}

  // Bottom margin normalization handled by CSS (last-child rule)

  function expand() {
    btn.disabled = true;
    const full = content.scrollHeight;
    content.style.maxHeight = full + 'px';
    content.classList.remove('is-collapsed');
    btn.setAttribute('aria-expanded', 'true');
    btn.querySelector('.product-description__text').textContent = txtLess;
    content.addEventListener('transitionend', function handler(e){
      if (e.propertyName === 'max-height') {
        content.style.maxHeight = 'none';
        btn.disabled = false;
        content.removeEventListener('transitionend', handler);
      }
    });
  }

  function collapse() {
    btn.disabled = true;
    const h = content.scrollHeight;
    content.style.maxHeight = h + 'px';
    void content.offsetHeight;
    content.style.maxHeight = MAX_HEIGHT + 'px';
    content.classList.add('is-collapsed');
    btn.setAttribute('aria-expanded', 'false');
    btn.querySelector('.product-description__text').textContent = txtMore;
    content.addEventListener('transitionend', function handler(e){
      if (e.propertyName === 'max-height') {
        btn.disabled = false;
        content.removeEventListener('transitionend', handler);
      }
    });
  }

  btn.addEventListener('click', () => {
    btn.getAttribute('aria-expanded') === 'true' ? collapse() : expand();
  });
});