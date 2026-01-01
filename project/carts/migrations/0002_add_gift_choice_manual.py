# Generated manually to ensure gift_choice column exists in DB
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('carts', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=r'''
            DO $$
            BEGIN
                -- Add column if missing
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='cart' AND column_name='gift_choice'
                ) THEN
                    ALTER TABLE "cart" ADD COLUMN "gift_choice" varchar(255);
                END IF;

                -- Backfill NULLs to empty string
                UPDATE "cart" SET "gift_choice" = '' WHERE "gift_choice" IS NULL;

                -- Ensure default and not null
                ALTER TABLE "cart" ALTER COLUMN "gift_choice" SET DEFAULT '';
                ALTER TABLE "cart" ALTER COLUMN "gift_choice" SET NOT NULL;
            END$$;
            ''',
            reverse_sql=r'''
            -- No-op on reverse; keep the column
            ''',
        ),
    ]
