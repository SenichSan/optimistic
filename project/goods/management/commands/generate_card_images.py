from __future__ import annotations

import os
from typing import Tuple

from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.conf import settings

from goods.models import Products
from common.image_utils import generate_card_variants


def _fs_path(name: str) -> str:
    try:
        return default_storage.path(name)  # type: ignore[attr-defined]
    except Exception:
        return os.path.join(settings.MEDIA_ROOT, name)


class Command(BaseCommand):
    help = "Generate AVIF/WebP card variants (blur-extend) for product card images (230x160, 200x160).\n" \
           "Prefers Products.card_image, falls back to Products.image."

    def add_arguments(self, parser):
        parser.add_argument("--only-missing", action="store_true",
                            help="Skip products where both sizes already have AVIF/WebP")
        parser.add_argument("--force", action="store_true",
                            help="Regenerate even if variants exist")
        parser.add_argument("--webp-quality", type=int, default=82,
                            help="WebP quality (default: 82)")
        parser.add_argument("--avif-quality", type=int, default=60,
                            help="AVIF quality (default: 60)")
        parser.add_argument("--desktop", type=str, default="230x160",
                            help="Desktop canvas WxH (default: 230x160)")
        parser.add_argument("--mobile", type=str, default="200x160",
                            help="Mobile canvas WxH (default: 200x160)")

    def handle(self, *args, **options):
        only_missing: bool = options["only_missing"]
        force: bool = options["force"]
        webp_q: int = options["webp_quality"]
        avif_q: int = options["avif_quality"]
        size_d = self._parse_size(options["desktop"], (230, 160))
        size_m = self._parse_size(options["mobile"], (200, 160))

        total = 0
        converted = 0

        for p in Products.objects.all():
            img_field = getattr(p, "card_image", None) or getattr(p, "image", None)
            if not img_field or not getattr(img_field, "name", ""):
                continue
            src_path = _fs_path(img_field.name)
            if not os.path.exists(src_path):
                continue

            total += 1

            if only_missing and not force:
                # check if both sizes have at least one of avif/webp
                if self._has_variants(src_path, size_d) and self._has_variants(src_path, size_m):
                    continue

            try:
                generate_card_variants(
                    src_path,
                    size_desktop=size_d,
                    size_mobile=size_m,
                    background_blur=True,
                    quality_webp=webp_q,
                    quality_avif=avif_q,
                )
                converted += 1
                self.stdout.write(self.style.SUCCESS(f"✓ {img_field.name} → card variants"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"✗ {img_field.name}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Done: converted {converted}/{total} products"))

    def _parse_size(self, s: str, default: Tuple[int, int]) -> Tuple[int, int]:
        try:
            w, h = [int(x.strip()) for x in s.split("x", 1)]
            return (w, h)
        except Exception:
            return default

    def _has_variants(self, src_path: str, size: Tuple[int, int]) -> bool:
        root, _ = os.path.splitext(src_path)
        size_name = f"{size[0]}x{size[1]}"
        avif_path = f"{root}_{size_name}.avif"
        webp_path = f"{root}_{size_name}.webp"
        return os.path.exists(avif_path) or os.path.exists(webp_path)
