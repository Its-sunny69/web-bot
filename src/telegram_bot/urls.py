from django.urls import path
from .services.webhook import handle_telegram_webhook


urlpatterns = [
    path('telegram-webhook/', handle_telegram_webhook, name='handle_telegram_webhook'),
]