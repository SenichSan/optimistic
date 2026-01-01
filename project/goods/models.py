from django.db import models
from django.urls import reverse
from tinymce.models import HTMLField
from PIL import Image, ImageOps
import os


class Categories(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name='Название')
    name_ru = models.CharField(max_length=150, unique=False, blank=True, null=True, verbose_name='Название (RU)')
    slug = models.SlugField(max_length=200, unique=True, blank=True, null=True, verbose_name='URL')
    meta_title = models.CharField(max_length=200, blank=True, null=True, verbose_name='Meta title')
    meta_title_ru = models.CharField(max_length=200, blank=True, null=True, verbose_name='Meta title (RU)')
    short_description = models.CharField(max_length=600, blank=True, null=True, verbose_name='Краткое описание')
    short_description_ru = models.CharField(max_length=600, blank=True, null=True, verbose_name='Краткое описание (RU)')
    meta_description = models.CharField(max_length=300, blank=True, null=True, verbose_name='Meta description')
    meta_description_ru = models.CharField(max_length=300, blank=True, null=True, verbose_name='Meta description (RU)')
    description = HTMLField(blank=True, null=True, verbose_name='Описание')
    description_ru = HTMLField(blank=True, null=True, verbose_name='Описание (RU)')
    image = models.ImageField(upload_to='categories_images', blank=True, null=True, verbose_name='Изображение')
    seo_image = models.ImageField(upload_to='categories_seo', blank=True, null=True, verbose_name='SEO-изображение')
    sort_order = models.PositiveIntegerField(default=100, db_index=True, verbose_name='Порядок')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')


    class Meta:
        db_table = 'category'
        verbose_name = 'Категорию'
        verbose_name_plural = 'Категории'
        ordering = ("sort_order", "id")

    def __str__(self):
        return self.name


class Products(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name='Название')
    name_ru = models.CharField(max_length=255, unique=False, blank=True, null=True, verbose_name='Название (RU)')
    slug = models.SlugField(max_length=200, unique=True, blank=True, null=True, verbose_name='URL')
    short_description = models.CharField(max_length=600, blank=True, null=True, verbose_name='Краткое описание')
    short_description_ru = models.CharField(max_length=600, blank=True, null=True, verbose_name='Краткое описание (RU)')
    description = HTMLField(blank=True, null=True, verbose_name='Описание')
    description_ru = HTMLField(blank=True, null=True, verbose_name='Описание (RU)')
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    # Отдельное изображение для карточки (бестселлеры/ленты)
    card_image = models.ImageField(upload_to="products/cards/", blank=True, null=True, verbose_name='Изображение для карточки')
    price = models.DecimalField(default=0.00, max_digits=7, decimal_places=2, verbose_name='Цена')
    discount = models.DecimalField(default=0.00, max_digits=4, decimal_places=2, verbose_name='Скидка в %')
    quantity = models.PositiveIntegerField(default=0, verbose_name='Количество')
    category = models.ForeignKey(to=Categories, on_delete=models.CASCADE, verbose_name='Категория')
    sort_order = models.PositiveIntegerField(default=100, db_index=True, verbose_name='Порядок')
    is_bestseller = models.BooleanField(default=False, verbose_name='Лидер продаж')
    is_benefit = models.BooleanField(default=False, verbose_name='Выгода')
    is_unique = models.BooleanField(default=False, db_index=True, verbose_name='Уникальное предложение')
    gift_enabled = models.BooleanField(default=False, verbose_name='Выбор стрейна')
    gift_double = models.BooleanField(default=False, verbose_name='Два стрейна')
    SPECIES_CHOICES = (
        ('cubensis', 'Cubensis'),
        ('panaeolus', 'Panaeolus'),
    )
    species = models.CharField(
        max_length=20,
        choices=SPECIES_CHOICES,
        blank=True,
        default='',
        verbose_name='Вид (species)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')



    class Meta:
        db_table = 'product'
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'
        ordering = ("sort_order", "-id")

    def __str__(self):
        return f'{self.name} Количество - {self.quantity}'

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={
            "category_slug": self.category.slug,
            "product_slug": self.slug
        })

    def display_id(self):
        return f"{self.id:05}"


    def sell_price(self):
        if self.discount:
            return round(self.price - self.price*self.discount/100, 2)
        
        return self.price

    def discount_price(self):
        if self.discount:
            return round(self.price * self.discount/100, 2)

        return 0

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Normalize orientation for primary and card images, if present
        try:
            if self.image and getattr(self.image, 'path', None):
                _normalize_image_file_inplace(self.image.path)
            if self.card_image and getattr(self.card_image, 'path', None):
                _normalize_image_file_inplace(self.card_image.path)
        except Exception:
            # Fail-safe: never block model save due to image processing
            pass

class ProductImage(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=255, blank=True)

def _normalize_image_file_inplace(path: str) -> None:
    """Open an image by path, auto-fix EXIF orientation, and resave in-place.
    Keeps original format; for JPEG ensures RGB and uses sane save params.
    """
    if not path or not os.path.exists(path):
        return
    try:
        with Image.open(path) as img:
            # Auto-rotate according to EXIF and drop the orientation metadata
            fixed = ImageOps.exif_transpose(img)
            fmt = (fixed.format or img.format or '').upper()
            ext = os.path.splitext(path)[1].lower()

            save_kwargs = {}
            if fmt == 'JPEG' or ext in ('.jpg', '.jpeg'):
                if fixed.mode in ('RGBA', 'P'):
                    fixed = fixed.convert('RGB')
                save_kwargs.update(dict(format='JPEG', quality=85, optimize=True, progressive=True))
            elif fmt == 'PNG' or ext == '.png':
                save_kwargs.update(dict(format='PNG', optimize=True))
            else:
                # Default: keep format if known, else PNG
                if fixed.mode == 'RGBA' and ext in ('.jpg', '.jpeg'):
                    fixed = fixed.convert('RGB')
                save_kwargs.update(dict(format=fmt or 'PNG'))

            fixed.save(path, **save_kwargs)
    except Exception:
        # Silently ignore processing failures
        return