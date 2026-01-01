from django.contrib import admin
from .models import Categories, Products, ProductImage



@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ["name", "sort_order"]
    list_editable = ["sort_order"]
    search_fields = [
        "name", "short_description", "description", "meta_title", "meta_description",
        "name_ru", "short_description_ru", "description_ru", "meta_title_ru", "meta_description_ru",
    ]
    fields = [
        "name",
        "name_ru",
        "slug",
        "meta_title",
        "meta_title_ru",
        "short_description",
        "short_description_ru",
        "meta_description",
        "meta_description_ru",
        "description",
        "description_ru",
        "image",
        "seo_image",
        "sort_order",
    ]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    prepopulated_fields = {"slug": ("name",)}
    list_display = ["name", "category", "sort_order", "species", "quantity", "price", "discount", "is_unique", "is_benefit", "gift_enabled", "gift_double"]
    list_editable = ["sort_order", "discount", "is_unique", "is_benefit", "gift_enabled", "gift_double", "species"]
    search_fields = [
        "name", "short_description", "description",
        "name_ru", "short_description_ru", "description_ru",
    ]
    list_filter = ["category", "species", "discount", "quantity", "is_benefit", "is_unique"]
    fields = [
        "name",
        "name_ru",
        "category",
        "slug",
        "short_description",
        "short_description_ru",
        "description",
        "description_ru",
        "image",
        "card_image",
        ("price", "discount"),
        "quantity",
        "is_bestseller",
        "is_unique",
        "is_benefit",
        "gift_enabled",
        "gift_double",
        "species",
        "sort_order",
    ]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "alt_text")
