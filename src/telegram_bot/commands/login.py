from urllib.parse import urlencode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def login_command(update, context):
    telegram_user_id = update.effective_user.id
    params = urlencode({"tg_id": telegram_user_id})
    login_url = f"http://localhost:8000/api/auth/github/login?{params}"
   
    await update.message.reply_text(
         f"Copy and open this link in your browser:\n{login_url}"
    )
