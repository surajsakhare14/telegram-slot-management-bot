# bot/keyboards.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(is_admin: bool):
    buttons = [
        [InlineKeyboardButton("📅 Book Slot", callback_data="book_slot")],
        [InlineKeyboardButton("📋 My Bookings", callback_data="my_bookings")],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
    ]

    if is_admin:
        buttons.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="admin_panel")])

    return InlineKeyboardMarkup(buttons)


def admin_menu_keyboard():
    buttons = [
        [InlineKeyboardButton("➕ Create Slot", callback_data="create_slot")],
        [InlineKeyboardButton("📊 List Slots", callback_data="list_slots")],
        [InlineKeyboardButton("📤 Export Bookings", callback_data="export_bookings")],
    ]
    return InlineKeyboardMarkup(buttons)