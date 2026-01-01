from __future__ import annotations

import os
from typing import Optional

from django import template
from django.core.files.storage import default_storage
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.templatetags.static import static
from django.contrib.staticfiles import finders
from django.conf import settings
import logging

register = template.Library()

logger = logging.getLogger(__name__)


@register.simple_tag
def product_image_picture(product, size: str = "400x300", classes: str = "", alt: Optional[str] = None,
                         width: int = 400, height: int = 300, loading: str = "lazy", fetchpriority: Optional[str] = None):
    """
    Render a <picture> for product image with AVIF/WebP priority and fallback to original.
    Usage:
      {% product_image_picture product '400x300' 'product-card-img' product.name 400 300 'lazy' %}
    """
    alt_attr = alt or getattr(product, "name", "")
    class_attr = classes or ""

    # Try main product image first
    img_field = getattr(product, "image", None)
    if not img_field or not getattr(img_field, "name", ""):
        # Try first additional image
        try:
            images = getattr(product, "images", None)
            if images and images.exists():
                img_field = images.first().image
        except Exception:
            pass

    if img_field and getattr(img_field, "name", ""):
        try:
            orig_url = img_field.url
        except Exception:
            orig_url = None

        if orig_url:
            name = img_field.name
            avif_name = _variant_name(name, size, "avif")
            webp_name = _variant_name(name, size, "webp")

            avif_url = _url_if_exists(avif_name)
            webp_url = _url_if_exists(webp_name)

            # Root-level fallbacks without size suffix
            root, _ext = os.path.splitext(name)
            root_avif = _url_if_exists(f"{root}.avif")
            root_webp = _url_if_exists(f"{root}.webp")

            if getattr(settings, 'DEBUG', False):
                logger.debug(
                    "product_image_picture: name=%s size=%s avif=%s webp=%s root_avif=%s root_webp=%s orig=%s",
                    name, size, bool(avif_url), bool(webp_url), bool(root_avif), bool(root_webp), bool(orig_url)
                )

            parts = ["<picture>"]
            # Prefer sized sources; if absent, add root-level sources
            if avif_url:
                parts.append(f"<source srcset=\"{avif_url}\" type=\"image/avif\">")
            elif root_avif:
                parts.append(f"<source srcset=\"{root_avif}\" type=\"image/avif\">")
            if webp_url:
                parts.append(f"<source srcset=\"{webp_url}\" type=\"image/webp\">")
            elif root_webp:
                parts.append(f"<source srcset=\"{root_webp}\" type=\"image/webp\">")

            # Fallback <img> src preference
            img_src = webp_url or avif_url or root_webp or root_avif or orig_url
            fp_attr = f" fetchpriority=\"{fetchpriority}\"" if fetchpriority else ""
            parts.append(
                f"<img src=\"{img_src}\" alt=\"{alt_attr}\" class=\"{class_attr}\" width=\"{width}\" height=\"{height}\" loading=\"{loading}\" decoding=\"async\"{fp_attr}>"
            )
            parts.append("</picture>")
            return mark_safe("".join(parts))

    # Ultimate fallback to placeholder
    fallback = static("deps/images/placeholder.png")
    fp_attr = f" fetchpriority=\"{fetchpriority}\"" if fetchpriority else ""
    return mark_safe(
        f"<img src=\"{fallback}\" alt=\"{alt_attr}\" class=\"{class_attr}\" width=\"{width}\" height=\"{height}\" loading=\"{loading}\" decoding=\"async\"{fp_attr}>"
    )


def _variant_name(orig_name: str, size: str, ext: str) -> str:
    root, _ext = os.path.splitext(orig_name)
    return f"{root}_{size}.{ext}"


def _url_if_exists(name: str) -> Optional[str]:
    try:
        if default_storage.exists(name):
            return default_storage.url(name)
    except Exception:
        return None
    return None

def _orig_url_safe(image_field) -> Optional[str]:
    try:
        return image_field.url
    except Exception:
        return None

def _best_variant_urls(name: str, size: str):
    """Return tuple (avif_url, webp_url) if those sized variants exist."""
    avif_name = _variant_name(name, size, "avif")
    webp_name = _variant_name(name, size, "webp")
    return _url_if_exists(avif_name), _url_if_exists(webp_name)

def _append_sources_for_breakpoint(parts, media_query: str, avif_url: Optional[str], webp_url: Optional[str]):
    if avif_url:
        parts.append(f'<source media="{media_query}" srcset="{avif_url}" type="image/avif">')
    if webp_url:
        parts.append(f'<source media="{media_query}" srcset="{webp_url}" type="image/webp">')


@register.simple_tag
def product_card_picture(product, classes: str = "tm-card-img", alt: Optional[str] = None,
                         loading: str = "lazy", fetchpriority: Optional[str] = None):
    """
    Render a <picture> for product card (bestsellers). Prefers product.card_image if provided,
    otherwise falls back to product.image. Uses size 230x160 for >=768px and 200x160 for default.
    """
    alt_attr = alt or getattr(product, "name", "")
    class_attr = classes or "tm-card-img"

    img_field = getattr(product, "card_image", None) or getattr(product, "image", None)
    if not img_field or not getattr(img_field, "name", ""):
        fallback = static("deps/images/placeholder.png")
        fp_attr = f" fetchpriority=\"{fetchpriority}\"" if fetchpriority else ""
        return mark_safe(
            f"<img src=\"{fallback}\" alt=\"{alt_attr}\" class=\"{class_attr}\" width=\"230\" height=\"160\" loading=\"{loading}\" decoding=\"async\"{fp_attr}>"
        )

    name = img_field.name
    # Desktop
    avif_230 = _url_if_exists(_variant_name(name, "230x160", "avif"))
    webp_230 = _url_if_exists(_variant_name(name, "230x160", "webp"))
    # Mobile/default
    avif_200 = _url_if_exists(_variant_name(name, "200x160", "avif"))
    webp_200 = _url_if_exists(_variant_name(name, "200x160", "webp"))

    parts = ["<picture>"]
    # >=768px first (will be ignored on smaller viewports)
    _append_sources_for_breakpoint(parts, "(min-width: 768px)", avif_230, webp_230)
    # default sources without media
    if avif_200:
        parts.append(f"<source srcset=\"{avif_200}\" type=\"image/avif\">")
    if webp_200:
        parts.append(f"<source srcset=\"{webp_200}\" type=\"image/webp\">")

    # Fallback img chooses best available mobile variant, else desktop, else original
    try:
        orig_url = img_field.url
    except Exception:
        orig_url = None
    img_src = webp_200 or avif_200 or webp_230 or avif_230 or orig_url or static("deps/images/placeholder.png")
    fp_attr = f" fetchpriority=\"{fetchpriority}\"" if fetchpriority else ""
    parts.append(
        f"<img src=\"{img_src}\" alt=\"{alt_attr}\" class=\"{class_attr}\" width=\"230\" height=\"160\" loading=\"{loading}\" decoding=\"async\"{fp_attr}>"
    )
    parts.append("</picture>")
    return mark_safe("".join(parts))


@register.simple_tag
def responsive_product_picture(product, classes: str = "", alt: Optional[str] = None,
                               width: int = 800, height: int = 600,
                               loading: str = "lazy", fetchpriority: Optional[str] = None):
    """
    Responsive <picture> for product main image with media breakpoints:
      - (min-width: 1200px): 1200x900
      - (min-width: 992px): 1024x768
      - (min-width: 768px): 800x600
      - default: 640x480
    """
    alt_attr = alt or getattr(product, "name", "")
    class_attr = classes or ""

    img_field = getattr(product, "image", None)
    if not img_field or not getattr(img_field, "name", ""):
        try:
            images = getattr(product, "images", None)
            if images and images.exists():
                img_field = images.first().image
        except Exception:
            pass

    if not img_field or not getattr(img_field, "name", ""):
        fallback = static("deps/images/placeholder.png")
        fp_attr = f" fetchpriority=\"{fetchpriority}\"" if fetchpriority else ""
        return mark_safe(
            f"<img src=\"{fallback}\" alt=\"{alt_attr}\" class=\"{class_attr}\" width=\"{width}\" height=\"{height}\" loading=\"{loading}\" decoding=\"async\"{fp_attr}>"
        )

    name = img_field.name
    orig = _orig_url_safe(img_field)

    parts = ["<picture>"]
    # Desktop XL
    avif, webp = _best_variant_urls(name, "1200x900")
    _append_sources_for_breakpoint(parts, "(min-width: 1200px)", avif, webp)
    # Desktop
    avif, webp = _best_variant_urls(name, "1024x768")
    _append_sources_for_breakpoint(parts, "(min-width: 992px)", avif, webp)
    # Tablet
    avif, webp = _best_variant_urls(name, "800x600")
    _append_sources_for_breakpoint(parts, "(min-width: 768px)", avif, webp)
    # Mobile default
    avif_m, webp_m = _best_variant_urls(name, "640x480")
    if avif_m:
        parts.append(f'<source srcset="{avif_m}" type="image/avif">')
    if webp_m:
        parts.append(f'<source srcset="{webp_m}" type="image/webp">')

    # Fallback img src preference, with extra root-level fallback (<root>.webp/.avif)
    img_src = webp_m or avif_m
    if not img_src:
        avif_s, webp_s = _best_variant_urls(name, "800x600")
        img_src = webp_s or avif_s
    if not img_src:
        # Try root-level variants without size suffix
        root, _ext = os.path.splitext(name)
        root_avif = _url_if_exists(f"{root}.avif")
        root_webp = _url_if_exists(f"{root}.webp")
        img_src = root_webp or root_avif or orig or static("deps/images/placeholder.png")

    fp_attr = f" fetchpriority=\"{fetchpriority}\"" if fetchpriority else ""
    parts.append(
        f"<img src=\"{img_src}\" alt=\"{alt_attr}\" class=\"{class_attr}\" width=\"{width}\" height=\"{height}\" loading=\"{loading}\" decoding=\"async\"{fp_attr}>"
    )
    parts.append("</picture>")
    return mark_safe("".join(parts))


@register.simple_tag
def category_best_img_src(category, size: str = "128x128") -> Optional[str]:
    """
    Return the best single URL to be used in <img src> for a category icon of given size.
    Priority: WebP -> AVIF -> original for media-based images; for static icons: WebP -> AVIF -> PNG.
    This is used for <link rel="preload" as="image"> to speed up LCP.
    """
    # 1) Media image attached to category
    img_field = getattr(category, "image", None)
    if img_field and getattr(img_field, "name", ""):
        try:
            orig_url = img_field.url
        except Exception:
            orig_url = None

        name = img_field.name
        avif_name = _variant_name(name, size, "avif")
        webp_name = _variant_name(name, size, "webp")
        webp_url = _url_if_exists(webp_name)
        avif_url = _url_if_exists(avif_name)
        # Prefer modern src for <img>
        return webp_url or avif_url or orig_url

    # 2) Static icon (by slug)
    slug = getattr(category, "slug", "")
    if slug:
        static_base = f"deps/icons/{slug}"
        # Sized first
        static_webp_sized = f"{static_base}_{size}.webp"
        static_avif_sized = f"{static_base}_{size}.avif"
        # Non-sized fallback
        static_webp = f"{static_base}.webp"
        static_avif = f"{static_base}.avif"
        static_png = f"{static_base}.png"

        # Prefer WebP -> AVIF -> PNG (for src attribute compatibility and weight)
        for path in (static_webp_sized, static_avif_sized, static_webp, static_avif, static_png):
            if finders.find(path):
                return static(path)

    return None


@register.simple_tag
def category_icon_picture(category, size: str = "128x128", classes: str = "", alt: Optional[str] = None,
                          width: int = 128, height: int = 128, loading: str = "lazy", fetchpriority: Optional[str] = None):
    """
    Render a <picture> for category.image with AVIF/WebP priority and fallback to original.
    Usage:
      {% category_icon_picture category '128x128' 'catalog-category-icon' category.name 128 128 %}
    """
    img_field = getattr(category, "image", None)
    alt_attr = alt or getattr(category, "name", "")
    class_attr = classes or ""

    # 1) Prefer media-based image from admin with our generated variants
    if img_field and getattr(img_field, "name", ""):
        orig_url = getattr(img_field, "url", None)
        if callable(orig_url):
            try:
                orig_url = img_field.url
            except Exception:
                orig_url = None

        name = img_field.name
        avif_name = _variant_name(name, size, "avif")
        webp_name = _variant_name(name, size, "webp")

        avif_url = _url_if_exists(avif_name)
        webp_url = _url_if_exists(webp_name)

        if getattr(settings, 'DEBUG', False):
            logger.debug("category_icon_picture: name=%s size=%s avif=%s webp=%s orig=%s", name, size, bool(avif_url), bool(webp_url), bool(orig_url))

        parts = ["<picture>"]
        if avif_url:
            parts.append(f"<source srcset=\"{avif_url}\" type=\"image/avif\">")
        if webp_url:
            parts.append(f"<source srcset=\"{webp_url}\" type=\"image/webp\">")
        # Prefer modern fallback in <img>: webp -> avif -> original
        if orig_url or webp_url or avif_url:
            img_src = webp_url or avif_url or orig_url
            fp_attr = f" fetchpriority=\"{fetchpriority}\"" if fetchpriority else ""
            parts.append(
                f"<img src=\"{img_src}\" alt=\"{alt_attr}\" class=\"{class_attr}\" width=\"{width}\" height=\"{height}\" loading=\"{loading}\" decoding=\"async\"{fp_attr}>"
            )
        parts.append("</picture>")
        return mark_safe("".join(parts))

    # 2) Fallback to static icon by slug (if exists)
    slug = getattr(category, "slug", "")
    if slug:
        static_base = f"deps/icons/{slug}"
        # Try with size suffix first (generated by generate_category_icons command)
        static_avif_sized = f"{static_base}_{size}.avif"
        static_webp_sized = f"{static_base}_{size}.webp"
        # Fallback to files without size suffix
        static_avif = f"{static_base}.avif"
        static_webp = f"{static_base}.webp"
        static_png = f"{static_base}.png"
        
        # Check for sized variants first, then fallback to non-sized
        has_avif = bool(finders.find(static_avif_sized)) or bool(finders.find(static_avif))
        has_webp = bool(finders.find(static_webp_sized)) or bool(finders.find(static_webp))
        has_png = bool(finders.find(static_png))
        
        # Use the actual found files
        final_avif = static_avif_sized if finders.find(static_avif_sized) else static_avif
        final_webp = static_webp_sized if finders.find(static_webp_sized) else static_webp
        if has_avif or has_webp or has_png:
            parts = ["<picture>"]
            if has_avif:
                parts.append(f"<source srcset=\"{ static(final_avif) }\" type=\"image/avif\">")
            if has_webp:
                parts.append(f"<source srcset=\"{ static(final_webp) }\" type=\"image/webp\">")
            fallback = static(static_png) if has_png else (static(final_webp) if has_webp else static(final_avif))
            fp_attr = f" fetchpriority=\"{fetchpriority}\"" if fetchpriority else ""
            parts.append(
                f"<img src=\"{fallback}\" alt=\"{alt_attr}\" class=\"{class_attr}\" width=\"{width}\" height=\"{height}\" loading=\"{loading}\" decoding=\"async\"{fp_attr}>"
            )
            parts.append("</picture>")
            return mark_safe("".join(parts))

    # 3) Ultimate placeholder
    fallback = static("deps/images/placeholder.png")
    fp_attr = f" fetchpriority=\"{fetchpriority}\"" if fetchpriority else ""
    return mark_safe(
        f"<img src=\"{fallback}\" alt=\"{alt_attr}\" class=\"{class_attr}\" width=\"{width}\" height=\"{height}\" loading=\"{loading}\" decoding=\"async\"{fp_attr}>"
    )


@register.simple_tag
def field_image_picture(image_field, size: str = "400x300", classes: str = "", alt: str = "",
                        width: int = 400, height: int = 300, loading: str = "lazy", fetchpriority: Optional[str] = None):
    """
    Render <picture> for arbitrary ImageField/FileField with AVIF/WebP priority and fallback.
    Usage:
      {% field_image_picture img.image '400x300' 'class' product.name 400 300 'lazy' %}
    """
    if not image_field or not getattr(image_field, "name", ""):
        fallback = static("deps/images/placeholder.png")
        fp_attr = f" fetchpriority=\"{fetchpriority}\"" if fetchpriority else ""
        return mark_safe(
            f"<img src=\"{fallback}\" alt=\"{alt}\" class=\"{classes}\" width=\"{width}\" height=\"{height}\" loading=\"{loading}\" decoding=\"async\"{fp_attr}>"
        )

    try:
        orig_url = image_field.url
    except Exception:
        orig_url = None

    name = image_field.name
    avif_name = _variant_name(name, size, "avif")
    webp_name = _variant_name(name, size, "webp")

    avif_url = _url_if_exists(avif_name)
    webp_url = _url_if_exists(webp_name)

    if getattr(settings, 'DEBUG', False):
        logger.debug("field_image_picture: name=%s size=%s avif=%s webp=%s orig=%s", name, size, bool(avif_url), bool(webp_url), bool(orig_url))

    parts = ["<picture>"]
    if avif_url:
        parts.append(f"<source srcset=\"{avif_url}\" type=\"image/avif\">")
    if webp_url:
        parts.append(f"<source srcset=\"{webp_url}\" type=\"image/webp\">")
    fp_attr = f" fetchpriority=\"{fetchpriority}\"" if fetchpriority else ""
    img_src = webp_url or avif_url or orig_url or static("deps/images/placeholder.png")
    parts.append(
        f"<img src=\"{img_src}\" alt=\"{alt}\" class=\"{classes}\" width=\"{width}\" height=\"{height}\" loading=\"{loading}\" decoding=\"async\"{fp_attr}>"
    )
    parts.append("</picture>")
    return mark_safe("".join(parts))


@register.simple_tag
def responsive_field_picture(image_field, classes: str = "", alt: str = "",
                              width: int = 800, height: int = 600,
                              loading: str = "lazy", fetchpriority: Optional[str] = None):
    """
    Responsive variant for arbitrary ImageField with the same breakpoints as responsive_product_picture.
    """
    if not image_field or not getattr(image_field, "name", ""):
        fallback = static("deps/images/placeholder.png")
        fp_attr = f" fetchpriority=\"{fetchpriority}\"" if fetchpriority else ""
        return mark_safe(
            f"<img src=\"{fallback}\" alt=\"{alt}\" class=\"{classes}\" width=\"{width}\" height=\"{height}\" loading=\"{loading}\" decoding=\"async\"{fp_attr}>"
        )

    name = image_field.name
    orig = _orig_url_safe(image_field)
    parts = ["<picture>"]
    avif, webp = _best_variant_urls(name, "1200x900"); _append_sources_for_breakpoint(parts, "(min-width: 1200px)", avif, webp)
    avif, webp = _best_variant_urls(name, "1024x768"); _append_sources_for_breakpoint(parts, "(min-width: 992px)", avif, webp)
    avif, webp = _best_variant_urls(name, "800x600");  _append_sources_for_breakpoint(parts, "(min-width: 768px)", avif, webp)
    avif_m, webp_m = _best_variant_urls(name, "640x480")
    if avif_m: parts.append(f'<source srcset="{avif_m}" type="image/avif">')
    if webp_m: parts.append(f'<source srcset="{webp_m}" type="image/webp">')

    # Fallback with root-level variants
    img_src = webp_m or avif_m
    if not img_src:
        avif_s, webp_s = _best_variant_urls(name, "800x600")
        img_src = webp_s or avif_s
    if not img_src:
        root, _ext = os.path.splitext(name)
        root_avif = _url_if_exists(f"{root}.avif")
        root_webp = _url_if_exists(f"{root}.webp")
        img_src = root_webp or root_avif or orig or static("deps/images/placeholder.png")
    fp_attr = f" fetchpriority=\"{fetchpriority}\"" if fetchpriority else ""
    parts.append(
        f"<img src=\"{img_src}\" alt=\"{alt}\" class=\"{classes}\" width=\"{width}\" height=\"{height}\" loading=\"{loading}\" decoding=\"async\"{fp_attr}>"
    )
    parts.append("</picture>")
    return mark_safe("".join(parts))
