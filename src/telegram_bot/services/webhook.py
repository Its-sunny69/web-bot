import json
from telegram import Update
from .bot import build_bot

app = build_bot()

def handle_telegram_webhook(request):
    data = json.loads(request.body)
    update = Update.de_json(data, app.bot)
    app.update_queue.put_nowait(update)
    return {"status": "ok"}
