from telegram.ext import Application, CommandHandler
from .dispatcher import register_commands
from telegram_bot.commands.start import start_command
from telegram_bot.commands.login import login_command
from django.conf import settings


def build_bot():
    token = settings.TELEGRAM_BOT_TOKEN
    app = Application.builder().token(token).build()
    register_commands(app)
    return app


def run_bot():
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("login", login_command))
    application.run_polling()
