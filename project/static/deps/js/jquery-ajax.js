// Когда html документ готов (прорисован)
$(document).ready(function () {
    // Вспомогательная функция получения CSRF из cookie (на некоторых страницах нет скрытого input)
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    // берем в переменную элемент разметки с id jq-notification для оповещений от ajax
    var successMessage = $("#jq-notification");

    // === Minimal global styles fallback (toasts + cart anim) for pages without catalog.css ===
    function ensureGlobalUiStyles() {
        if (!document.getElementById('tm-global-ui-styles')) {
            var css = "" +
            ".tm-toast-stack{position:fixed;top:20px;right:24px;z-index:12000;display:flex;flex-direction:column;gap:8px;pointer-events:none}"+
            ".tm-toast{pointer-events:auto;display:flex;align-items:center;gap:10px;opacity:0;transform:translateY(-8px);transition:opacity .18s ease,transform .18s ease}"+
            ".tm-toast.visible{opacity:1;transform:translateY(0)}"+
            ".tm-toast--bare .tm-toast-message{color:#FFF2C2;font-weight:700;font-size:16px;letter-spacing:.2px;text-shadow:0 1px 2px rgba(0,0,0,.35),0 0 10px rgba(255,233,176,.55)}"+
            "@keyframes tm-cart-shake{0%{transform:translateZ(0) rotate(0) scale(1)}15%{transform:rotate(-8deg) scale(1.04)}30%{transform:rotate(6deg) scale(1.04)}45%{transform:rotate(-4deg) scale(1.03)}60%{transform:rotate(3deg) scale(1.02)}75%{transform:rotate(-2deg) scale(1.01)}100%{transform:rotate(0) scale(1)}}"+
            "@keyframes tm-cart-bump{0%{transform:translateZ(0) scale(1)}30%{transform:scale(1.18)}60%{transform:scale(0.98)}100%{transform:scale(1)}}"+
            "#tm-cart-component .tm-cart-button.tm-cart-button--shake{animation:tm-cart-shake .6s cubic-bezier(.2,.9,.25,1)}"+
            "#tm-cart-count.tm-cart-count--bump,#tm-cart-component .tm-cart-count.tm-cart-count--bump{animation:tm-cart-bump .5s cubic-bezier(.25,.8,.25,1)}";
            var style = document.createElement('style');
            style.id = 'tm-global-ui-styles';
            style.type = 'text/css';
            style.appendChild(document.createTextNode(css));
            document.head.appendChild(style);
        }
    }
    ensureGlobalUiStyles();

    // === Global bare toast fallback if not provided elsewhere ===
    if (typeof window.showToast !== 'function') {
        window.showToast = function(options){
            ensureGlobalUiStyles();
            var o = (typeof options === 'string') ? { message: options } : (options || {});
            var message = o.message || '';
            var duration = Math.max(1200, Math.min(6000, o.duration || 2000));

            var stack = document.getElementById('tm-toast-stack');
            if (!stack) {
                stack = document.createElement('div');
                stack.id = 'tm-toast-stack';
                stack.className = 'tm-toast-stack';
                stack.setAttribute('aria-live', 'polite');
                stack.setAttribute('aria-atomic', 'true');
                document.body.appendChild(stack);
            }

            var toast = document.createElement('div');
            toast.className = 'tm-toast tm-toast--bare';
            toast.setAttribute('role','status');

            var msg = document.createElement('div');
            msg.className = 'tm-toast-message';
            msg.textContent = message;
            toast.appendChild(msg);
            stack.appendChild(toast);
            requestAnimationFrame(function(){ toast.classList.add('visible'); });

            var timer = setTimeout(dismiss, duration);
            function dismiss(){
                if (!toast) return;
                toast.classList.remove('visible');
                setTimeout(function(){ if (toast) toast.remove(); toast = null; }, 220);
            }
            toast.addEventListener('mouseenter', function(){ clearTimeout(timer); });
            toast.addEventListener('mouseleave', function(){ timer = setTimeout(dismiss, 900); });
            return { dismiss: dismiss };
        };
    }

    // Небольшая функция для анимации корзины (в шапке и во float-виджете)
    function triggerCartAnim() {
        ensureGlobalUiStyles();
        try {
            var btn = document.querySelector('#tm-cart-component .tm-cart-button');
            var floatBadge = document.querySelector('#tm-cart-component .tm-cart-count');
            var headerBadge = document.getElementById('tm-cart-count');

            if (btn) {
                btn.classList.remove('tm-cart-button--shake');
                // перезапуск анимации
                void btn.offsetWidth;
                btn.classList.add('tm-cart-button--shake');
                btn.addEventListener('animationend', function onEnd(){
                    btn.classList.remove('tm-cart-button--shake');
                    btn.removeEventListener('animationend', onEnd);
                });
            }
            [floatBadge, headerBadge].forEach(function(el){
                if (!el) return;
                el.classList.remove('tm-cart-count--bump');
                void el.offsetWidth;
                el.classList.add('tm-cart-count--bump');
                el.addEventListener('animationend', function onEnd(){
                    el.classList.remove('tm-cart-count--bump');
                    el.removeEventListener('animationend', onEnd);
                });
            });
        } catch (e) { /* no-op */ }
    }

    // Ловим собыитие клика по кнопке добавить в корзину
    $(document).on("click", ".add-to-cart", function (e) {
        // Блокируем его базовое действие
        e.preventDefault();

        // Берем элемент счетчика в значке корзины и берем оттуда значение
        var goodsInCartCount = $("#goods-in-cart-count");
        var cartCount = parseInt(goodsInCartCount.text() || 0);

        // Получаем id товара из атрибута data-product-id
        var product_id = $(this).data("product-id");

        // Из атрибута href берем ссылку на контроллер django
        var add_to_cart_url = $(this).attr("href");

        // делаем post запрос через ajax не перезагружая страницу
        $.ajax({
            type: "POST",
            url: add_to_cart_url,
            data: {
                product_id: product_id,
                csrfmiddlewaretoken: $("[name=csrfmiddlewaretoken]").val(),
            },
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            success: function (data) {
                // Сообщение
                successMessage.html(data.message);
                successMessage.fadeIn(400);
                // Через 7сек убираем сообщение
                setTimeout(function () {
                    successMessage.fadeOut(400);
                }, 7000);

                // Toast (если доступен) — компактный, без фона и кнопки
                if (window.showToast) {
                    window.showToast({
                        message: (data && data.message) ? data.message : 'Товар добавлен в корзину',
                        variant: 'bare',
                        duration: 2000
                    });
                }

                // Увеличиваем количество товаров в корзине (отрисовка в шаблоне)
                cartCount++;
                goodsInCartCount.text(cartCount);

                // Меняем содержимое корзины на ответ от django (новый отрисованный фрагмент разметки корзины)
                var cartItemsContainer = $("#cart-items-container");
                cartItemsContainer.html(data.cart_items_html);

                // Обновляем новый виджет, если присутствует
                var $tmCounter = $("#tm-cart-count");
                if ($tmCounter.length && typeof data.total_quantity !== 'undefined') {
                    $tmCounter.text(data.total_quantity);
                }
                var $tmItems = $("#tm-cart-items-container");
                if ($tmItems.length && typeof data.cart_items_html !== 'undefined') {
                    $tmItems.html(data.cart_items_html);
                }

                // Анимация корзины
                triggerCartAnim();

                // Сообщаем новому компоненту о том, что корзина обновилась
                document.dispatchEvent(new Event('cart:updated'));

            },

            error: function (data) {
                console.log("Ошибка при добавлении товара в корзину");
            },
        });
    });

    // Новый обработчик для кнопок в tm-featured-wrapper
    // Кнопка — <button class="add-to-cart-btn" data-product-id data-cart-add-url>
    $(document).on("click", ".add-to-cart-btn", function (e) {
        e.preventDefault();

        var goodsInCartCount = $("#goods-in-cart-count");
        var cartCount = parseInt(goodsInCartCount.text() || 0);

        var product_id = $(this).data("product-id");
        var add_to_cart_url = $(this).data("cart-add-url");
        if (!add_to_cart_url || !product_id) {
            return;
        }

        // Пытаемся взять количество из ближайшей формы на странице товара
        var $form = $(this).closest('form');
        var qtyVal = 1;
        var giftChoiceVal = null;
        var giftChoice2Val = null;
        if ($form.length) {
            var v = parseInt($form.find('.product-quantity-input-number').val(), 10);
            if (!isNaN(v) && v > 0) qtyVal = v;
            var $gift = $form.find('#gift-choice');
            if ($gift.length) {
                giftChoiceVal = $gift.val() || null;
            }
            var $gift2 = $form.find('#gift-choice-2');
            if ($gift2.length) {
                giftChoice2Val = $gift2.val() || null;
            }
        }

        $.ajax({
            type: "POST",
            url: add_to_cart_url,
            data: {
                product_id: product_id,
                quantity: qtyVal,
                gift_choice: giftChoiceVal,
                gift_choice_2: giftChoice2Val,
                csrfmiddlewaretoken: $("[name=csrfmiddlewaretoken]").val(),
            },
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            success: function (data) {
                // Сообщение
                successMessage.html(data.message);
                successMessage.fadeIn(400);
                setTimeout(function () { successMessage.fadeOut(400); }, 7000);

                // Toast (если доступен) — компактный, без фона и кнопки
                if (window.showToast) {
                    window.showToast({
                        message: (data && data.message) ? data.message : 'Товар добавлен в корзину',
                        variant: 'bare',
                        duration: 2000
                    });
                }

                // Увеличиваем количество товаров в корзине (legacy виджет)
                cartCount++;
                goodsInCartCount.text(cartCount);

                // Обновляем legacy контейнер
                var cartItemsContainer = $("#cart-items-container");
                cartItemsContainer.html(data.cart_items_html);

                // Обновляем новый виджет, если присутствует
                var $tmCounter = $("#tm-cart-count");
                if ($tmCounter.length && typeof data.total_quantity !== 'undefined') {
                    $tmCounter.text(data.total_quantity);
                }
                var $tmItems = $("#tm-cart-items-container");
                if ($tmItems.length && typeof data.cart_items_html !== 'undefined') {
                    $tmItems.html(data.cart_items_html);
                }

                // Анимация корзины
                triggerCartAnim();

                // Уведомим новый компонент
                document.dispatchEvent(new Event('cart:updated'));
            },
            error: function () {
                console.log("Ошибка при добавлении товара в корзину (tm-featured)");
            }
        });
    });

    // Ловим собыитие клика по кнопке удалить товар из корзины
    $(document).on("click", ".remove-from-cart", function (e) {
        // Блокируем его базовое действие
        e.preventDefault();

        // Если клик произошёл внутри нового модального компонента —
        // даём сработать новой логике cart-component.js и выходим
        if ($(this).closest('#tm-cart-modal-root').length) {
            return;
        }

        // Берем элемент счетчика в значке корзины и берем оттуда значение
        var goodsInCartCount = $("#goods-in-cart-count");
        var cartCount = parseInt(goodsInCartCount.text() || 0);

        // Получаем id корзины из атрибута data-cart-id
        var cart_id = $(this).data("cart-id");
        // Из атрибута href берем ссылку на контроллер django
        var remove_from_cart = $(this).attr("href");

        // делаем post запрос через ajax не перезагружая страницу
        $.ajax({

            type: "POST",
            url: remove_from_cart,
            data: {
                cart_id: cart_id,
                csrfmiddlewaretoken: $("[name=csrfmiddlewaretoken]").val(),
            },
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            success: function (data) {
                // Сообщение
                successMessage.html(data.message);
                successMessage.fadeIn(400);
                // Через 7сек убираем сообщение
                setTimeout(function () {
                    successMessage.fadeOut(400);
                }, 7000);

                // Уменьшаем количество товаров в корзине (отрисовка)
                cartCount -= data.quantity_deleted;
                goodsInCartCount.text(cartCount);

                // Меняем содержимое корзины на ответ от django (новый отрисованный фрагмент разметки корзины)
                var cartItemsContainer = $("#cart-items-container");
                cartItemsContainer.html(data.cart_items_html);

                // Обновляем новый виджет, если присутствует
                var $tmCounter = $("#tm-cart-count");
                if ($tmCounter.length && typeof data.total_quantity !== 'undefined') {
                    $tmCounter.text(data.total_quantity);
                }
                var $tmItems = $("#tm-cart-items-container");
                if ($tmItems.length && typeof data.cart_items_html !== 'undefined') {
                    $tmItems.html(data.cart_items_html);
                }

                // Сообщаем новому компоненту о том, что корзина обновилась
                document.dispatchEvent(new Event('cart:updated'));

            },

            error: function (data) {
                console.log("Ошибка при добавлении товара в корзину");
            },
        });
    });




    // Теперь + - количества товара 
    // Обработчик события для уменьшения значения
    $(document).on("click", ".decrement", function () {
        // Берем ссылку на контроллер django из атрибута data-cart-change-url
        var url = $(this).data("cart-change-url");
        // Берем id корзины из атрибута data-cart-id
        var cartID = $(this).data("cart-id");
        // Ищем ближайшеий input с количеством 
        var $input = $(this).closest('.input-group').find('.number');
        // Берем значение количества товара
        var currentValue = parseInt($input.val());
        // Если количества больше одного, то только тогда делаем -1
        if (currentValue > 1) {
            $input.val(currentValue - 1);
            // Запускаем функцию определенную ниже
            // с аргументами (id карты, новое количество, количество уменьшилось или прибавилось, url)
            updateCart(cartID, currentValue - 1, -1, url);
        }
    });

    // Обработчик события для увеличения значения
    $(document).on("click", ".increment", function () {
        // Берем ссылку на контроллер django из атрибута data-cart-change-url
        var url = $(this).data("cart-change-url");
        // Берем id корзины из атрибута data-cart-id
        var cartID = $(this).data("cart-id");
        // Ищем ближайшеий input с количеством 
        var $input = $(this).closest('.input-group').find('.number');
        // Берем значение количества товара
        var currentValue = parseInt($input.val());

        $input.val(currentValue + 1);

        // Запускаем функцию определенную ниже
        // с аргументами (id карты, новое количество, количество уменьшилось или прибавилось, url)
        updateCart(cartID, currentValue + 1, 1, url);
    });

    function updateCart(cartID, quantity, change, url) {
        $.ajax({
            type: "POST",
            url: url,
            data: {
                cart_id: cartID,
                quantity: quantity,
                csrfmiddlewaretoken: $("[name=csrfmiddlewaretoken]").val(),
            },
            headers: { 'X-CSRFToken': getCookie('csrftoken') },

            success: function (data) {
                // Сообщение
                successMessage.html(data.message);
                successMessage.fadeIn(400);
                // Через 7сек убираем сообщение
                setTimeout(function () {
                    successMessage.fadeOut(400);
                }, 7000);

                // Изменяем количество товаров в корзине
                var goodsInCartCount = $("#goods-in-cart-count");
                var cartCount = parseInt(goodsInCartCount.text() || 0);
                cartCount += change;
                goodsInCartCount.text(cartCount);

                // Меняем содержимое корзины
                var cartItemsContainer = $("#cart-items-container");
                cartItemsContainer.html(data.cart_items_html);

                // Обновляем новый виджет, если присутствует
                var $tmCounter = $("#tm-cart-count");
                if ($tmCounter.length && typeof data.total_quantity !== 'undefined') {
                    $tmCounter.text(data.total_quantity);
                }
                var $tmItems = $("#tm-cart-items-container");
                if ($tmItems.length && typeof data.cart_items_html !== 'undefined') {
                    $tmItems.html(data.cart_items_html);
                }

            },
            error: function (data) {
                console.log("Ошибка при добавлении товара в корзину");
            },
        });
    }

    // Берем из разметки элемент по id - оповещения от django
    var notification = $('#notification');
    // И через 7 сек. убираем
    if (notification.length > 0) {
        setTimeout(function () {
            notification.alert('close');
        }, 7000);
    }

    // При клике по значку корзины открываем всплывающее(модальное) окно
    $('#modalButton').click(function () {
        $('#exampleModal').appendTo('body');

        $('#exampleModal').modal('show');
    });

    // Собыите клик по кнопке закрыть окна корзины
    $('#exampleModal .btn-close').click(function () {
        $('#exampleModal').modal('hide');
    });

    // Обработчик события радиокнопки выбора способа доставки
    $("input[name='requires_delivery']").change(function () {
        var selectedValue = $(this).val();
        // Скрываем или отображаем input ввода адреса доставки
        if (selectedValue === "1") {
            $("#deliveryAddressField").show();
        } else {
            $("#deliveryAddressField").hide();
        }
    });

    // Форматирования ввода номера телефона в форме (xxx) xxx-хххx
    var phoneInputEl = document.getElementById('id_phone_number');
    if (phoneInputEl) {
        phoneInputEl.addEventListener('input', function (e) {
            var x = e.target.value.replace(/\D/g, '').match(/(\d{0,3})(\d{0,3})(\d{0,4})(\d{0,2})/);
            e.target.value = x[1]
                ? '(' + x[1] + ') '
                    + (x[2] || '')
                    + (x[3] ? '-' + x[3] : '')
                    + (x[4] ? '-' + x[4] : '')
                : '';
        });
    }

    // Проверяем на стороне клинта коррекность номера телефона в форме xxx-xxx-хх-хx
    $('#create_order_form').on('submit', function (event) {
        var phoneNumber = $('#id_phone_number').val();
        var regex = /^\(\d{3}\) \d{3}-\d{4}-\d{2}$/;
        if (!regex.test(phoneNumber)) {
            $('#phone_number_error').show();
            event.preventDefault();
        } else {
            $('#phone_number_error').hide();

            // Очистка номера телефона от скобок и тире перед отправкой формы
            var cleanedPhoneNumber = phoneNumber.replace(/[()\-\s]/g, '');
            $('#id_phone_number').val(cleanedPhoneNumber);
        }
    });

    // Сигнализируем, что обработчики корзины через jQuery инициализированы
    try { window.__cartHandlersReady = true; } catch (_) {}
});