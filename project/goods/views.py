from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import render, get_object_or_404
from django.utils.translation import get_language
from django.views.generic import DetailView, ListView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Products, Categories
from .utils import q_search
from django.core.cache import cache


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CatalogView(ListView):
    model = Products
    template_name = "goods/catalog.html"
    context_object_name = "goods"
    paginate_by = 10
    allow_empty = False
    slug_url_kwarg = "category_slug"

    def get_queryset(self):
        # Base queryset with prefetch of related images to avoid N+1 in templates
        base_qs = Products.objects.all().prefetch_related('images')

        category_slug = self.kwargs.get(self.slug_url_kwarg)
        species = (self.request.GET.get("species") or "").strip().lower()
        # Default to cubensis for 'sporovi-vidbitki' when no explicit filter provided
        if (category_slug == 'sporovi-vidbitki') and not species:
            species = 'cubensis'
        on_sale = self.request.GET.get("on_sale")
        order_by = self.request.GET.get("order_by")
        query = self.request.GET.get("q")

        # Text search (ensure prefetch is preserved if q_search returns a queryset)
        if query:
            goods = q_search(query)
            try:
                goods = goods.prefetch_related('images')
            except AttributeError:
                goods = base_qs.none()
        else:
            if not category_slug or category_slug == "all":
                goods = base_qs
            else:
                goods = base_qs.filter(category__slug=category_slug)
                if not goods.exists():
                    raise Http404()

        # Soft subdivision for 'Спорові відбитки': filter by species when provided or defaulted
        if species in ("cubensis", "panaeolus"):
            goods = goods.filter(species=species)

        if on_sale:
            goods = goods.filter(discount__gt=0)

        if order_by and order_by != "default":
            goods = goods.order_by(order_by)

        return goods

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Home - Каталог"
        context["slug_url"] = self.kwargs.get(self.slug_url_kwarg)
        # Cache categories list to avoid repeated DB hits
        categories = cache.get('categories_ordered')
        if categories is None:
            categories = Categories.objects.order_by('sort_order', 'name')
            cache.set('categories_ordered', categories, 1800)  # 30 minutes
        context["categories"] = categories
        context['current_category'] = self.kwargs.get(self.slug_url_kwarg, 'all')
        # Provide selected category object (for image + description presentation)
        current_slug = context['current_category']
        context['current_category_obj'] = None
        if current_slug:
            context['current_category_obj'] = Categories.objects.filter(slug=current_slug).first()

        # Expose active species in context (default to cubensis for 'sporovi-vidbitki')
        species = (self.request.GET.get("species") or "").strip().lower()
        if current_slug == 'sporovi-vidbitki' and not species:
            species = 'cubensis'
        context['species'] = species
        
        # Split products by species for the template
        if current_slug == 'sporovi-vidbitki' and not species:
            context['cubensis_list'] = [p for p in context['goods'] if p.species == 'cubensis']
            context['panaeolus_list'] = [p for p in context['goods'] if p.species == 'panaeolus']
        
        context['CUR_LANG'] = get_language()
        return context


    def render_to_response(self, context, **response_kwargs):
        # Если AJAX — возвращаем только partial с товарами
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Обновляем контекст перед рендерингом AJAX-ответа
            context.update(self.get_context_data())
            resp = render(self.request, "goods/_products_list.html", context)
            # Критично: разделить кэши по заголовку и запретить кешировать partial
            try:
                # Append to existing Vary if necessary
                prev_vary = resp.headers.get('Vary')
                vary_val = 'X-Requested-With, Accept'
                if prev_vary:
                    if 'X-Requested-With' not in prev_vary:
                        vary_val = prev_vary + ', X-Requested-With, Accept'
                    else:
                        # ensure Accept included too
                        vary_val = prev_vary if 'Accept' in prev_vary else (prev_vary + ', Accept')
                resp.headers['Vary'] = vary_val
                # Жесткий запрет кэширования у прокси/браузера для фрагментов
                resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                resp.headers['Pragma'] = 'no-cache'
                resp.headers['X-Partial'] = '1'
            except Exception:
                pass
            return resp
        # Полная страница — тоже помечаем Vary, чтобы прокси не путали варианты
        full_resp = super().render_to_response(context, **response_kwargs)
        try:
            prev_vary = full_resp.headers.get('Vary')
            vary_val = 'X-Requested-With, Accept'
            if prev_vary:
                if 'X-Requested-With' not in prev_vary:
                    vary_val = prev_vary + ', X-Requested-With, Accept'
                else:
                    vary_val = prev_vary if 'Accept' in prev_vary else (prev_vary + ', Accept')
            full_resp.headers['Vary'] = vary_val
        except Exception:
            pass
        return full_resp


@method_decorator(ensure_csrf_cookie, name='dispatch')
class ProductView(DetailView):
    model = Products
    template_name = "goods/product.html"
    context_object_name = "product"
    slug_url_kwarg = "product_slug"

    def get_queryset(self):
        return super().get_queryset().prefetch_related('images').select_related('category')

    def get_object(self, queryset=None):
        """
        Get product and validate category_slug.
        If category doesn't match, redirect to correct URL (301).
        """
        if queryset is None:
            queryset = self.get_queryset()
        
        product_slug = self.kwargs.get('product_slug')
        category_slug = self.kwargs.get('category_slug')
        
        # Get product by slug
        product = get_object_or_404(queryset, slug=product_slug)
        
        # Validate that product belongs to the specified category
        if product.category.slug != category_slug:
            # Category mismatch - redirect to correct URL with 301
            correct_url = product.get_absolute_url()
            # Preserve query string if present
            if self.request.META.get('QUERY_STRING'):
                correct_url += '?' + self.request.META['QUERY_STRING']
            # This will be caught by dispatch and returned as response
            self.redirect_response = HttpResponsePermanentRedirect(correct_url)
        
        return product
    
    def dispatch(self, request, *args, **kwargs):
        """Check if get_object set a redirect response."""
        self.redirect_response = None
        response = super().dispatch(request, *args, **kwargs)
        # If get_object set a redirect, return it
        if hasattr(self, 'redirect_response') and self.redirect_response:
            return self.redirect_response
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        # Похожие товары: из той же категории, исключая текущий товар
        related_products = (
            Products.objects
            .filter(category=product.category)
            .exclude(pk=product.pk)
            .order_by('?')[:10]
        )

        # Опции подарка-отпечатка (только для этого селектора)
        gift_options = []
        if getattr(product, 'gift_enabled', False):
            gift_category = Categories.objects.filter(slug='sporovi-vidbitki').first()
            if gift_category:
                # Базовый набор кандидатов из категории "Спорові відбитки"
                gift_qs = (
                    Products.objects
                    .filter(category=gift_category, quantity__gt=0)
                    .order_by('name')
                )

                # Если у текущего товара задан вид (species), фильтруем по нему
                target_species = (product.species or '').strip().lower()
                if target_species in ("cubensis", "panaeolus"):
                    gift_qs = gift_qs.filter(species=target_species)

                # Вытаскиваем локализованные имена для формирования опций
                gift_qs = gift_qs.values('name', 'name_ru')

                cur_lang = get_language() or 'uk'

                def _clean_prefix(s: str) -> str:
                    if not s:
                        return ''
                    s2 = s.strip()
                    prefixes = ['Спорові відбитки', 'Споровые отпечатки']
                    for p in prefixes:
                        if s2.startswith(p):
                            rest = s2[len(p):].lstrip(' :\u2014-')
                            return (rest.strip() or s2)
                    return s2

                gift_options = []
                for row in gift_qs:
                    original = row['name_ru'] if (cur_lang == 'ru' and row.get('name_ru')) else row['name']
                    label = _clean_prefix(original)
                    gift_options.append({'value': original, 'label': label})

        context.update({
            'title': product.name,
            'related_products': related_products,
            'gift_enabled': getattr(product, 'gift_enabled', False),
            'gift_options': gift_options,
        })
        return context


class CategoriesView(ListView):
    model = Categories
    template_name = 'goods/categories.html'
    context_object_name = 'categories'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Все категории"
        context["categories"] = Categories.objects.order_by('sort_order', 'name')
        return context
