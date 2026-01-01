from __future__ import annotations

import os
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.conf import settings

from goods.models import Categories
from common.image_utils import generate_icon_variants


def _fs_path(name: str) -> str:
    try:
        return default_storage.path(name)  # type: ignore[attr-defined]
    except Exception:
        return os.path.join(settings.MEDIA_ROOT, name)


class Command(BaseCommand):
    help = "Generate AVIF/WebP icon variants (128x128) for all categories that have an image."

    def add_arguments(self, parser):
        parser.add_argument("--size", default="128x128", help="Size WxH, default 128x128")
        parser.add_argument("--only-missing", action="store_true", help="Skip if both variants already exist")
        parser.add_argument("--mode", choices=["contain", "cover"], default="contain",
                            help="Resize mode: 'contain' fits inside without cropping, 'cover' crops to fill (default: contain)")
        parser.add_argument("--quality-avif", type=int, default=None,
                            help="AVIF quality (0..100). If omitted, defaults from image_utils are used.")
        parser.add_argument("--quality-webp", type=int, default=None,
                            help="WebP quality (0..100). If omitted, defaults from image_utils are used.")

    def handle(self, *args, **options):
        size_str: str = options["size"]
        try:
            w, h = [int(x) for x in size_str.lower().split("x", 1)]
        except Exception:
            self.stderr.write(self.style.ERROR(f"Invalid --size '{size_str}', expected WxH"))
            return 1

        total = 0
        ok = 0
        mode = options.get("mode", "contain")
        q_avif = options.get("quality_avif")
        q_webp = options.get("quality_webp")
        for cat in Categories.objects.all():
            img = getattr(cat, "image", None)
            if not img or not getattr(img, "name", ""):
                continue
            total += 1
            src = _fs_path(img.name)
            if options["only_missing"]:
                root, _ = os.path.splitext(src)
                avif = f"{root}_{size_str}.avif"
                webp = f"{root}_{size_str}.webp"
                if os.path.exists(avif) and os.path.exists(webp):
                    continue
            try:
                generate_icon_variants(src, size=(w, h), mode=mode,
                                       quality_avif=q_avif, quality_webp=q_webp)
                ok += 1
                self.stdout.write(self.style.SUCCESS(f"OK: {cat.name}"))
            except Exception as e:
                self.stderr.write(self.style.WARNING(f"Skip {cat.name}: {e}"))
        self.stdout.write(self.style.SUCCESS(f"Done. Processed={total}, generated={ok}"))
