import json
import traceback
from telegram import Update
from .bot import build_bot

# Build bot once globally
bot_app = build_bot()
bot_initialized = False
async def handle_telegram_webhook(request_body):
    """
    Processes the raw request body from Telegram.
    Returns a dict response.
    """
    global bot_initialized
    try:
        print(request_body)
        # Parse raw body (bytes -> dict)
        data = json.loads(request_body.decode('utf-8'))
        print("Incoming update:", data)  # Log the raw update to Vercel logs

        # Convert JSON to Telegram Update object
        update = Update.de_json(data, bot_app.bot)

        # Push update to python-telegram-bot async queue
        if not bot_initialized:
            await bot_app.initialize()
            await bot_app.start()
            bot_initialized = True

        # Process the update
        await bot_app.process_update(update)

        return {"status": "ok"}

    except Exception as e:
        # Log full traceback for debugging in Vercel
        print("Error processing Telegram update:", e)
        print("Traceback:", traceback.format_exc())
        return {"status": "error", "error": str(e)}
