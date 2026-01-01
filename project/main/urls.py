from django.urls import path, include
from django.views.decorators.cache import cache_page

from . import views
# from django.views.decorators.cache import cache_page


from main import views

app_name = 'main'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('security/', views.SecurityView.as_view(), name='security'),
    path('articles/', views.ArticlesView.as_view(), name='articles'),

]

# urlpatterns = [
#     path('', views.IndexView.as_view(), name='index'),
#     path('about/', cache_page(60)(views.AboutView.as_view()), name='about'),
# ]