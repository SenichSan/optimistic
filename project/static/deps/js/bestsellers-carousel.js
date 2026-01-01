document.addEventListener('click', function(e){
  const btn = e.target.closest('.add-to-cart-btn');
  if (!btn) return;

  // UI feedback (animation) regardless of handler source
  const pressed = btn.getAttribute('aria-pressed') === 'true';
  btn.setAttribute('aria-pressed', String(!pressed));
  if (btn.animate) {
    btn.animate(
      [ { transform: 'translateY(0)' }, { transform: 'translateY(-4px)' }, { transform: 'translateY(0)' } ],
      { duration: 220 }
    );
  }

  // If jQuery cart handlers are ready — let them handle it
  if (window.__cartHandlersReady) return;

  // Fallback: perform fetch POST safely
  e.preventDefault();
  if (btn.disabled || btn.getAttribute('aria-busy') === 'true') return;
  const url = btn.getAttribute('data-cart-add-url');
  const pid = btn.getAttribute('data-product-id');
  if (!url || !pid) return;

  // lock button
  btn.disabled = true;
  btn.setAttribute('aria-busy', 'true');

  // read CSRF from cookie
  function getCookie(name){
    const m = document.cookie.match('(?:^|; )' + name.replace(/([.$?*|{}()\[\]\\\/\+^])/g,'\\$1') + '=([^;]*)');
    return m ? decodeURIComponent(m[1]) : null;
  }

  const payload = new URLSearchParams();
  payload.set('product_id', pid);
  payload.set('quantity', '1');

  fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
      'X-CSRFToken': getCookie('csrftoken') || ''
    },
    body: payload.toString()
  }).then(async (res) => {
    if (!res.ok) throw res;
    return res.json();
  }).then((data) => {
    // Update counters/HTML if present
    try {
      if (typeof data.total_quantity !== 'undefined') {
        const cnt = document.getElementById('tm-cart-count');
        if (cnt) cnt.textContent = data.total_quantity;
      }
      if (data.cart_items_html) {
        const cont = document.getElementById('tm-cart-items-container');
        if (cont) cont.innerHTML = data.cart_items_html;
      }
      if (window.showToast) {
        window.showToast({ message: (data && data.message) ? data.message : 'Товар додано' });
      }
      document.dispatchEvent(new Event('cart:updated'));
    } catch(_) {}
  }).catch(async (err) => {
    // attempt single CSRF refresh on 403
    try {
      if (err && err.status === 403) {
        await fetch(window.location.href, { credentials: 'same-origin' });
        const retry = await fetch(url, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-CSRFToken': getCookie('csrftoken') || ''
          },
          body: payload.toString()
        });
        if (retry.ok) {
          const data = await retry.json();
          if (typeof data.total_quantity !== 'undefined') {
            const cnt = document.getElementById('tm-cart-count');
            if (cnt) cnt.textContent = data.total_quantity;
          }
          if (data.cart_items_html) {
            const cont = document.getElementById('tm-cart-items-container');
            if (cont) cont.innerHTML = data.cart_items_html;
          }
          document.dispatchEvent(new Event('cart:updated'));
          return;
        }
      }
    } catch(_) {}
  }).finally(() => {
    btn.disabled = false;
    btn.removeAttribute('aria-busy');
  });
});
