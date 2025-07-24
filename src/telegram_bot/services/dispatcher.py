from telegram.ext import CommandHandler
from ..commands.start import start_command
from ..commands.login import login_command
from ..commands.logout import logout_command
from ..commands.list_repos import list_repos_command
def register_commands(app):
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("login", login_command))
    app.add_handler(CommandHandler("logout", logout_command))
    app.add_handler(CommandHandler("listrepos", list_repos_command))