from ninja_extra import NinjaExtraAPI
from accounts.api import GitHubAuthController
from telegram_bot.api import TelegramController

# Create API instance with unique identifier to avoid conflicts
api = NinjaExtraAPI(
    title="Web-Bot Core API", 
    version="1.0.0",
    urls_namespace="webbot_api"
)

# Register controllers only if not already registered
try:
    api.register_controllers(GitHubAuthController)
    api.register_controllers(TelegramController)
except Exception as e:
    # Controllers might already be registered during development server reload
    pass
