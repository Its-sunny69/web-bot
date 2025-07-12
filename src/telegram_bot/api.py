from ninja_extra import api_controller, http_post
from django.http import HttpRequest
from .services.webhook import handle_telegram_webhook

@api_controller("/telegram", tags=["Telegram"])
class TelegramController:
    @http_post("/webhook")
    def webhook(self, request: HttpRequest):
        return handle_telegram_webhook(request)
