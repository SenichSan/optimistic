(function(){
  function initRelatedSwiper(){
    var container = document.querySelector('.rp-swiper');
    if (!container || typeof Swiper === 'undefined') return;

    var slidesCount = container.querySelectorAll('.swiper-slide').length;
    var canLoop = slidesCount >= 3;

    var swiper = new Swiper(container, {
      slidesPerView: 'auto',
      spaceBetween: 16,
      speed: 500,
      grabCursor: true,
      watchOverflow: true,
      loop: canLoop,
      loopAdditionalSlides: canLoop ? 6 : 0,
      loopedSlides: canLoop ? Math.min(8, slidesCount) : 0,
      observer: true,
      observeParents: true,
      resizeObserver: true,
      navigation: {
        nextEl: '.rp-next',
        prevEl: '.rp-prev'
      },
      breakpoints: {
        576: { spaceBetween: 18 },
        768: { spaceBetween: 20 },
        1200: { spaceBetween: 22 }
      },
      preventClicks: false,
      preventClicksPropagation: false
    });

    setTimeout(function(){ try { swiper.update(); } catch(e){} }, 60);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initRelatedSwiper);
  } else {
    initRelatedSwiper();
  }
})();
