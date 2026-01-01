document.addEventListener('DOMContentLoaded', function () {
  const productsBlock = document.getElementById('products-block');

  if (!productsBlock) return;

  // Универсальная функция загрузки и замены блока
  async function loadProducts(url, push = true) {
    try {
      productsBlock.classList.add('loading'); // можно показать спиннер через CSS
      const res = await fetch(url, {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'text/html'
        },
        credentials: 'same-origin'
      });
      if (!res.ok) throw new Error('Network error: ' + res.status);
      const html = await res.text();
      productsBlock.innerHTML = html;
      if (push) {
        // показываем "чистый" URL (без ajax-хедеров) для deep-linking
        history.pushState({}, '', url);
      }
      // сместить фокус/скролл к блокy товаров для удобства
      productsBlock.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      console.error('Load products failed', err);
      // можно показать уведомление пользователю
    } finally {
      productsBlock.classList.remove('loading');
    }
  }

  // Перехватываем клики:
  document.body.addEventListener('click', function (e) {
    const a = e.target.closest('a');
    if (!a) return;

    // Если клик по категории
    if (a.classList.contains('tm-paging-link')) {
      e.preventDefault();
      // Обновим UI активной категории
      document.querySelectorAll('.tm-paging-item').forEach(li => li.classList.remove('active'));
      const parent = a.closest('.tm-paging-item');
      if (parent) parent.classList.add('active');

      loadProducts(a.href, true);
      return;
    }

    // Если клик по ссылке пагинации внутри блока
    if (a.closest('#products-block') && a.classList.contains('pagination-link')) {
      e.preventDefault();
      // ссылка вида "?page=2" — нужно построить абсолютный URL: взять current location, replace search
      let url;
      if (a.getAttribute('href').startsWith('?')) {
        // сохранить текущ path (категория) и добавить query
        url = window.location.pathname + a.getAttribute('href');
      } else {
        url = a.href;
      }
      loadProducts(url, true);
    }
  });

  // Обработка back/forward
  window.addEventListener('popstate', function () {
    loadProducts(location.href, false);
  });
});
