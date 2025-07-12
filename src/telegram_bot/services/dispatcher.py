from telegram_bot.services.dispatcher import CommandHandler
from ..commands.start import start_command

def register_commands(app):
    app.add_handler(CommandHandler("start", start_command))