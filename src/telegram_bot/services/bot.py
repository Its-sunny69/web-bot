from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from ..commands.start import start_command
from django.conf import settings
def build_bot():
    from decouple import config
    token = settings.TELEGRAM_BOT_TOKEN

    app = Application.builder().token(token).build()

    async def start(update: Update, context):
        await start_command(update, context)
    app.add_handler(CommandHandler("start", start))
    return app
