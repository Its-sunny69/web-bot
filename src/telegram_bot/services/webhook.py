import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from telegram import Update
from .bot import build_bot  # Your bot initialization

# Build the bot application (once)
app = build_bot()

@csrf_exempt
def handle_telegram_webhook(request):
    """
    Django view to handle Telegram webhook updates.
    Telegram will POST updates to this endpoint.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))  # Decode JSON
            update = Update.de_json(data, app.bot)          # Convert to Update object
            app.update_queue.put_nowait(update)             # Pass update to the bot's handlers
            return JsonResponse({"status": "ok"})
        except Exception as e:
            return JsonResponse({"status": "error", "error": str(e)}, status=500)

    return JsonResponse({"status": "invalid method"}, status=405)
