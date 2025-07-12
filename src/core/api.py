from ninja_extra import NinjaExtraAPI
from accounts.api import GitHubController
from telegram_bot.api import TelegramController
api = NinjaExtraAPI(title="Web-Bot Core API", version="0.0.1")

api.register_controllers(GitHubController)
api.register_controllers(TelegramController)
