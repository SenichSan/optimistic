from django.apps import AppConfig


class GoodsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'goods'
    verbose_name = 'Товары'

    def ready(self):
        # Import signals to ensure post_save handlers are registered
        from . import signals  # noqa: F401
