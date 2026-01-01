from django.contrib import admin
from django.utils.html import format_html
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "preview", "title", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    search_fields = ("title",)
    list_filter = ("is_active",)
    ordering = ("sort_order", "-id")

    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px;">', obj.image.url)
        return ""
    preview.short_description = "Превью"
