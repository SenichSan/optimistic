from django.db import migrations, models
import uuid

def fill_uuid(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    for o in Order.objects.all():
        if not getattr(o, 'uuid', None):
            o.uuid = uuid.uuid4()
            o.save(update_fields=['uuid'])

class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='uuid',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(fill_uuid, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='order',
            name='uuid',
            field=models.UUIDField(null=False, unique=True, editable=False),
        ),
    ]