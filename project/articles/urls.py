from django.urls import path
from . import views

app_name = 'articles'

urlpatterns = [
    path('', views.ArticleListView.as_view(), name='list'),
    path('category/<slug:slug>/', views.ArticleByCategoryView.as_view(), name='category'),
    path('upload/', views.tinymce_image_upload, name='upload'),
    path('<slug:slug>/', views.ArticleDetailView.as_view(), name='detail'),
]
