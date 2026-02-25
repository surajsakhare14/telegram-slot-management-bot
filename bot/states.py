# bot/states.py

from telegram.ext import ConversationHandler

(
    CREATE_SLOT_DATE,
    CREATE_SLOT_START,
    CREATE_SLOT_END,
    CREATE_SLOT_CAPACITY,
    CREATE_SLOT_TITLE,
) = range(5)