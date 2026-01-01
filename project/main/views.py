from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from django.db.models import Prefetch
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from goods.models import Categories, Products
from articles.models import Article, ArticleCategory


@method_decorator(ensure_csrf_cookie, name='dispatch')
class HomeView(ListView):
    model = Categories
    template_name = 'main/home.html'  # путь к шаблону
    context_object_name = 'categories'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Categories.objects.order_by('sort_order', 'name')
        context['bestsellers'] = Products.objects.filter(is_bestseller=True).order_by('name')
        # Unique offer products for homepage slider
        context['unique_products'] = (
            Products.objects.filter(is_unique=True).order_by('-updated_at', '-id')
        )
        return context


class AboutView(TemplateView):
    template_name = 'main/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Home - О нас'
        context['content'] = "О нас"
        context['text_on_page'] = "************"
        return context


class SecurityView(TemplateView):
    template_name = 'main/security.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Доп. контекст при необходимости
        return context
    
class ArticlesView(TemplateView):
    template_name = 'main/articles.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Prefetch all published articles per category (newest first)
        published_qs = (
            Article.objects.published()
            .order_by('-published_at', '-id')
            .select_related('author')
            .prefetch_related('categories')
        )
        categories = (
            ArticleCategory.objects.all()
            .prefetch_related(Prefetch('articles', queryset=published_qs, to_attr='published_articles'))
            .order_by('name_uk')
        )
        # Hide empty categories
        categories = [c for c in categories if getattr(c, 'published_articles', [])]
        context['article_categories'] = categories
        return context
    

# def index(request):

#     context = {
#         'title': 'Home - Главная',
#         'content': "Магазин мебели HOME",
#     }

#     return render(request, 'main/home.html', context)


# def about(request):
#     context = {
#         'title': 'Home - О нас',
#         'content': "О нас",
#         'text_on_page': "Текст о том почему этот магазин такой классный, и какой хороший товар."
#     }

#     return render(request, 'main/about.html', context)