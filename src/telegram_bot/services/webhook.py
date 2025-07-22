import json
import traceback
from telegram import Update
from .bot import build_bot

# Build bot once globally
bot_app = build_bot()

def handle_telegram_webhook(request_body: bytes):
    """
    Processes the raw request body from Telegram.
    Returns a dict response.
    """
    try:
        # Parse raw body (bytes -> dict)
        data = json.loads(request_body.decode('utf-8'))
        print("Incoming update:", data)  # Log the raw update to Vercel logs

        # Convert JSON to Telegram Update object
        update = Update.de_json(data, bot_app.bot)

        # Push update to python-telegram-bot async queue
        bot_app.update_queue.put_nowait(update)

        return {"status": "ok"}

    except Exception as e:
        # Log full traceback for debugging in Vercel
        print("Error processing Telegram update:", e)
        print("Traceback:", traceback.format_exc())
        return {"status": "error", "error": str(e)}
