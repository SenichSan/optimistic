# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.core.mail import send_mail
# from django.db import transaction
# from .models import Order
#
#
#
# @receiver(post_save, sender=Order)
# def send_order_confirmation_to_seller(sender, instance, created, **kwargs):
#     if created:  # Отправляем письмо только при создании нового заказа
#         # Формируем список товаров
#         items = '\n'.join([f"{item.name} - Количество: {item.quantity}, Цена: {item.price}" for item in instance.orderitem_set.all()])
#         # Формируем содержимое письма
#         message = f"Новый заказ №{instance.id}\n\nТовары:\n{items}\n\nАдрес доставки:\n{instance.delivery_address.upper()}\n\nИмя клиента: {instance.first_name.upper()}\nФамилия клиента: {instance.last_name.upper()}\nНомер телефона клиента: {instance.phone_number}\nEmail клиента: {instance.user.email}"
#         subject = f"Новый заказ №{instance.id}"
#         from_email = 'shroomer0ua@gmail.com'  # Замените на ваш Gmail-адрес
#         recipient_list = ['shroomer0ua@gmail.com']  # Замените на ваш рабочий email
#
#         # Отправляем письмо
#         send_mail(subject, message, from_email, recipient_list, fail_silently=False)