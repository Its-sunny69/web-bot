from ninja_extra import api_controller, http_post
from django.http import HttpRequest
from .services.webhook import handle_telegram_webhook

@api_controller("/telegram", tags=["Telegram"])
class TelegramController:
    @http_post("/webhook")
    async def webhook(self, request: HttpRequest,data):
        # Get the raw request body (Telegram update payload)
       
        return handle_telegram_webhook(data)
