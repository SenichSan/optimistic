document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('.fantasy-news-slider').forEach(slider => {
    const slides = slider.querySelectorAll('.fantasy-slide');
    const AUTOPLAY_DELAY = 5000; // 5 секунд
    let currentSlide = [...slides].findIndex(s => s.classList.contains('active'));
    if (currentSlide === -1) currentSlide = 0;

    // Создаём/находим контейнер контролов стрелок
    let controls = slider.querySelector('.fantasy-slider-controls');
    if (!controls) {
      controls = document.createElement('div');
      controls.className = 'fantasy-slider-controls';
      slider.appendChild(controls);
    }

    // Вставляем кнопки (если уже есть — переписываем)
    controls.innerHTML = `
      <button class="fantasy-arrow fantasy-prev" aria-label="Предыдущий">❮</button>
      <button class="fantasy-arrow fantasy-next" aria-label="Следующий">❯</button>
    `;
    const prevBtn = controls.querySelector('.fantasy-prev');
    const nextBtn = controls.querySelector('.fantasy-next');

    // Показ слайда по индексу
    function showSlide(index) {
      if (!slides.length) return;
      index = (index + slides.length) % slides.length;
      slides.forEach((slide, i) => slide.classList.toggle('active', i === index));
      currentSlide = index;
    }

    // Обработчики стрелок
    prevBtn.addEventListener('click', () => {
      showSlide(currentSlide - 1);
      restartAutoplay();
    });
    nextBtn.addEventListener('click', () => {
      showSlide(currentSlide + 1);
      restartAutoplay();
    });

    // Автоплей (один таймер на слайдер)
    let timer = null;
    function startAutoplay() {
      if (timer) clearInterval(timer);
      timer = setInterval(() => {
        showSlide(currentSlide + 1);
      }, AUTOPLAY_DELAY);
    }
    function restartAutoplay() {
      clearInterval(timer);
      startAutoplay();
    }
    startAutoplay();

    // Пауза при наведении
    slider.addEventListener('mouseenter', () => clearInterval(timer));
    slider.addEventListener('mouseleave', () => startAutoplay());

    // Свайп (мобильные)
    let touchStartX = null;
    slider.addEventListener('touchstart', (e) => {
      touchStartX = e.touches[0].clientX;
      clearInterval(timer);
    }, {passive: true});
    slider.addEventListener('touchend', (e) => {
      if (touchStartX === null) return;
      const dx = e.changedTouches[0].clientX - touchStartX;
      if (Math.abs(dx) > 40) {
        if (dx < 0) showSlide(currentSlide + 1);
        else showSlide(currentSlide - 1);
      }
      touchStartX = null;
      restartAutoplay();
    });

    // Клавиши ← → (если фокус внутри слайдера)
    slider.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') { showSlide(currentSlide - 1); restartAutoplay(); }
      if (e.key === 'ArrowRight') { showSlide(currentSlide + 1); restartAutoplay(); }
    });
    // Чтобы ловить keydown, даём tabindex, если его нет
    if (!slider.hasAttribute('tabindex')) slider.setAttribute('tabindex', '0');

    // Инициализация
    showSlide(currentSlide);
  });
});
