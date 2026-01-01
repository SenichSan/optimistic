from __future__ import annotations

import os
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.files.storage import default_storage
from django.core.cache import cache

from .models import Categories, Products, ProductImage
from common.image_utils import (
    generate_icon_variants,
    generate_formats_noresize,
    generate_card_variants,
)


def _fs_path_from_storage(name: str) -> str:
    """Resolve absolute filesystem path for a stored file name.
    Works for FileSystemStorage; for others, best-effort using MEDIA_ROOT.
    """
    # default_storage may have .path (FileSystemStorage)
    try:
        return default_storage.path(name)  # type: ignore[attr-defined]
    except Exception:
        return os.path.join(settings.MEDIA_ROOT, name)


@receiver(post_save, sender=Categories)
def categories_generate_icon_variants(sender, instance: Categories, **kwargs):
    """On category save, invalidate cached categories and (re)generate image variants."""
    # Invalidate cached ordered categories so meta_description changes appear immediately
    try:
        cache.delete('categories_ordered')
    except Exception:
        pass
    # Icon-sized variants for main category image (used in lists/cards)
    image_field = getattr(instance, "image", None)
    if image_field and getattr(image_field, "name", ""):
        try:
            src_path = _fs_path_from_storage(image_field.name)
            generate_icon_variants(src_path, size=(128, 128))
        except Exception:
            # Fail silently; this is a best-effort optimization and should not block saving
            pass

    # SEO image: generate no-resize formats and 800x450 cover variants for category presentation block
    seo_field = getattr(instance, "seo_image", None)
    if seo_field and getattr(seo_field, "name", ""):
        try:
            seo_src = _fs_path_from_storage(seo_field.name)
            # Create side-by-side AVIF/WebP without resizing
            generate_formats_noresize(seo_src, image_type="background", overwrite=False)
            # Create sized cover variants expected by templates (800x450)
            generate_icon_variants(seo_src, size=(800, 450), mode="cover")
        except Exception:
            pass


@receiver(post_save, sender=Products)
def products_generate_image_variants(sender, instance: Products, **kwargs):
    """On product save, generate AVIF/WebP next to original files WITHOUT resizing."""
    # Main product image
    image_field = getattr(instance, "image", None)
    if image_field and getattr(image_field, "name", ""):
        try:
            src_path = _fs_path_from_storage(image_field.name)
            generate_formats_noresize(src_path, image_type="product", overwrite=False)
            # Generate card-sized variants (no blur-extend), to avoid "baked" background
            generate_card_variants(src_path, size_desktop=(230,160), size_mobile=(200,160), background_blur=False)
        except Exception:
            pass

    # Card-specific image
    card_field = getattr(instance, "card_image", None)
    if card_field and getattr(card_field, "name", ""):
        try:
            src_path = _fs_path_from_storage(card_field.name)
            generate_formats_noresize(src_path, image_type="product", overwrite=False)
            # Ensure card image also has card-sized variants (no blur-extend)
            generate_card_variants(src_path, size_desktop=(230,160), size_mobile=(200,160), background_blur=False)
        except Exception:
            pass


@receiver(post_save, sender=ProductImage)
def product_images_generate_variants(sender, instance: ProductImage, **kwargs):
    """On gallery image save, generate AVIF/WebP next to original WITHOUT resizing."""
    image_field = getattr(instance, "image", None)
    if image_field and getattr(image_field, "name", ""):
        try:
            src_path = _fs_path_from_storage(image_field.name)
            generate_formats_noresize(src_path, image_type="product", overwrite=False)
        except Exception:
            pass
