# bot/handlers.py

import os
import io
import csv
from datetime import date, timedelta, datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes, ConversationHandler

from db.session import SessionLocal
from services.slot_service import list_slots_by_date, create_slot, get_all_upcoming_slots, get_slot_with_bookings, cancel_slot
from services.booking_service import (
    book_slot,
    SlotFull,
    AlreadyBooked,
    SlotInPast,
    get_user_bookings,
    cancel_booking,
    get_all_confirmed_bookings
)

from bot.states import (
    CREATE_SLOT_DATE,
    CREATE_SLOT_START,
    CREATE_SLOT_END,
    CREATE_SLOT_CAPACITY,
    CREATE_SLOT_TITLE,
)

# ==============================
# Admin Configuration
# ==============================

ADMIN_IDS = set(
    int(x) for x in os.getenv("ADMIN_TELEGRAM_IDS", "").split(",") if x
)

# ==============================
# Start Command
# ==============================

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS

    buttons = [
        [InlineKeyboardButton("📅 Book Slot", callback_data="book_slot")],
        [InlineKeyboardButton("📋 My Bookings", callback_data="my_bookings")],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
    ]

    if is_admin:
        buttons.append(
            [InlineKeyboardButton("🛠 Admin Panel", callback_data="admin_panel")]
        )

    await update.message.reply_text(
        "Welcome to Slot Booking Bot!",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ==============================
# Callback Handler
# ==============================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id
    user_name = query.from_user.first_name

    # BOOK SLOT - DATE
    if data == "book_slot":
        today = date.today()
        buttons = []

        for i in range(7):
            d = today + timedelta(days=i)
            buttons.append([
                InlineKeyboardButton(
                    d.strftime("%Y-%m-%d"),
                    callback_data=f"select_date:{d.isoformat()}"
                )
            ])

        await query.edit_message_text(
            "Select a date:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # BOOK SLOT - LIST SLOTS
    elif data.startswith("select_date:"):

        selected_date = data.split(":")[1]
        selected_date_obj = date.fromisoformat(selected_date)

        db = SessionLocal()

        try:
            slots = list_slots_by_date(db, selected_date_obj)

            if not slots:
                await query.edit_message_text(
                    "No available slots for this date."
                )
                return

            buttons = []

            for slot in slots:

                # Count confirmed bookings
                confirmed = [
                    b for b in slot.bookings
                    if b.status.name == "CONFIRMED"
                ]

                remaining = slot.capacity - len(confirmed)

                # Skip fully booked slots
                if remaining <= 0:
                    continue

                # Optional title display
                title_part = f"[{slot.title}] " if slot.title else ""

                buttons.append([
                    InlineKeyboardButton(
                        f"{title_part} | {slot.start_time} - {slot.end_time} | {remaining} left",
                        callback_data=f"book_confirm:{slot.id}"
                    )
                ])

            if not buttons:
                await query.edit_message_text(
                    "All slots for this date are fully booked."
                )
                return

            await query.edit_message_text(
                "Select a slot:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        finally:
            db.close()

    # BOOK SLOT - CONFIRM
    elif data.startswith("book_confirm:"):
        slot_id = int(data.split(":")[1])
        db = SessionLocal()

        try:
            book_slot(
                db=db,
                slot_id=slot_id,
                telegram_user_id=user_id,
                name=user_name
            )
            await context.bot.send_message(chat_id=user_id, text="✅ Booking confirmed!")
        except SlotFull:
            await context.bot.send_message(chat_id=user_id, text="❌ Slot is sold out.")
        except AlreadyBooked:
            await context.bot.send_message(chat_id=user_id, text="⚠ You already booked this slot.")
        except SlotInPast:
            await context.bot.send_message(chat_id=user_id, text="❌ Cannot book a past slot.")
        finally:
            db.close()

    # MY BOOKINGS
    elif data == "my_bookings":
        db = SessionLocal()
        try:
            bookings = get_user_bookings(db, user_id)

            if not bookings:
                await query.edit_message_text("You have no bookings.")
                return

            buttons = []
            message = "Your Bookings:\n\n"

            for b in bookings:
                message += (
                    f"📅 {b.slot.date} | "
                    f"{b.slot.start_time}-{b.slot.end_time}\n"
                )

                buttons.append([
                    InlineKeyboardButton(
                        "❌ Cancel",
                        callback_data=f"cancel_booking:{b.id}"
                    )
                ])

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        finally:
            db.close()

    # CANCEL BOOKING
    elif data.startswith("cancel_booking:"):
        booking_id = int(data.split(":")[1])
        db = SessionLocal()

        try:
            cancel_booking(db, booking_id)
            await context.bot.send_message(chat_id=user_id, text="❌ Booking cancelled.")
        finally:
            db.close()

    # HELP
    elif data == "help":
        help_text = (
            "📌 *How to Use This Bot:*\n\n"
            "1️⃣ Click 'Book Slot' to see available dates and times.\n"
            "2️⃣ Select a date, then choose a slot to book.\n"
            "3️⃣ View your bookings under 'My Bookings' and cancel if needed.\n\n"
            "⚠️ *Admin Panel:*\n"
            "- Admins can create new slots, view all bookings, and cancel slots.\n\n"
            "For any issues, contact the administrator."
        )
        await context.bot.send_message(chat_id=user_id, text=help_text, parse_mode="Markdown")

    # ADMIN PANEL
    elif data == "admin_panel":
        if user_id not in ADMIN_IDS:
            await context.bot.send_message(chat_id=user_id, text="❌ Unauthorized.")
            return

        buttons = [
            [InlineKeyboardButton("➕ Create Slot", callback_data="create_slot")],
            [InlineKeyboardButton("📊 List Slots", callback_data="list_slots")],
            [InlineKeyboardButton("📤 Export Bookings", callback_data="export_bookings")],
        ]

        await query.edit_message_text(
            "Admin Panel",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ADMIN LIST SLOTS
    elif data == "list_slots":

        if user_id not in ADMIN_IDS:
            await context.bot.send_message(chat_id=user_id, text="❌ Unauthorized.")
            return

        db = SessionLocal()

        try:
            slots = get_all_upcoming_slots(db)

            if not slots:
                await context.bot.send_message(chat_id=user_id, text="No slots available.")
                return

            buttons = []
            for slot in slots:
                buttons.append([
                    InlineKeyboardButton(
                        f"{slot.date} | {slot.start_time}-{slot.end_time}",
                        callback_data=f"admin_slot_detail:{slot.id}"
                    )
                ])

            await query.edit_message_text(
                "Select a slot:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        finally:
            db.close()

    # ADMIN SLOT DETAIL
    elif data.startswith("admin_slot_detail:"):

        if user_id not in ADMIN_IDS:
            await query.edit_message_text("❌ Unauthorized.")
            return

        slot_id = int(data.split(":")[1])

        db = SessionLocal()

        try:
            slot = get_slot_with_bookings(db, slot_id)

            if not slot:
                await query.edit_message_text("Slot not found.")
                return

            # Only count CONFIRMED bookings
            confirmed = [
                b for b in slot.bookings
                if b.status.name == "CONFIRMED"
            ]

            remaining = slot.capacity - len(confirmed)

            message = (
                f"📅 {slot.date}\n"
                f"⏰ {slot.start_time} - {slot.end_time}\n"
                f"👥 Capacity: {slot.capacity}\n"
                f"🟢 Confirmed: {len(confirmed)}\n"
                f"🪑 Remaining: {remaining}\n\n"
            )

            if confirmed:
                message += "👤 Booked Users:\n"
                for b in confirmed:
                    message += f"- {b.name} (ID: {b.telegram_user_id})\n"
            else:
                message += "No confirmed bookings yet.\n"

            # Add Cancel Slot button only if slot is ACTIVE
            buttons = []
            if slot.status.name == "ACTIVE":
                buttons.append([
                    InlineKeyboardButton(
                        "❌ Cancel Slot",
                        callback_data=f"admin_cancel_slot:{slot.id}"
                    )
                ])

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
            )

        finally:
            db.close()

    # ADMIN CANCEL SLOT
    elif data.startswith("admin_cancel_slot:"):

        if user_id not in ADMIN_IDS:
            await query.edit_message_text("❌ Unauthorized.")
            return

        slot_id = int(data.split(":")[1])

        db = SessionLocal()

        try:
            slot = get_slot_with_bookings(db, slot_id)

            if not slot:
                await query.edit_message_text("Slot not found.")
                return

            # Get confirmed bookings before cancellation
            confirmed_bookings = [
                b for b in slot.bookings
                if b.status.name == "CONFIRMED"
            ]

            # Cancel slot
            cancel_slot(db, slot_id)

            # Notify all users
            for booking in confirmed_bookings:
                try:
                    await context.bot.send_message(
                        chat_id=booking.telegram_user_id,
                        text=f"⚠ Slot on {slot.date} {slot.start_time}-{slot.end_time} has been cancelled by admin."
                    )
                except Exception:
                    pass  # Avoid breaking loop if one user blocked bot

            await query.edit_message_text("✅ Slot cancelled and users notified.")

        finally:
            db.close()

    # ADMIN EXPORT BOOKINGS
    elif data == "export_bookings":

        if user_id not in ADMIN_IDS:
            await query.edit_message_text("❌ Unauthorized.")
            return

        db = SessionLocal()

        try:
            bookings = get_all_confirmed_bookings(db)

            if not bookings:
                await query.edit_message_text("No confirmed bookings found.")
                return

            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow([
                "Booking ID",
                "User Name",
                "Telegram User ID",
                "Slot Date",
                "Start Time",
                "End Time",
                "Created At"
            ])

            # Rows
            for b in bookings:
                writer.writerow([
                    b.id,
                    b.name,
                    b.telegram_user_id,
                    b.slot.date,
                    b.slot.start_time,
                    b.slot.end_time,
                    b.created_at,
                ])

            output.seek(0)

            # Send file
            await query.message.reply_document(
                document=InputFile(
                    io.BytesIO(output.getvalue().encode()),
                    filename="bookings_export.csv"
                ),
                caption="📤 Confirmed Bookings Export"
            )

        finally:
            db.close()

    else:
        await query.edit_message_text("Invalid option.")

# ==============================
# ADMIN CREATE SLOT CONVERSATION
# ==============================

async def start_create_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ADMIN_IDS:
        await update.callback_query.edit_message_text("❌ Unauthorized.")
        return ConversationHandler.END

    await update.callback_query.edit_message_text(
        "Enter slot date (YYYY-MM-DD):"
    )
    return CREATE_SLOT_DATE


async def create_slot_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        slot_date = datetime.strptime(update.message.text, "%Y-%m-%d").date()
        context.user_data["slot_date"] = slot_date
    except ValueError:
        await update.message.reply_text("Invalid date format. Use YYYY-MM-DD.")
        return CREATE_SLOT_DATE

    await update.message.reply_text("Enter start time (HH:MM):")
    return CREATE_SLOT_START


async def create_slot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        start_time = datetime.strptime(update.message.text, "%H:%M").time()
        context.user_data["start_time"] = start_time
    except ValueError:
        await update.message.reply_text("Invalid time format. Use HH:MM.")
        return CREATE_SLOT_START

    await update.message.reply_text("Enter end time (HH:MM):")
    return CREATE_SLOT_END


async def create_slot_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        end_time = datetime.strptime(update.message.text, "%H:%M").time()
        context.user_data["end_time"] = end_time
    except ValueError:
        await update.message.reply_text("Invalid time format. Use HH:MM.")
        return CREATE_SLOT_END

    await update.message.reply_text("Enter capacity:")
    return CREATE_SLOT_CAPACITY


async def create_slot_capacity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        capacity = int(update.message.text)
        context.user_data["capacity"] = capacity
    except ValueError:
        await update.message.reply_text("Capacity must be a number.")
        return CREATE_SLOT_CAPACITY

    await update.message.reply_text("Enter slot title:")
    return CREATE_SLOT_TITLE


async def create_slot_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text
    db = SessionLocal()

    try:
        create_slot(
            db=db,
            slot_date=context.user_data["slot_date"],
            start_time=context.user_data["start_time"],
            end_time=context.user_data["end_time"],
            capacity=context.user_data["capacity"],
            title=title
        )
        await update.message.reply_text("✅ Slot created successfully!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    finally:
        db.close()

    return ConversationHandler.END

# ==============================
# Text Fallback Handler
# ==============================
async def show_booking_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = date.today()
    buttons = []

    for i in range(7):
        d = today + timedelta(days=i)
        buttons.append([
            InlineKeyboardButton(
                d.strftime("%Y-%m-%d"),
                callback_data=f"select_date:{d.isoformat()}"
            )
        ])

    await update.message.reply_text(
        "Select a date:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_my_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user_id = update.effective_user.id

    try:
        bookings = get_user_bookings(db, user_id)

        if not bookings:
            await update.message.reply_text("You have no bookings.")
            return

        message = "Your Bookings:\n\n"

        for b in bookings:
            message += (
                f"📅 {b.slot.date} | "
                f"{b.slot.start_time}-{b.slot.end_time}\n"
            )

        await update.message.reply_text(message)

    finally:
        db.close()

async def text_fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip().lower()
    user_id = update.effective_user.id

    if text in ["book slot", "book"]:
        await show_booking_dates(update, context)

    elif text in ["my bookings", "my booking"]:
        await show_my_bookings(update, context)

    elif text in ["help"]:
        help_text = (
            "📌 *How to Use This Bot:*\n\n"
            "1️⃣ Type 'book slot/book' to see available dates and times.\n"
            "2️⃣ Select a date, then choose a slot to book.\n"
            "3️⃣ View your bookings under 'My Bookings' and cancel if needed.\n\n"
            "⚠️ *Admin Panel:*\n"
            "- Admins can create new slots, view all bookings, and cancel slots.\n\n"
            "For any issues, contact the administrator."
        )
        await context.bot.send_message(chat_id=user_id, text=help_text, parse_mode="Markdown")

    elif text in ["admin panel"] and user_id in ADMIN_IDS:
        buttons = [
            [InlineKeyboardButton("➕ Create Slot", callback_data="create_slot")],
            [InlineKeyboardButton("📊 List Slots", callback_data="list_slots")],
            [InlineKeyboardButton("📤 Export Bookings", callback_data="export_bookings")],
        ]

        await update.message.reply_text(
            "Admin Panel",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    else:
        await update.message.reply_text(
            "Please use menu buttons or type:\n"
            "- Book Slot\n"
            "- My Bookings\n"
            "- Help"
        )