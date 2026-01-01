from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.urls import reverse
import os
import uuid

from .models import Article, ArticleCategory


class ArticleListView(ListView):
    template_name = 'articles/list.html'
    context_object_name = 'articles'
    paginate_by = 12

    def get_queryset(self):
        qs = Article.objects.published().select_related('author').prefetch_related('categories')
        return qs


class ArticleDetailView(DetailView):
    model = Article
    template_name = 'articles/page_tittle.html'
    context_object_name = 'article'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return Article.objects.published().select_related('author').prefetch_related('categories')


class ArticleByCategoryView(ListView):
    template_name = 'articles/category_list.html'
    context_object_name = 'articles'
    paginate_by = 12

    def get_queryset(self):
        self.category = get_object_or_404(ArticleCategory, slug=self.kwargs['slug'])
        return (
            Article.objects.published()
            .filter(categories=self.category)
            .select_related('author')
            .prefetch_related('categories')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['category'] = self.category
        return ctx


@require_POST
@login_required
@csrf_exempt
def tinymce_image_upload(request):
    # Expect field name 'file' from TinyMCE
    f = request.FILES.get('file')
    if not f:
        return HttpResponseBadRequest('No file uploaded')

    # Basic allowlist
    name = f.name.lower()
    if not (name.endswith('.jpg') or name.endswith('.jpeg') or name.endswith('.png') or name.endswith('.webp') or name.endswith('.gif') or name.endswith('.avif')):
        return HttpResponseBadRequest('Unsupported file type')

    # Path: media/articles/content/<uuid>_<orig>
    filename = f"{uuid.uuid4().hex}_{os.path.basename(name)}"
    rel_path = os.path.join('articles', 'content', filename)
    saved_path = default_storage.save(rel_path, ContentFile(f.read()))

    url = settings.MEDIA_URL + saved_path.replace('\\', '/')

    # TinyMCE expects JSON with { location: url }
    return JsonResponse({'location': url})
