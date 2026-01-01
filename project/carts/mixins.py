from django.template.loader import render_to_string
from django.urls import reverse
from django.shortcuts import get_object_or_404
from carts.models import Cart
from carts.utils import get_user_carts


class CartMixin:
    def _owner_filter(self, request):
        if request.user.is_authenticated:
            return {"user": request.user}
        if not request.session.session_key:
            request.session.create()
        return {"session_key": request.session.session_key}

    def get_cart(self, request, product=None, cart_id=None):
        filters = self._owner_filter(request)
        if product is not None:
            return Cart.objects.filter(product=product, **filters).first()
        if cart_id is not None:
            return get_object_or_404(Cart, id=cart_id, **filters)
        return Cart.objects.filter(**filters).first()

    def render_cart(self, request):
        carts = get_user_carts(request)
        context = {"carts": carts}
        referer = request.META.get('HTTP_REFERER', '')
        if 'orders:create_order' in referer:
            context["order"] = True
        return render_to_string("carts/includes/included_cart.html", context, request=request)
