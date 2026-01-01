from __future__ import annotations

import glob
import os
from typing import Iterable, Tuple

from django.core.management.base import BaseCommand, CommandParser
from django.conf import settings
from PIL import Image

from common.image_utils import ensure_dir, _fit_box, save_avif, save_webp


class Command(BaseCommand):
    help = "Generate AVIF/WebP icon variants for static images (multiple sizes)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--glob",
            required=True,
            help="Glob pattern relative to project root or absolute path. Example: static/deps/images/{telegram,viber,whatsapp}.png",
        )
        parser.add_argument(
            "--sizes",
            required=True,
            help="Comma-separated sizes WxH. Example: 48x48,96x96",
        )
        parser.add_argument(
            "--quality-avif",
            type=int,
            default=70,
            help="AVIF quality (0..100), default 70 (high).",
        )
        parser.add_argument(
            "--quality-webp",
            type=int,
            default=82,
            help="WebP quality (0..100), default 82 (high).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate even if target files exist.",
        )

    def handle(self, *args, **options):
        pattern: str = options["glob"]
        sizes_raw: str = options["sizes"]
        q_avif: int = options["quality_avif"]
        q_webp: int = options["quality_webp"]
        force: bool = options["force"]

        sizes: list[Tuple[int, int]] = []
        for token in sizes_raw.split(","):
            token = token.strip().lower()
            if not token:
                continue
            try:
                w, h = [int(x) for x in token.split("x", 1)]
                sizes.append((w, h))
            except Exception:
                raise SystemExit(self.style.ERROR(f"Invalid size token '{token}', expected WxH"))
        if not sizes:
            raise SystemExit(self.style.ERROR("No valid sizes provided"))

        # Resolve search root
        root = settings.BASE_DIR
        globs: Iterable[str] = []
        if os.path.isabs(pattern):
            globs = [pattern]
        else:
            globs = [os.path.join(root, pattern)]

        files: list[str] = []
        for g in globs:
            files.extend(glob.glob(g, recursive=True))
        if not files:
            self.stdout.write(self.style.WARNING(f"No files matched: {pattern}"))
            return

        processed = 0
        for src in files:
            try:
                if not os.path.isfile(src):
                    continue
                with Image.open(src) as img:
                    img.load()
                    for (w, h) in sizes:
                        fitted = _fit_box(img, (w, h))
                        base, _ext = os.path.splitext(src)
                        avif_path = f"{base}_{w}x{h}.avif"
                        webp_path = f"{base}_{w}x{h}.webp"
                        if not force and os.path.exists(avif_path) and os.path.exists(webp_path):
                            self.stdout.write(f"Skip existing: {os.path.basename(src)} -> {w}x{h}")
                            continue
                        ensure_dir(avif_path)
                        save_avif(fitted, avif_path, quality=q_avif)
                        save_webp(fitted, webp_path, quality=q_webp)
                        self.stdout.write(self.style.SUCCESS(
                            f"OK {os.path.basename(src)} -> {w}x{h} (AVIF q={q_avif}, WebP q={q_webp})"
                        ))
                        processed += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error {src}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Generated {processed} variants."))
