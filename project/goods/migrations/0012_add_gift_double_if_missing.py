from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('goods', '0011_categories_description_ru_categories_name_ru_and_more'),
    ]
    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE "product" ADD COLUMN IF NOT EXISTS "gift_double" boolean NOT NULL DEFAULT false;',
            reverse_sql='ALTER TABLE "product" DROP COLUMN IF EXISTS "gift_double";'
        ),
    ]