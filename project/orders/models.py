from uuid import uuid4

from django.db import models
from goods.models import Products

from users.models import User


class OrderitemQueryset(models.QuerySet):
    
    def total_price(self):
        return sum(cart.products_price() for cart in self)
    
    def total_quantity(self):
        if self:
            return sum(cart.quantity for cart in self)
        return 0

class Order(models.Model):
    user = models.ForeignKey(to=User, on_delete=models.SET_DEFAULT, blank=True, null=True, verbose_name="Пользователь", default=None)
    first_name = models.CharField(max_length=50, verbose_name="Имя")
    last_name = models.CharField(max_length=50, verbose_name="Фамилия")
    created_timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания заказа")
    phone_number = models.CharField(max_length=25, verbose_name="Номер телефона")
    email = models.EmailField(verbose_name="Email")
    requires_delivery = models.CharField(verbose_name="Вид почты")
    delivery_address = models.TextField(null=True, blank=True, verbose_name="Адрес доставки")
    payment_on_get = models.BooleanField(default=False, verbose_name="Оплата при получении")
    is_paid = models.BooleanField(default=False, verbose_name="Оплачено")
    status = models.CharField(max_length=50, default='В обработке', verbose_name="Статус заказа")
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)

    class Meta:
        db_table = "order"
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ("id",)

    def __str__(self):
        # Безопасное отображение покупателя, даже если user=None
        buyer = ""
        try:
            if self.user_id and self.user:
                buyer = (self.user.get_full_name() or self.user.username or "").strip()
        except Exception:
            buyer = ""
        if not buyer:
            buyer = f"{(self.first_name or '').strip()} {(self.last_name or '').strip()}".strip()
        if not buyer:
            buyer = (self.email or self.phone_number or "гость").strip()
        return f"Заказ № {self.pk} | Покупатель {buyer}"


class OrderItem(models.Model):
    order = models.ForeignKey(to=Order, on_delete=models.CASCADE, verbose_name="Заказ")
    product = models.ForeignKey(to=Products, on_delete=models.SET_DEFAULT, null=True, verbose_name="Продукт", default=None)
    name = models.CharField(max_length=150, verbose_name="Название")
    price = models.DecimalField(max_digits=7, decimal_places=2, verbose_name="Цена")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Количество")
    created_timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Дата продажи")
    # Сохранённый выбор подарка-отпечатка на момент оформления (может быть пустым)
    gift_choice = models.CharField(max_length=255, default='', blank=True, verbose_name='Подарок (отпечаток)')
    # Второй выбранный стрейн (для товаров типа Гроубокс)
    gift_choice_2 = models.CharField(max_length=255, default='', blank=True, verbose_name='Подарок 2 (отпечаток)')


    class Meta:
        db_table = "order_item"
        verbose_name = "Проданный товар"
        verbose_name_plural = "Проданные товары"
        ordering = ("id",)

    objects = OrderitemQueryset.as_manager()

    def products_price(self):
        return round(self.product.sell_price() * self.quantity, 2)

    def __str__(self):
        return f"Товар {self.name} | Заказ № {self.order.pk}"