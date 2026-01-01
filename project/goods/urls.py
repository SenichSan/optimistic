from django.urls import path

from goods import views
from .views import CategoriesView, CatalogView

app_name = 'goods'

urlpatterns = [
    path('search/', views.CatalogView.as_view(), name='search'),
    # Catalog root (all products) at /catalog/
    path('', CatalogView.as_view(), name='catalog_all'),
    path('<slug:category_slug>/', views.CatalogView.as_view(), name='index'),
    # Old product URL removed - now handled at top level as /<category>/<product>/
    # Redirects handled by ProductURLRedirectMiddleware
    path('categories/', views.CategoriesView.as_view(), name='categories'),
]
