"""
Management command to update Site domain for sitemap generation.
Run once after deployment: python manage.py update_site
"""
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = 'Updates the Site domain to grownica.com.ua for sitemap generation'

    def handle(self, *args, **options):
        try:
            site = Site.objects.get(id=1)
            site.domain = 'grownica.com.ua'
            site.name = 'Grownica'
            site.save()
            self.stdout.write(
                self.style.SUCCESS(f'✅ Successfully updated Site: {site.domain}')
            )
        except Site.DoesNotExist:
            # Create site if doesn't exist
            site = Site.objects.create(
                id=1,
                domain='grownica.com.ua',
                name='Grownica'
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Created Site: {site.domain}')
            )
