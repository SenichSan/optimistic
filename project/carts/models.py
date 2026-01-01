from django.db import models
from django.db.models import Sum, F
from goods.models import Products
from users.models import User


class CartQuerySet(models.QuerySet):
    def with_products(self):
        return self.select_related('product')

    def total_quantity(self):
        return self.aggregate(total=Sum('quantity'))['total'] or 0

    def total_price(self):
        # считаем на питоне, т.к. sell_price() — метод модели
        return sum(item.product.sell_price() * item.quantity for item in self.with_products())

    def total_discount(self):
        # если у Products есть price_discount()/discount — учитываем, иначе можно убрать
        return sum(
            getattr(item.product, 'price_discount', lambda: 0)() * item.quantity
            for item in self.with_products()
        )


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Пользователь')
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    product = models.ForeignKey(Products, on_delete=models.CASCADE, verbose_name='Товар')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')
    created_timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    # Выбранный пользователем подарок-отпечаток (или строка "Рандом"). Пусто, если для товара выбор не включён
    gift_choice = models.CharField(max_length=255, default='', blank=True, verbose_name='Подарок (отпечаток)')
    # Второй выбранный стрейн (для товаров типа Гроубокс). Пусто для обычных товаров
    gift_choice_2 = models.CharField(max_length=255, default='', blank=True, verbose_name='Подарок 2 (отпечаток)')

    objects = CartQuerySet.as_manager()

    class Meta:
        db_table = 'cart'
        verbose_name = "Корзина"
        verbose_name_plural = "Корзина"
        ordering = ("id",)
        constraints = [
            # одна запись на user+product+gift_choice или на session_key+product+gift_choice
            models.UniqueConstraint(fields=['user', 'product', 'gift_choice', 'gift_choice_2'], name='uniq_user_product_gift2', condition=~models.Q(user=None)),
            models.UniqueConstraint(fields=['session_key', 'product', 'gift_choice', 'gift_choice_2'], name='uniq_session_product_gift2', condition=~models.Q(session_key=None)),
        ]

    def products_price(self):
        return round(self.product.sell_price() * self.quantity, 2)

    def product_discount(self):
        if hasattr(self.product, 'price_discount'):
            return round(self.product.price_discount() * self.quantity, 2)
        return 0

    def __str__(self):
        owner = self.user.username if self.user else "Аноним"
        return f'Корзина {owner} | {self.product.name} x{self.quantity}'
