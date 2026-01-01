from django.db import models
from django.conf import settings
from django.urls import reverse
from tinymce.models import HTMLField
from django.utils import timezone, translation


class ArticleCategory(models.Model):
    name_uk = models.CharField("Назва (укр)", max_length=200)
    name_ru = models.CharField("Название (рус)", max_length=200, blank=True, default="")
    slug = models.SlugField(unique=True, db_index=True)
    description_uk = models.TextField("Опис (укр)", blank=True, default="")
    description_ru = models.TextField("Описание (рус)", blank=True, default="")

    class Meta:
        verbose_name = "Категория статьи"
        verbose_name_plural = "Категории статей"
        ordering = ("name_uk",)

    def __str__(self):
        return self.name_uk or self.name_ru or self.slug

    def get_absolute_url(self):
        return reverse('articles:category', kwargs={'slug': self.slug})

    # i18n helpers
    def _pick(self, base: str, lang: str | None = None) -> str:
        lang = (lang or translation.get_language() or 'uk')[:2]
        if lang == 'ru':
            return getattr(self, f"{base}_ru") or getattr(self, f"{base}_uk")
        return getattr(self, f"{base}_uk") or getattr(self, f"{base}_ru")

    def title(self, lang: str | None = None) -> str:
        return self._pick('name', lang)
    def description(self, lang: str | None = None) -> str:
        return self._pick('description', lang)


class ArticleQuerySet(models.QuerySet):
    def published(self):
        now = timezone.now()
        return self.filter(status=Article.Status.PUBLISHED, published_at__lte=now)


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'

    title_uk = models.CharField("Заголовок (укр)", max_length=255)
    title_ru = models.CharField("Заголовок (рус)", max_length=255, blank=True, default="")

    slug = models.SlugField(unique=True, db_index=True, help_text="URL без дат: /articles/<slug>/")

    excerpt_uk = models.CharField("Краткое описание (укр)", max_length=300, blank=True, default="")
    excerpt_ru = models.CharField("Краткое описание (рус)", max_length=300, blank=True, default="")

    body_uk = HTMLField("Текст (укр)")
    body_ru = HTMLField("Текст (рус)", blank=True, default="")

    cover_image = models.ImageField("Обложка", upload_to="articles/covers/")
    cover_caption_uk = models.CharField("Подпись к обложке (укр)", max_length=300, blank=True, default="")
    cover_caption_ru = models.CharField("Подпись к обложке (рус)", max_length=300, blank=True, default="")

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    published_at = models.DateTimeField("Дата публикации", db_index=True, default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    categories = models.ManyToManyField(ArticleCategory, related_name='articles', blank=True)

    # SEO (по языкам)
    meta_title_uk = models.CharField(max_length=255, blank=True, default="")
    meta_title_ru = models.CharField(max_length=255, blank=True, default="")
    meta_description_uk = models.CharField(max_length=300, blank=True, default="")
    meta_description_ru = models.CharField(max_length=300, blank=True, default="")

    objects = ArticleQuerySet.as_manager()

    class Meta:
        verbose_name = "Статья"
        verbose_name_plural = "Статьи"
        ordering = ("-published_at", "-id")
        indexes = [
            models.Index(fields=["status", "published_at"]),
        ]

    def __str__(self):
        return self.title_uk or self.title_ru or self.slug

    def get_absolute_url(self):
        return reverse('articles:detail', kwargs={'slug': self.slug})

    # i18n helpers
    def _pick(self, base: str, lang: str | None = None) -> str:
        lang = (lang or translation.get_language() or 'uk')[:2]
        if lang == 'ru':
            return getattr(self, f"{base}_ru") or getattr(self, f"{base}_uk")
        return getattr(self, f"{base}_uk") or getattr(self, f"{base}_ru")

    def title(self, lang: str | None = None) -> str:
        return self._pick('title', lang)
    def excerpt(self, lang: str | None = None) -> str:
        return self._pick('excerpt', lang)
    def body(self, lang: str | None = None) -> str:
        return self._pick('body', lang)
    def meta_title(self, lang: str | None = None) -> str:
        return self._pick('meta_title', lang)
    def meta_description(self, lang: str | None = None) -> str:
        return self._pick('meta_description', lang)
    def cover_caption(self, lang: str | None = None) -> str:
        return self._pick('cover_caption', lang)
