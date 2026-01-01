"""
Dynamic sitemap generation for Grownica.
Automatically includes all products, categories, and static pages.

This update expands coverage to:
- Include additional static pages (catalog root, security, articles)
- Provide RU-prefixed variants as separate sitemap sections to reflect
  the language routing scheme implemented via LanguagePrefixMiddleware.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from goods.models import Products, Categories
from articles.models import Article, ArticleCategory


class AlternatesImagesSitemapMixin(Sitemap):
    """Mixin to add hreflang alternates (uk/ru) and image data to sitemap items."""
    include_alternates = True
    include_images = False

    def _abs(self, site, protocol: str, path: str) -> str:
        if not path.startswith('/'):
            path = '/' + path
        return f"{protocol}://{site.domain}{path}"

    def get_item_images(self, item) -> list[dict]:
        """Override in subclasses to return list of {'loc': str, 'caption': str|None} dicts (absolute URLs)."""
        return []

    def get_urls(self, page=1, site=None, protocol=None):
        urls = super().get_urls(page=page, site=site, protocol=protocol)
        if not site or not protocol:
            return urls
        for u in urls:
            item = u.get('item')
            # Build alternates uk/ru based on location()
            if self.include_alternates and item is not None:
                try:
                    path = self.location(item)
                except Exception:
                    path = None
                if path:
                    uk_path = path[3:] if (path == '/ru' or path.startswith('/ru/')) else path
                    ru_path = _ru_prefixed(path)
                    u['alternates'] = [
                        {'lang': 'uk', 'location': self._abs(site, protocol, uk_path)},
                        {'lang': 'ru', 'location': self._abs(site, protocol, ru_path)},
                    ]
            # Images
            if self.include_images and item is not None:
                images = self.get_item_images(item)
                if images:
                    abs_images = []
                    for img in images:
                        loc = img.get('loc') or ''
                        caption = img.get('caption') or ''
                        if loc.startswith('/'):
                            loc = self._abs(site, protocol, loc)
                        abs_images.append({'loc': loc, 'caption': caption})
                    u['images'] = abs_images
        return urls


class StaticViewSitemap(Sitemap):
    """Static pages (home, about, etc.)"""
    protocol = 'https'
    priority = 1.0
    changefreq = 'weekly'
    include_images = True

    def items(self):
        # List of static page URL names
        # Note: catalog root lives in goods app under the 'catalog' namespace
        return [
            'main:home',
            'main:about',
            'main:security',
            'main:articles',
            'catalog:catalog_all',
            'catalog:categories',
        ]

    def location(self, item):
        return reverse(item)


class CategorySitemap(AlternatesImagesSitemapMixin, Sitemap):
    """Product categories"""
    protocol = 'https'
    priority = 0.8
    changefreq = 'monthly'
    include_images = True

    def items(self):
        return Categories.objects.all().order_by('sort_order', 'name')

    def location(self, obj):
        return reverse('catalog:index', kwargs={'category_slug': obj.slug})

    def lastmod(self, obj):
        return getattr(obj, 'updated_at', None)

    def get_item_images(self, obj):
        images = []
        try:
            if obj.image and getattr(obj.image, 'url', ''):
                images.append({'loc': obj.image.url, 'caption': getattr(obj, 'name', '')})
        except Exception:
            pass
        try:
            for img in getattr(obj, 'images', []).all():
                if img.image and getattr(img.image, 'url', ''):
                    images.append({'loc': img.image.url, 'caption': getattr(img, 'alt_text', '')})
        except Exception:
            pass
        return images


class ArticleCategorySitemap(AlternatesImagesSitemapMixin, Sitemap):
    """Categories of articles"""
    protocol = 'https'
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        return ArticleCategory.objects.all().order_by('name_uk')

    def location(self, obj):
        return reverse('articles:category', kwargs={'slug': obj.slug})


class ArticleSitemap(Sitemap):
    """Published articles"""
    protocol = 'https'
    priority = 0.7
    changefreq = 'weekly'

    def items(self):
        return Article.objects.filter(status='published').order_by('-published_at')

    def location(self, obj):
        return reverse('articles:detail', kwargs={'slug': obj.slug})

    def lastmod(self, obj):
        return getattr(obj, 'updated_at', None) or getattr(obj, 'published_at', None)

class ProductSitemap(Sitemap):
    """Individual products with new URL structure"""
    protocol = 'https'
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        # Include all products
        return Products.objects.select_related('category').all()

    def location(self, obj):
        # Uses new URL structure: /<category>/<product>/
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return getattr(obj, 'updated_at', None)


def _ru_prefixed(path: str) -> str:
    """Prefix a path with /ru if not already prefixed.
    Assumes incoming paths start with '/'.
    """
    if not path:
        return '/ru/'
    if path == '/ru' or path.startswith('/ru/'):
        return path
    return '/ru' + path


class StaticViewSitemapRU(StaticViewSitemap):
    """RU-prefixed static pages."""
    def location(self, item):
        return _ru_prefixed(super().location(item))



class CategorySitemapRU(CategorySitemap):
    """RU-prefixed category URLs."""
    def location(self, obj):
        return _ru_prefixed(super().location(obj))


class ProductSitemapRU(ProductSitemap):
    """RU-prefixed product URLs."""
    def location(self, obj):
        return _ru_prefixed(super().location(obj))


class ArticleCategorySitemapRU(ArticleCategorySitemap):
    """RU-prefixed article category URLs."""
    def location(self, obj):
        return _ru_prefixed(super().location(obj))


class ArticleSitemapRU(ArticleSitemap):
    """RU-prefixed article URLs."""
    def location(self, obj):
        return _ru_prefixed(super().location(obj))


# Sitemap index - combines all sitemaps (UK default + RU-prefixed variants)
sitemaps = {
    'static': StaticViewSitemap,
    'categories': CategorySitemap,
    'products': ProductSitemap,
    'article-categories': ArticleCategorySitemap,
    'articles': ArticleSitemap,
    'static-ru': StaticViewSitemapRU,
    'categories-ru': CategorySitemapRU,
    'products-ru': ProductSitemapRU,
    'article-categories-ru': ArticleCategorySitemapRU,
    'articles-ru': ArticleSitemapRU,
}
