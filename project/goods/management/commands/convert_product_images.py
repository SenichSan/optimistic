from __future__ import annotations

import os
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.conf import settings

from goods.models import Products, ProductImage
from common.image_utils import generate_icon_variants


def _fs_path(name: str) -> str:
    try:
        return default_storage.path(name)  # type: ignore[attr-defined]
    except Exception:
        return os.path.join(settings.MEDIA_ROOT, name)


class Command(BaseCommand):
    help = "Convert all product images to WebP/AVIF variants for better performance"

    def add_arguments(self, parser):
        parser.add_argument("--sizes", default="400x300,800x600", 
                          help="Comma-separated sizes like '400x300,800x600'")
        parser.add_argument("--only-missing", action="store_true", 
                          help="Skip if variants already exist")
        parser.add_argument("--dry-run", action="store_true", 
                          help="Show what would be converted without actually doing it")

    def handle(self, *args, **options):
        sizes_str: str = options["sizes"]
        dry_run: bool = options["dry_run"]
        only_missing: bool = options["only_missing"]
        
        # Parse sizes
        sizes = []
        for size_str in sizes_str.split(","):
            try:
                w, h = [int(x.strip()) for x in size_str.strip().split("x", 1)]
                sizes.append((w, h))
            except Exception:
                self.stderr.write(self.style.ERROR(f"Invalid size '{size_str}', expected WxH"))
                continue

        if not sizes:
            self.stderr.write(self.style.ERROR("No valid sizes provided"))
            return 1

        total_processed = 0
        total_converted = 0

        # Process main product images
        for product in Products.objects.all():
            if product.image and getattr(product.image, "name", ""):
                total_processed += 1
                if self._process_image(product.image, sizes, only_missing, dry_run):
                    total_converted += 1

        # Process additional product images
        for product_image in ProductImage.objects.all():
            if product_image.image and getattr(product_image.image, "name", ""):
                total_processed += 1
                if self._process_image(product_image.image, sizes, only_missing, dry_run):
                    total_converted += 1

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"DRY RUN: Would convert {total_converted} of {total_processed} images")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Converted {total_converted} of {total_processed} images")
            )

    def _process_image(self, image_field, sizes, only_missing, dry_run):
        """Process a single image field"""
        try:
            src_path = _fs_path(image_field.name)
            if not os.path.exists(src_path):
                return False

            converted_any = False
            for size in sizes:
                size_name = f"{size[0]}x{size[1]}"
                
                if only_missing:
                    # Check if variants already exist
                    root, _ = os.path.splitext(src_path)
                    avif_path = f"{root}_{size_name}.avif"
                    webp_path = f"{root}_{size_name}.webp"
                    if os.path.exists(avif_path) and os.path.exists(webp_path):
                        continue

                if dry_run:
                    self.stdout.write(f"Would convert: {image_field.name} → {size_name}")
                    converted_any = True
                else:
                    try:
                        variants = generate_icon_variants(src_path, size=size)
                        if variants:
                            self.stdout.write(
                                self.style.SUCCESS(f"✓ {image_field.name} → {size_name}")
                            )
                            converted_any = True
                    except Exception as e:
                        self.stderr.write(
                            self.style.WARNING(f"✗ {image_field.name}: {e}")
                        )

            return converted_any

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"Error processing {image_field.name}: {e}")
            )
            return False
