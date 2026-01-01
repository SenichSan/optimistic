from django.contrib import admin
from .models import Article, ArticleCategory
from django import forms
from tinymce.widgets import TinyMCE


class ArticleAdminForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = '__all__'
        widgets = {
            'body_uk': TinyMCE(attrs={'cols': 80, 'rows': 30}),
            'body_ru': TinyMCE(attrs={'cols': 80, 'rows': 30}),
        }


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ("name_uk", "name_ru", "slug")
    search_fields = ("name_uk", "name_ru", "slug")
    prepopulated_fields = {"slug": ("name_uk",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    form = ArticleAdminForm

    list_display = ("title_uk", "status", "published_at", "author")
    list_filter = ("status", "published_at", "categories")
    search_fields = ("title_uk", "title_ru", "slug", "excerpt_uk", "excerpt_ru")
    date_hierarchy = "published_at"

    prepopulated_fields = {"slug": ("title_uk",)}

    filter_horizontal = ("categories",)

    fieldsets = (
        (None, {
            'fields': ("title_uk", "title_ru", "slug", "cover_image", "cover_caption_uk", "cover_caption_ru", "status", "published_at", "author", "categories"),
        }),
        ("Контент", {
            'fields': ("excerpt_uk", "excerpt_ru", "body_uk", "body_ru"),
        }),
        ("SEO", {
            'fields': ("meta_title_uk", "meta_title_ru", "meta_description_uk", "meta_description_ru"),
        }),
    )
