import logging
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from threading import Thread
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET
from django.views.generic import FormView, TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf import settings
from django.http import JsonResponse, Http404
from django.core.cache import cache

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from carts.models import Cart
from orders.forms import CreateOrderForm
from orders.models import Order, OrderItem
from orders.utils import send_order_email_to_seller, send_order_email_to_customer
from goods.models import Products

logger = logging.getLogger(__name__)

def get_user_carts(request):
    """Return cart queryset for current owner (user or session).

    Important: ensure session_key exists for anonymous users so that the
    checkout page does not see an empty cart due to missing session.
    """
    if request.user.is_authenticated:
        return Cart.objects.filter(user=request.user)
    # Ensure session exists for anonymous users
    if not request.session.session_key:
        try:
            request.session.create()
        except Exception:
            pass
    return Cart.objects.filter(session_key=request.session.session_key)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CreateOrderView(FormView):
    template_name = 'orders/create_order.html'
    form_class = CreateOrderForm
    success_url = reverse_lazy('main:home')

    def get_initial(self):
        initial = super().get_initial()
        if self.request.user.is_authenticated:
            initial['first_name'] = self.request.user.first_name
            initial['last_name'] = self.request.user.last_name
            initial['email'] = self.request.user.email
        return initial

    def form_valid(self, form):
        try:
            with transaction.atomic():
                cart_items = get_user_carts(self.request)
                
                if cart_items.exists():
                    form_data = form.cleaned_data
                    delivery_address = self.request.POST.get('delivery_address', '').strip()
                    comment = self.request.POST.get('comment', '').strip()

                    # Соберём запрошенные количества по товарам
                    requested = {}
                    for ci in cart_items:
                        if ci.product_id:
                            requested[ci.product_id] = requested.get(ci.product_id, 0) + ci.quantity

                    # Заблокируем строки с товарами и перепроверим остатки под блокировкой
                    product_ids = list(requested.keys())
                    locked_products = list(
                        Products.objects.select_for_update().filter(id__in=product_ids).only('id', 'name', 'quantity')
                    )
                    current_qty = {p.id: p.quantity for p in locked_products}
                    names = {p.id: p.name for p in locked_products}

                    insufficient = []
                    for pid, need in requested.items():
                        have = current_qty.get(pid, 0)
                        if need > have:
                            insufficient.append(f"{names.get(pid, 'Товар')}:\nдоступно {have}, в корзине {need}")

                    if insufficient:
                        messages.error(
                            self.request,
                            "Недостаточно товара на складе:\n" + "\n".join(insufficient)
                        )
                        return redirect('orders:create_order')

                    # Создаем заказ
                    # Нормализуем способ доставки для сохранения читаемой метки
                    raw_delivery = self.request.POST.get('delivery_method', '') or ''
                    delivery_label = 'Нова Пошта' if raw_delivery in ('courier', 'nova', 'nova_poshta') else (raw_delivery or 'Нова Пошта')

                    order = Order.objects.create(
                        user=self.request.user if self.request.user.is_authenticated else None,
                        first_name=form_data['first_name'],
                        last_name=form_data['last_name'],
                        phone_number=form_data['phone_number'],
                        email=form_data['email'],
                        requires_delivery=delivery_label,
                        delivery_address=delivery_address,
                        payment_on_get=form_data.get('payment_on_get', False),
                    )

                    # Создаем позиции заказа
                    for cart_item in cart_items:
                        product = cart_item.product
                        if not product:
                            continue
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            name=product.name,
                            price=product.sell_price(),
                            quantity=cart_item.quantity,
                            gift_choice=getattr(cart_item, 'gift_choice', '') or '',
                            gift_choice_2=getattr(cart_item, 'gift_choice_2', '') or '',
                        )

                    # Списываем остатки под блокировкой
                    for p in locked_products:
                        need = requested.get(p.id, 0)
                        if need:
                            p.quantity = p.quantity - need
                            p.save(update_fields=["quantity"]) 

                    # Очищаем корзину
                    cart_items.delete()

                    # Отправляем уведомления асинхронно после фиксации транзакции,
                    # чтобы не блокировать отклик запроса на медленных SMTP
                    def _send_seller():
                        try:
                            send_order_email_to_seller(order, comment)
                        except Exception:
                            pass
                    def _send_customer():
                        try:
                            if order.email:
                                send_order_email_to_customer(order)
                        except Exception:
                            pass

                    # Планируем отправку после успешного commit
                    transaction.on_commit(lambda: Thread(target=_send_seller, daemon=True).start())
                    transaction.on_commit(lambda: Thread(target=_send_customer, daemon=True).start())

                    # Разрешаем просмотр страницы успеха для этого заказа (гостям и на случай разлогина)
                    allowed = self.request.session.get('allowed_orders') or []
                    if order.id not in allowed:
                        allowed.append(order.id)
                        self.request.session['allowed_orders'] = allowed
                        self.request.session.modified = True

                    messages.success(self.request, 'Заказ успешно оформлен!')
                    return redirect('orders:order_success', order_uuid=order.uuid)
                else:
                    messages.error(self.request, 'Ваша корзина пуста')
                    return redirect('orders:create_order')

        except Exception as e:
            messages.error(self.request, f'Ошибка при оформлении заказа: {str(e)}')
            return redirect('orders:create_order')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Оформление заказа'
        context['order'] = True
        return context


class OrderSuccessView(TemplateView):
    template_name = 'orders/order_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_uuid = self.kwargs.get('order_uuid')
        order = get_object_or_404(Order, uuid=order_uuid)

        # Контроль доступа
        user = self.request.user
        if user.is_authenticated:
            # Разрешаем только владельцу заказа; если заказ гостевой (user=None) — проверяем по сессии
            if order.user_id:
                if order.user_id != user.id:
                    raise Http404()
            else:
                allowed = self.request.session.get('allowed_orders', [])
                if order.id not in allowed:
                    raise Http404()
        else:
            # Гость: только если заказ разрешен для текущей сессии
            allowed = self.request.session.get('allowed_orders', [])
            if order.id not in allowed:
                raise Http404()
        items = OrderItem.objects.filter(order=order).select_related('product')
        items_data = [
            {
                'obj': it,
                'name': it.name,
                'price': it.price,
                'quantity': it.quantity,
                'subtotal': it.price * it.quantity,
                'gift_choice': getattr(it, 'gift_choice', ''),
                'gift_choice_2': getattr(it, 'gift_choice_2', ''),
            }
            for it in items
        ]
        total_qty = sum(d['quantity'] for d in items_data)
        total_sum = sum(d['subtotal'] for d in items_data)

        context['order'] = order
        context['items'] = items
        context['items_data'] = items_data
        context['total_qty'] = total_qty
        context['total_sum'] = total_sum
        return context


# nova poshta поиск отделений
def _np_session():
    """Requests session with retries for Nova Poshta API calls."""
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def search_city(request):
    q = request.GET.get('q', '')[:100]
    if len(q) < 2:
        return JsonResponse([], safe=False)
    key = settings.NOVA_POSHTA_API_KEY or ''
    cache_key = f"np:city:{q.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse(cached, safe=False)
    payload = {
        "apiKey": key,
        "modelName": "AddressGeneral",
        "calledMethod": "searchSettlements",
        "methodProperties": {
            "CityName": q,
            "Limit": 10,
            "Page": 1
        }
    }
    try:
        session = _np_session()
        resp = session.post(
            "https://api.novaposhta.ua/v2.0/json/", json=payload, timeout=6
        )
        data_json = resp.json() if resp.ok else {}
        if data_json.get('success'):
            data = data_json.get('data', [])
            results = [
                {
                    "label": f"{item.get('Present', '')}",
                    "ref": item.get('Ref', '')
                }
                for x in data
                for item in x.get('Addresses', [])
            ]
            cache.set(cache_key, results, 300)
            return JsonResponse(results, safe=False)
        return JsonResponse([], safe=False)
    except Exception as e:
        logger.warning("NP search_city failed: %s", e)
        # Fail gracefully to avoid 500 on UI
        return JsonResponse([], safe=False)


@require_GET
def get_warehouses(request):
    settlement_ref = request.GET.get("settlement_ref")
    if not settlement_ref:
        return JsonResponse({"success": False, "warehouses": []})
    key = settings.NOVA_POSHTA_API_KEY or ''
    cache_key = f"np:wh:{settlement_ref}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse(cached)

    payload = {
        "apiKey": key,
        "modelName": "Address",
        "calledMethod": "getWarehouses",
        "methodProperties": {
            "SettlementRef": settlement_ref
        }
    }
    try:
        session = _np_session()
        resp = session.post(
            "https://api.novaposhta.ua/v2.0/json/", json=payload, timeout=12
        )
        data_json = resp.json() if resp.ok else {}
        if data_json.get("success"):
            warehouses = [
                w.get("Description", "")
                for w in data_json.get("data", [])
            ]
            result = {"success": True, "warehouses": warehouses}
            cache.set(cache_key, result, 300)
            return JsonResponse(result)
    except Exception as e:
        logger.warning("NP get_warehouses failed (ref=%s): %s", settlement_ref, e)
    return JsonResponse({"success": False, "warehouses": []})

def get_warehouse_description(ref):
    key = settings.NOVA_POSHTA_API_KEY or ''
    payload = {
        "apiKey": key,
        "modelName": "Address",
        "calledMethod": "getWarehouses",
        "methodProperties": {
            "Ref": ref
        }
    }
    try:
        session = _np_session()
        res_resp = session.post(
            "https://api.novaposhta.ua/v2.0/json/", json=payload, timeout=12
        )
        res = res_resp.json() if res_resp.ok else {}
        if res.get("success") and res.get("data"):
            return res["data"][0].get("Description", ref)
    except Exception as e:
        logger.warning("NP get_warehouse_description failed (ref=%s): %s", ref, e)
    return ref  # fallback: просто вернуть ref, если что-то пошло не так
