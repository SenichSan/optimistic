from __future__ import annotations

from urllib.parse import quote

from django import template
from django.conf import settings

register = template.Library()


def _cloud_name() -> str | None:
    return getattr(settings, 'CLOUDINARY_CLOUD_NAME', None)


def _best_product_img(product):
    # Prefer dedicated card image, then main image
    img = getattr(product, 'card_image', None) or getattr(product, 'image', None)
    if img and getattr(img, 'url', None):
        try:
            return img.url
        except Exception:
            return None
    return None


@register.simple_tag(takes_context=True)
def cloud_card_picture(context, product, classes: str = 'tm-card-img', alt: str | None = None,
                       loading: str = 'lazy'):
    """
    Render <picture> for product card via Cloudinary fetch:
      - Desktop (>=768px): 230x160, c_fill,g_auto
      - Mobile/default:    200x160, c_fill,g_auto
      - Auto format/quality: f_auto,q_auto
    Requires settings.CLOUDINARY_CLOUD_NAME and access to request to build absolute media URL.
    Falls back to original <img> if Cloudinary not configured.
    """
    cloud = _cloud_name()
    req = context.get('request')
    src_rel = _best_product_img(product)
    alt_attr = alt or getattr(product, 'name', '')

    if not cloud or not req or not src_rel:
        # Fallback to original URL
        src = src_rel or ''
        return template.mark_safe(f'<img src="{src}" alt="{alt_attr}" class="{classes}" width="230" height="160" loading="{loading}" decoding="async">')

    try:
        abs_url = req.build_absolute_uri(src_rel)
    except Exception:
        abs_url = src_rel

    enc = quote(abs_url, safe='')
    base = f"https://res.cloudinary.com/{cloud}/image/fetch/"

    # Build transformations
    desk = f"{base}f_auto,q_auto,w_230,h_160,c_fill,g_auto/{enc}"
    mob = f"{base}f_auto,q_auto,w_200,h_160,c_fill,g_auto/{enc}"

    parts = [
        '<picture>',
        f'<source media="(min-width: 768px)" srcset="{desk}">',
        f'<source srcset="{mob}">',
        f'<img src="{mob}" alt="{alt_attr}" class="{classes}" width="230" height="160" loading="{loading}" decoding="async">',
        '</picture>'
    ]
    return template.mark_safe('\n'.join(parts))
