# orders/validators.py

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings


# Отправляет письмо продавцу о новом заказе
def send_order_email_to_seller(order, comment=None):
    items = order.orderitem_set.all()

    if not items.exists():
        return  # Не отправляем письмо, если товаров нет (на всякий случай)

    item_lines = '\n'.join([
        (
            f"{item.name} — Кол-во: {item.quantity}, Цена: {item.price * item.quantity}"
            + (f"; Стрейн: {item.gift_choice}" if getattr(item, 'gift_choice', '') else '')
        )
        for item in items
    ])
    order_price = sum(item.price * item.quantity for item in items)
    # Предпочитаем email, указанный при оформлении заказа; если пуст — берём из профиля пользователя (если есть)
    seller_contact_email = order.email or (order.user.email if getattr(order, 'user', None) else '')

    message = (
        f"Новый заказ №{order.id}\n\n"
        f"Товары:\n{item_lines}\n\n"
        f"Общая стоимость заказа: {order_price}\n\n"
        f"Адрес доставки:\n{order.delivery_address}\n\n"
        f"Имя клиента: {order.first_name.upper()}\n"
        f"Фамилия клиента: {order.last_name.upper()}\n"
        f"Телефон: {order.phone_number}\n"
        f"Email: {seller_contact_email}"
    )

    if comment:
        message += f"\n\nКомментарий к заказу:\n{comment}"

    send_mail(
        subject=f"Новый заказ №{order.id}",
        message=message,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'shroomer0ua@gmail.com'),
        recipient_list=[getattr(settings, 'SELLER_EMAIL', 'shroomer0ua@gmail.com')],
        fail_silently=False
    )

def send_order_email_to_customer(order):
    items = order.orderitem_set.all()

    if not items.exists():
        return  # Не отправляем письмо, если товаров нет (на всякий случай)

    item_lines = '\n'.join([
        (
            f"{item.name} — Кол-во: {item.quantity}, Цена: {item.price * item.quantity}"
            + (f"; Стрейн: {getattr(item, 'gift_choice', '')}" if getattr(item, 'gift_choice', '') else '')
        )
        for item in items
    ])
    order_price = sum(item.price * item.quantity for item in items)

    # Подготовим список для HTML-шаблона с суммой по строке
    email_items = [
        {
            'name': item.name,
            'quantity': item.quantity,
            'line_total': item.price * item.quantity,
            'gift_choice': getattr(item, 'gift_choice', ''),
        }
        for item in items
    ]

    message = (
        f"Новый заказ №{order.id}\n\n"
        f"Товары:\n{item_lines}\n\n"
        f"Общая стоимость заказа: {order_price}\n\n"
        f"Адрес доставки:\n{order.delivery_address}\n\n"
        f"Имя клиента: {order.first_name.upper()}\n"
        f"Фамилия клиента: {order.last_name.upper()}\n"
        f"Телефон: {order.phone_number}\n"
        f"Email: {order.email}"
    )

    html_message = render_to_string('order_confirmation_email.html', {
        'order': order,
        'items': items,            # оставим для совместимости, если где-то используется
        'email_items': email_items, # используем в шаблоне
        'total_price': order_price,
    })

    # Отправка письма с двумя форматами
    email = EmailMultiAlternatives(
        subject=f"Ваше замовлення №{order.id}",
        body=message,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'shroomer0ua@gmail.com'),
        to=[order.email],
    )
    email.attach_alternative(html_message, "text/html")
    email.send()