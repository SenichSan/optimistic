document.addEventListener("DOMContentLoaded", function () {
    // Элементы компонента
    const cartComponent = document.getElementById('tm-cart-component');
    const cartButton = cartComponent ? cartComponent.querySelector('.tm-cart-button') : null;
    const cartViewUrl = cartComponent ? cartComponent.dataset.cartViewUrl : null;

    const modalRoot = document.getElementById('tm-cart-modal-root');
    const overlay = modalRoot ? modalRoot.querySelector('.tm-cart-overlay') : null;
    const modal = modalRoot ? modalRoot.querySelector('.tm-cart-modal') : null;
    const modalCloseBtn = modalRoot ? modalRoot.querySelector('.tm-cart-modal-close') : null;
    const itemsContainer = document.getElementById('tm-cart-items-container');
    const counterEl = document.getElementById('tm-cart-count');

    const changeUrl = modalRoot ? modalRoot.dataset.cartUpdateUrl : null; // name: carts:cart_change
    // Кнопка удаления может содержать свой data-cart-remove-url, иначе fallback к общему
    const removeDefaultUrl = modalRoot ? modalRoot.dataset.cartRemoveUrl : null; // name: carts:cart_remove

    // Если нет самой кнопки — выходим. Счётчик и модалка зависят от наличия кнопки.
    if (!cartButton) {
        return;
    }

    // Синхронизация с legacy-частью: реагируем на внешние события обновления корзины
    document.addEventListener('cart:updated', function () {
        loadCartCounter();
    });

    // =================== Живой пересчёт при вводе количества ===================
    // Дебаунс для снижения числа POST-запросов при наборе
    const debouncers = new Map();
    function debouncePost(cartId, qty) {
        clearTimeout(debouncers.get(cartId));
        const t = setTimeout(() => postChange(cartId, qty), 300);
        debouncers.set(cartId, t);
    }

    // Утилиты формата/парсинга
    function parseNumber(text) {
        // оставить цифры и точку/запятую, заменить запятую на точку
        const cleaned = String(text).replace(/[^0-9.,]/g, '').replace(',', '.');
        const n = parseFloat(cleaned);
        return isNaN(n) ? 0 : n;
    }
    function formatMoney(n) {
        // Всегда целые значения (без копеек)
        const rounded = Math.round(Number(n) || 0);
        return String(rounded);
    }

    function normalizeAllPrices() {
        // Привести все цены в модалке к целым: строки, юнит-цены и итоги
        if (!itemsContainer) return;
        // Строки (с валютой внутри элемента)
        itemsContainer.querySelectorAll('.cart-prod-price').forEach((el) => {
            const value = parseNumber(el.textContent);
            el.textContent = formatMoney(value) + ' ₴';
        });
        // Юнит-цены (валюта снаружи strong)
        itemsContainer.querySelectorAll('.cart-prod-unit-price strong').forEach((el) => {
            const value = parseNumber(el.textContent);
            el.textContent = formatMoney(value);
        });
        // Итоги
        const totalSumEl = document.getElementById('tm-cart-total-sum');
        if (totalSumEl) totalSumEl.textContent = formatMoney(parseNumber(totalSumEl.textContent));
        const summarySumEl = document.getElementById('cart-summary-sum');
        if (summarySumEl) summarySumEl.textContent = formatMoney(parseNumber(summarySumEl.textContent));
    }

    function recalcRow(rowEl) {
        if (!rowEl) return { qty: 0, sum: 0 };
        const qtyInput = rowEl.querySelector('.qty-input');
        const unitEl = rowEl.querySelector('.cart-prod-unit-price strong');
        const priceEl = rowEl.querySelector('.cart-prod-price');
        const qty = Math.max(1, parseInt(qtyInput?.value || '1', 10) || 1);
        const unit = parseNumber(unitEl ? unitEl.textContent : '0');
        const line = unit * qty;
        if (priceEl) priceEl.textContent = formatMoney(line) + ' ₴';
        // нормализуем значение инпута (без ведущих нулей)
        if (qtyInput && String(qtyInput.value) !== String(qty)) qtyInput.value = qty;
        return { qty, sum: line };
    }

    function recalcTotals() {
        const rows = itemsContainer ? itemsContainer.querySelectorAll('.cart-row') : [];
        let totalQty = 0;
        let totalSum = 0;
        rows.forEach((row) => {
            const { qty, sum } = recalcRow(row);
            totalQty += qty;
            totalSum += sum;
        });
        const totalSumEl = document.getElementById('tm-cart-total-sum');
        if (totalSumEl) totalSumEl.textContent = formatMoney(totalSum);
        const summaryQtyEl = document.getElementById('cart-summary-quantity');
        if (summaryQtyEl) summaryQtyEl.textContent = String(totalQty);
        const summarySumEl = document.getElementById('cart-summary-sum');
        if (summarySumEl) summarySumEl.textContent = formatMoney(totalSum);
    }

    // Слушаем ввод количества: мгновенно пересчитываем строку и итог, отправляем POST с дебаунсом
    document.addEventListener('input', function (e) {
        const target = e.target;
        if (!(target instanceof HTMLElement)) return;
        if (!target.classList.contains('qty-input')) return;
        const input = target;
        const row = input.closest('.cart-row');
        const cartId = input.dataset.cartId;
        const qty = Math.max(1, parseInt(input.value || '1', 10) || 1);
        recalcRow(row);
        recalcTotals();
        if (cartId) debouncePost(cartId, qty);
    });

    // На change/blur фиксируем минимумы и ещё раз отправляем
    document.addEventListener('change', function (e) {
        const target = e.target;
        if (!(target instanceof HTMLElement)) return;
        if (!target.classList.contains('qty-input')) return;
        const input = target;
        const row = input.closest('.cart-row');
        const cartId = input.dataset.cartId;
        const qty = Math.max(1, parseInt(input.value || '1', 10) || 1);
        recalcRow(row);
        recalcTotals();
        if (cartId) debouncePost(cartId, qty);
    });

    // Инициализируем счётчик сразу при загрузке страницы,
    // чтобы не показывать "0" до первого открытия модалки.
    if (cartViewUrl) {
        loadCartCounter();
        // При возврате на страницу из истории (bfcache) — пересчитать
        window.addEventListener('pageshow', function () {
            loadCartCounter();
        });
        // При переключении вкладки назад — пересчитать
        document.addEventListener('visibilitychange', function () {
            if (document.visibilityState === 'visible') {
                loadCartCounter();
            }
        });
    }

    // Открыть модалку (только если структура модалки присутствует на странице)
    cartButton.addEventListener('click', function () {
        if (modal && overlay && modalRoot) {
            openModal();
            loadCart();
        }
    });

    // Закрыть модалку
    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', closeModal);
    }
    if (overlay) {
        overlay.addEventListener('click', closeModal);
    }

    function openModal() {
        if (!overlay || !modal || !modalRoot) return;
        overlay.hidden = false;
        modal.hidden = false;
        modalRoot.classList.add('open');
        document.body.style.overflow = 'hidden';
        document.body.setAttribute('data-modal-open', 'true');
    }

    function closeModal() {
        if (!overlay || !modal || !modalRoot) return;
        overlay.hidden = true;
        modal.hidden = true;
        modalRoot.classList.remove('open');
        document.body.style.overflow = '';
        document.body.removeAttribute('data-modal-open');
    }

    // Загрузка содержимого корзины
    function loadCart() {
        if (!cartViewUrl) return;
        fetch(cartViewUrl, { credentials: 'same-origin', cache: 'no-store' })
            .then((r) => r.json())
            .then((data) => {
                if (itemsContainer && typeof data.cart_items_html !== 'undefined') {
                    itemsContainer.innerHTML = data.cart_items_html;
                }
                if (counterEl && typeof data.total_quantity !== 'undefined') {
                    counterEl.textContent = data.total_quantity;
                }
                // Итого в модалке, если есть отдельный элемент
                const totalSumEl = document.getElementById('tm-cart-total-sum');
                if (totalSumEl && typeof data.total_sum !== 'undefined') {
                    totalSumEl.textContent = formatMoney(parseNumber(data.total_sum));
                }
                normalizeAllPrices();
            })
            .catch(() => {});
    }

    // Лёгкая версия загрузки: только обновить счётчик и, если есть, сумму
    function loadCartCounter() {
        if (!cartViewUrl) return;
        fetch(cartViewUrl, { credentials: 'same-origin' })
            .then((r) => r.json())
            .then((data) => {
                if (counterEl && typeof data.total_quantity !== 'undefined') {
                    counterEl.textContent = data.total_quantity;
                }
                const totalSumEl = document.getElementById('tm-cart-total-sum');
                if (totalSumEl && typeof data.total_sum !== 'undefined') {
                    totalSumEl.textContent = formatMoney(parseNumber(data.total_sum));
                }
                normalizeAllPrices();
            })
            .catch(() => {});
    }

    // Делегирование кликов: +/- и удаление
    document.addEventListener('click', function (e) {
        // Увеличение количества
        if (e.target.classList.contains('qty-increment')) {
            const input = e.target.closest('.cart-row-qty')?.querySelector('.qty-input');
            if (!input) return;
            const cartId = input.dataset.cartId;
            const newQty = parseInt(input.value || '0', 10) + 1;
            input.value = newQty;
            postChange(cartId, newQty);
        }

        // Уменьшение количества
        if (e.target.classList.contains('qty-decrement')) {
            const input = e.target.closest('.cart-row-qty')?.querySelector('.qty-input');
            if (!input) return;
            const current = parseInt(input.value || '1', 10);
            if (current > 1) {
                const cartId = input.dataset.cartId;
                const newQty = current - 1;
                input.value = newQty;
                postChange(cartId, newQty);
            }
        }

        // Удаление позиции
        if (e.target.classList.contains('remove-from-cart')) {
            const btn = e.target;
            const cartId = btn.dataset.cartId;
            const url = btn.dataset.cartRemoveUrl || removeDefaultUrl;
            if (!cartId || !url) return;
            postRemove(cartId, url);
        }
    });

    function postChange(cartId, quantity) {
        if (!changeUrl || !cartId) return;
        const body = new URLSearchParams();
        body.append('cart_id', String(cartId));
        body.append('quantity', String(quantity));
        fetch(changeUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body,
            credentials: 'same-origin',
        })
            .then((r) => r.json())
            .then((data) => {
                applyCartResponse(data);
            })
            .catch(() => {});
    }

    function postRemove(cartId, url) {
        const body = new URLSearchParams();
        body.append('cart_id', String(cartId));
        fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body,
            credentials: 'same-origin',
        })
            .then((r) => r.json())
            .then((data) => {
                applyCartResponse(data);
            })
            .catch(() => {});
    }

    function applyCartResponse(data) {
        // 1) Точечное обновление DOM списка позиций без перерисовки изображений
        if (data && typeof data.cart_items_html !== 'undefined' && itemsContainer) {
            try {
                const tmp = document.createElement('div');
                tmp.innerHTML = data.cart_items_html;

                const newRows = Array.from(tmp.querySelectorAll('.cart-row'));
                const newIds = new Set(newRows.map(r => r.getAttribute('data-cart-id')));

                // a) Удалить строки, которых больше нет
                Array.from(itemsContainer.querySelectorAll('.cart-row')).forEach((oldRow) => {
                    const id = oldRow.getAttribute('data-cart-id');
                    if (!newIds.has(id)) {
                        oldRow.remove();
                    }
                });

                // b) Обновить существующие строки (только правые части), добавить новые
                newRows.forEach((newRow) => {
                    const id = newRow.getAttribute('data-cart-id');
                    const oldRow = itemsContainer.querySelector(`.cart-row[data-cart-id="${CSS.escape(id)}"]`);
                    if (oldRow) {
                        const oldMid = oldRow.querySelector('.cart-row-mid');
                        const oldQty = oldRow.querySelector('.cart-row-qty');
                        const oldPrice = oldRow.querySelector('.cart-row-price');

                        const newMid = newRow.querySelector('.cart-row-mid');
                        const newQty = newRow.querySelector('.cart-row-qty');
                        const newPrice = newRow.querySelector('.cart-row-price');

                        if (oldMid && newMid) oldMid.innerHTML = newMid.innerHTML;
                        if (oldQty && newQty) oldQty.innerHTML = newQty.innerHTML;
                        if (oldPrice && newPrice) oldPrice.innerHTML = newPrice.innerHTML;
                    } else {
                        // Добавить новую строку (если появилась новая позиция)
                        itemsContainer.querySelector('.cart-list')
                            ?.appendChild(newRow);
                    }
                });
            } catch (e) {
                // Фолбэк: если что-то пошло не так — полная замена, как раньше
                itemsContainer.innerHTML = data.cart_items_html;
            }
        }
        if (counterEl && typeof data.total_quantity !== 'undefined') {
            counterEl.textContent = data.total_quantity;
        }
        const totalSumEl = document.getElementById('tm-cart-total-sum');
        if (totalSumEl && typeof data.total_sum !== 'undefined') {
            totalSumEl.textContent = formatMoney(parseNumber(data.total_sum));
        }
        // Обновим блоки итогов внизу partial'а, если они присутствуют
        const summaryQtyEl = document.getElementById('cart-summary-quantity');
        if (summaryQtyEl && typeof data.total_quantity !== 'undefined') {
            summaryQtyEl.textContent = String(data.total_quantity);
        }
        const summarySumEl = document.getElementById('cart-summary-sum');
        if (summarySumEl && typeof data.total_sum !== 'undefined') {
            summarySumEl.textContent = formatMoney(parseNumber(data.total_sum));
        }
        normalizeAllPrices();
    }

    // Вспомогательная функция получения CSRF
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                cookie = cookie.trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
