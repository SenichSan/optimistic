from __future__ import annotations

import os
from typing import Iterable, Tuple

from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage

from goods.models import Categories, Products, ProductImage


def _variant_name(orig_name: str, size: str, ext: str) -> str:
    root, _ext = os.path.splitext(orig_name)
    return f"{root}_{size}.{ext}"


def _exists(path: str) -> bool:
    try:
        return default_storage.exists(path)
    except Exception:
        return False


class Command(BaseCommand):
    help = "Check presence of AVIF/WebP generated variants for categories and products."

    def add_arguments(self, parser):
        parser.add_argument("--sizes", default="400x300,800x600,256x192,800x450",
                            help="Comma-separated sizes to check (WxH)")
        parser.add_argument("--only-missing", action="store_true",
                            help="Print only items missing any variant")

    def handle(self, *args, **options):
        sizes_str: str = options["sizes"]
        only_missing: bool = options.get("only_missing", False)
        sizes: Tuple[str, ...] = tuple(s.strip() for s in sizes_str.split(",") if s.strip())

        self.stdout.write(self.style.WARNING("Checking category images..."))
        cat_total = 0
        cat_missing = 0
        for cat in Categories.objects.all():
            img = getattr(cat, "image", None)
            if not img or not getattr(img, "name", ""):
                continue
            cat_total += 1
            missing_for_cat = []
            for size in sizes:
                avif = _variant_name(img.name, size, "avif")
                webp = _variant_name(img.name, size, "webp")
                ok_avif = _exists(avif)
                ok_webp = _exists(webp)
                if not (ok_avif or ok_webp):
                    missing_for_cat.append(size)
            if missing_for_cat:
                cat_missing += 1
                self.stdout.write(f"[CATEGORY] {cat.slug or cat.id} ({cat.name}): missing {', '.join(missing_for_cat)}")

        self.stdout.write(self.style.WARNING("Checking product images..."))
        prod_total = 0
        prod_missing = 0
        # main images
        for p in Products.objects.all():
            img = getattr(p, "image", None)
            if not img or not getattr(img, "name", ""):
                continue
            prod_total += 1
            missing_for_prod = []
            for size in sizes:
                avif = _variant_name(img.name, size, "avif")
                webp = _variant_name(img.name, size, "webp")
                if not (_exists(avif) or _exists(webp)):
                    missing_for_prod.append(size)
            if missing_for_prod:
                prod_missing += 1
                self.stdout.write(f"[PRODUCT] {p.id} {p.name}: missing {', '.join(missing_for_prod)}")

        # additional images
        for pi in ProductImage.objects.all():
            img = getattr(pi, "image", None)
            if not img or not getattr(img, "name", ""):
                continue
            prod_total += 1
            missing_for_prod = []
            for size in sizes:
                avif = _variant_name(img.name, size, "avif")
                webp = _variant_name(img.name, size, "webp")
                if not (_exists(avif) or _exists(webp)):
                    missing_for_prod.append(size)
            if missing_for_prod:
                prod_missing += 1
                self.stdout.write(f"[PRODUCT-IMG] {pi.id} of {pi.product_id}: missing {', '.join(missing_for_prod)}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Categories: total={cat_total}, missing_any={cat_missing}"))
        self.stdout.write(self.style.SUCCESS(f"Products: total_images={prod_total}, missing_any={prod_missing}"))
        self.stdout.write(self.style.NOTICE("Tip: run 'python manage.py generate_category_icons --size 800x450' and 'python manage.py convert_product_images --sizes 400x300,800x600,256x192'"))
