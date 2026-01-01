from django.core.management.base import BaseCommand
from django.db import transaction

from goods.models import Categories, Products


class Command(BaseCommand):
    help = (
        "Backfill RU fields (name_ru, short_description_ru, description_ru) for Categories and Products "
        "from the existing UA fields. Safe: updates only empty RU fields."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write changes, only show what would be updated",
        )
        parser.add_argument(
            "--only",
            choices=["categories", "products", "all"],
            default="all",
            help="Limit scope to categories, products, or all",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Batch size for bulk updates",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        scope: str = options["only"]
        batch_size: int = options["batch_size"]

        total_cats = total_prods = 0
        upd_cats = upd_prods = 0

        def backfill_categories():
            nonlocal total_cats, upd_cats
            qs = Categories.objects.all().only(
                "id", "name", "name_ru", "short_description", "short_description_ru", "description", "description_ru"
            )
            total_cats = qs.count()
            to_update = []
            for cat in qs.iterator(chunk_size=batch_size):
                changed = False
                if not cat.name_ru and cat.name:
                    cat.name_ru = cat.name
                    changed = True
                if not cat.short_description_ru and cat.short_description:
                    cat.short_description_ru = cat.short_description
                    changed = True
                if not cat.description_ru and cat.description:
                    cat.description_ru = cat.description
                    changed = True
                if changed:
                    upd_cats += 1
                    to_update.append(cat)
                    if len(to_update) >= batch_size and not dry_run:
                        Categories.objects.bulk_update(
                            to_update,
                            ["name_ru", "short_description_ru", "description_ru"],
                            batch_size=batch_size,
                        )
                        to_update.clear()
            if to_update and not dry_run:
                Categories.objects.bulk_update(
                    to_update, ["name_ru", "short_description_ru", "description_ru"], batch_size=batch_size
                )

        def backfill_products():
            nonlocal total_prods, upd_prods
            qs = Products.objects.all().only(
                "id", "name", "name_ru", "short_description", "short_description_ru", "description", "description_ru"
            )
            total_prods = qs.count()
            to_update = []
            for prod in qs.iterator(chunk_size=batch_size):
                changed = False
                if not prod.name_ru and prod.name:
                    prod.name_ru = prod.name
                    changed = True
                if not prod.short_description_ru and prod.short_description:
                    prod.short_description_ru = prod.short_description
                    changed = True
                if not prod.description_ru and prod.description:
                    prod.description_ru = prod.description
                    changed = True
                if changed:
                    upd_prods += 1
                    to_update.append(prod)
                    if len(to_update) >= batch_size and not dry_run:
                        Products.objects.bulk_update(
                            to_update,
                            ["name_ru", "short_description_ru", "description_ru"],
                            batch_size=batch_size,
                        )
                        to_update.clear()
            if to_update and not dry_run:
                Products.objects.bulk_update(
                    to_update, ["name_ru", "short_description_ru", "description_ru"], batch_size=batch_size
                )

        # Run inside a transaction for safety if not dry-run
        if dry_run:
            if scope in ("all", "categories"):
                backfill_categories()
            if scope in ("all", "products"):
                backfill_products()
        else:
            with transaction.atomic():
                if scope in ("all", "categories"):
                    backfill_categories()
                if scope in ("all", "products"):
                    backfill_products()

        self.stdout.write(self.style.SUCCESS("Backfill completed" + (" (dry-run)" if dry_run else "")))
        self.stdout.write(
            f"Categories: total={total_cats}, updated_missing_ru={upd_cats}; Products: total={total_prods}, updated_missing_ru={upd_prods}"
        )
