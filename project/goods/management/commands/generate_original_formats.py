import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Q

from goods.models import Products, ProductImage
from common.image_utils import generate_formats_noresize


class Command(BaseCommand):
    help = (
        "Generate AVIF/WebP next to original product images WITHOUT resizing.\n"
        "Processes main product image, card_image, and gallery images by default.\n"
        "Writes <root>.avif and <root>.webp beside the original file."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-missing",
            action="store_true",
            help="Skip files that already have both .avif and .webp",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Force re-create .avif/.webp even if they already exist",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be done without writing files",
        )
        parser.add_argument(
            "--include-main",
            action="store_true",
            default=True,
            help="Include Products.image (default: true)",
        )
        parser.add_argument(
            "--include-card",
            action="store_true",
            default=True,
            help="Include Products.card_image (default: true)",
        )
        parser.add_argument(
            "--include-gallery",
            action="store_true",
            default=True,
            help="Include ProductImage.image (default: true)",
        )
        parser.add_argument(
            "--quality-avif",
            type=int,
            default=None,
            help="Explicit AVIF quality (0..100). If omitted, uses product preset.",
        )
        parser.add_argument(
            "--quality-webp",
            type=int,
            default=None,
            help="Explicit WebP quality (0..100). If omitted, uses sensible default.",
        )
        parser.add_argument(
            "--ids",
            type=str,
            default=None,
            help="Optional comma-separated product IDs to limit processing (e.g., '12,15,21')",
        )

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        overwrite = opts["overwrite"]
        only_missing = opts["only_missing"]
        inc_main = opts["include_main"]
        inc_card = opts["include_card"]
        inc_gallery = opts["include_gallery"]
        q_avif = opts.get("quality_avif")
        q_webp = opts.get("quality_webp")

        ids_raw = opts.get("ids")
        ids = None
        if ids_raw:
            try:
                ids = [int(x.strip()) for x in ids_raw.split(",") if x.strip().isdigit()]
            except Exception:
                ids = None

        # Query products
        qs = Products.objects.all()
        if ids:
            qs = qs.filter(id__in=ids)

        total_files = 0
        created_avif = 0
        created_webp = 0
        skipped = 0
        errors = 0

        def process_path(fs_path: str, origin_label: str):
            nonlocal total_files, created_avif, created_webp, skipped, errors
            if not fs_path or not os.path.exists(fs_path):
                return

            root, _ = os.path.splitext(fs_path)
            avif_path = f"{root}.avif"
            webp_path = f"{root}.webp"

            if only_missing and os.path.exists(avif_path) and os.path.exists(webp_path):
                skipped += 1
                self.stdout.write(f"⏩ Skip (exists): {origin_label} -> {os.path.basename(fs_path)}")
                return

            total_files += 1
            if dry:
                action = "OVERWRITE" if overwrite else ("ONLY-MISSING" if only_missing else "CREATE")
                self.stdout.write(
                    f"🔍 Would generate ({action}): {origin_label} -> {os.path.basename(fs_path)}"
                )
                return

            try:
                result = generate_formats_noresize(
                    fs_path,
                    image_type="product",
                    quality_avif=q_avif,
                    quality_webp=q_webp,
                    overwrite=overwrite,
                )
                if result.get("avif"):
                    created_avif += 1
                if result.get("webp"):
                    created_webp += 1
                self.stdout.write(
                    f"✅ Done: {origin_label} -> {os.path.basename(fs_path)}"
                )
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"❌ Error: {origin_label} -> {fs_path}: {e}"))

        # Iterate
        for p in qs.iterator():
            # main image
            if inc_main and getattr(p, "image", None) and getattr(p.image, "path", None):
                process_path(p.image.path, f"Product #{p.id} main")
            # card_image
            if inc_card and getattr(p, "card_image", None) and getattr(p.card_image, "path", None):
                process_path(p.card_image.path, f"Product #{p.id} card")

            # gallery images
            if inc_gallery:
                imgs = getattr(p, "images", None)
                if imgs is not None:
                    for gi in imgs.all().iterator():
                        if getattr(gi, "image", None) and getattr(gi.image, "path", None):
                            process_path(gi.image.path, f"Product #{p.id} gallery #{gi.id}")

        # Summary
        self.stdout.write("\n📊 Summary:")
        self.stdout.write(f"   Total encountered: {total_files}")
        self.stdout.write(f"   Created AVIF:      {created_avif}")
        self.stdout.write(f"   Created WebP:      {created_webp}")
        self.stdout.write(f"   Skipped existing:  {skipped}")
        if errors:
            self.stdout.write(self.style.ERROR(f"   Errors:            {errors}"))
        else:
            self.stdout.write("   Errors:            0")

        self.stdout.write("\n💡 Tips:")
        self.stdout.write("   • Use --only-missing for idempotent runs on large datasets")
        self.stdout.write("   • Use --ids '1,2,3' to limit to certain products for testing")
        self.stdout.write("   • Combine with --dry-run before real run")
