import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))
BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and ADMIN_CHAT_ID:
        await context.bot.forward_message(
            chat_id=ADMIN_CHAT_ID,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id,
        )


def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set")
    if not ADMIN_CHAT_ID:
        raise ValueError("ADMIN_CHAT_ID environment variable not set")

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, forward_to_admin))
    application.run_polling()


if __name__ == "__main__":
    main()
