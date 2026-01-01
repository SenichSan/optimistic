"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from .sitemaps import sitemaps
from .views import robots_txt

from django.conf import settings
from goods.views import ProductView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls', namespace='main')),
    path('catalog/', include('goods.urls', namespace='catalog')),
    path('user/', include('users.urls', namespace='user')),
    path('cart/', include(('carts.urls', 'carts'), namespace='carts')),
    path('orders/', include('orders.urls', namespace='orders')),
    path('articles/', include(('articles.urls', 'articles'), namespace='articles')),

    # Provide a stable root favicon path for crawlers and browsers
    path(
        'favicon.ico',
        RedirectView.as_view(url=f"{settings.STATIC_URL}deps/icons/logo48x48.ico", permanent=True),
        name='favicon'
    ),

    # Dynamic sitemap (use re_path to prevent APPEND_SLASH redirect)
    re_path(r'^sitemap\.xml$', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    # robots.txt
    path('robots.txt', robots_txt, name='robots'),
    
    path('tinymce/', include('tinymce.urls')),
]

if settings.DEBUG:
    # Debug toolbar URLs MUST be before general slug pattern
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Product pages on top level: /<category>/<product>/
# MUST be last - catches any two-slug URLs
urlpatterns += [
    path('<slug:category_slug>/<slug:product_slug>/', ProductView.as_view(), name='product_detail'),
]

"""
www.site.com/admin/
www.site.com
www.site.com/about/
www.site.com/catalog/
www.site.com/catalog/product
"""
