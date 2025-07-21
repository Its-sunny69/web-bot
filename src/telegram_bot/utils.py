import logging
from .services.bot import build_bot
logger = logging.getLogger(__name__)
async def notify_user(tg_id: int, message: str):
    application = build_bot()
    await application.initialize()

    try:
        await application.bot.send_message(chat_id=tg_id, text=message)
    except Exception as e:
        logger.error(f"Failed to send Telegram message to {tg_id}: {str(e)}")
