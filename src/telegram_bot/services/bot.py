from telegram.ext import Application
from .dispatcher import register_commands
from django.conf import settings
def build_bot():
    from decouple import config
    token = settings.TELEGRAM_BOT_TOKEN
    app = Application.builder().token(token).build()
    register_commands(app)
    
    return app
