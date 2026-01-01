from django.db import models


class Review(models.Model):
    image = models.ImageField(upload_to='reviews/%Y/%m/', verbose_name='Изображение')
    alt_text = models.CharField(max_length=255, verbose_name='Alt текст')
    title = models.CharField(max_length=255, blank=True, verbose_name='Заголовок')
    caption = models.TextField(blank=True, verbose_name='Подпись')
    sort_order = models.PositiveIntegerField(default=0, db_index=True, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Активен')

    class Meta:
        db_table = 'review'
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ('sort_order', '-id')

    def __str__(self):
        return self.title or f'Review #{self.pk}'
