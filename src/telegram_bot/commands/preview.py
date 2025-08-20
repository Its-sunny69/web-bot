from telegram import Update
from telegram.ext import CallbackContext
from accounts.models import User
from django.conf import settings

def preview(update: Update, context: CallbackContext):
    telegram_id = update.effective_user.id
    try:
        user = User.objects.get(telegram_id=telegram_id)
        repo = user.selected_repo
        branch = user.current_branch
        if not repo or not branch:
            update.message.reply_text("No repository or branch selected. Use /select_repo and /select_branch first.")
            return

        # Construct preview URL (assuming repo.id is used in preview_embed)
        preview_url = f"{settings.SERVER_URL}/preview/embed/{repo.id}/"
        msg = (
            f"🔎 *Preview for your current selection:*\n"
            f"*Repository:* `{repo.name}`\n"
            f"*Branch:* `{branch}`\n"
            f"*Preview URL:* [Open Preview]({preview_url})"
        )
        update.message.reply_markdown(msg)
    except User.DoesNotExist:
        update.message.reply_text("User not found. Please login first.")