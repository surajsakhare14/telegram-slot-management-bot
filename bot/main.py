# bot/main.py

import os
from dotenv import load_dotenv

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.handlers import (
    start_handler,
    callback_handler,
    start_create_slot,
    create_slot_date,
    create_slot_start,
    create_slot_end,
    create_slot_capacity,
    create_slot_title,
    text_fallback_handler
)

from bot.states import (
    CREATE_SLOT_DATE,
    CREATE_SLOT_START,
    CREATE_SLOT_END,
    CREATE_SLOT_CAPACITY,
    CREATE_SLOT_TITLE,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not found in environment variables")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # -----------------------
    # Basic Commands
    # -----------------------
    app.add_handler(CommandHandler("start", start_handler))

    # -----------------------
    # Admin Create Slot Conversation
    # IMPORTANT: Must be added BEFORE generic CallbackQueryHandler
    # -----------------------
    create_slot_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_create_slot, pattern="^create_slot$")
        ],
        states={
            CREATE_SLOT_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_slot_date)
            ],
            CREATE_SLOT_START: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_slot_start)
            ],
            CREATE_SLOT_END: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_slot_end)
            ],
            CREATE_SLOT_CAPACITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_slot_capacity)
            ],
            CREATE_SLOT_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_slot_title)
            ],
        },
        fallbacks=[],
    )

    app.add_handler(create_slot_conv)

    # -----------------------
    # General Callback Handler
    # -----------------------
    app.add_handler(CallbackQueryHandler(callback_handler))

    # -----------------------
    # Fallback for unrecognized text messages
    # -----------------------
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_fallback_handler))
    
    print("🚀 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()