# services/booking_service.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from datetime import datetime

from db.models import Slot, Booking, SlotStatus, BookingStatus


# ============================================================
# Exceptions
# ============================================================

class SlotNotFound(Exception):
    """Raised when slot does not exist."""
    pass


class SlotCancelled(Exception):
    """Raised when booking is attempted on a cancelled slot."""
    pass


class SlotFull(Exception):
    """Raised when slot capacity is exhausted."""
    pass


class AlreadyBooked(Exception):
    """Raised when user tries to book the same slot twice."""
    pass


class BookingNotFound(Exception):
    """Raised when booking does not exist."""
    pass

class SlotInPast(Exception):
    """Raised when attempting to book a past slot."""
    pass


# ============================================================
# Booking Logic
# ============================================================

def book_slot(
    db: Session,
    *,
    slot_id: int,
    telegram_user_id: int,
    name: str,
) -> Booking:
    """
    Book a slot using transactional row-level locking.

    Concurrency Strategy:
    - Lock slot row using SELECT ... FOR UPDATE
    - Validate slot status
    - Prevent booking past slots
    - Count confirmed bookings inside same transaction
    - Enforce capacity check
    - Partial unique index prevents duplicate confirmed booking
    """

    try:
        # 🔒 Lock slot row to prevent race conditions
        slot = (
            db.query(Slot)
            .filter(Slot.id == slot_id)
            .with_for_update()
            .first()
        )

        if not slot:
            raise SlotNotFound("Slot does not exist.")

        if slot.status == SlotStatus.CANCELLED:
            raise SlotCancelled("Slot is cancelled.")

        # ⏳ Prevent booking past slots (time-aware check)
        now = datetime.now()
        slot_end_datetime = datetime.combine(slot.date, slot.end_time)

        if slot_end_datetime <= now:
            raise SlotInPast("Cannot book a past slot.")

        # 👥 Count confirmed bookings
        confirmed_count = (
            db.query(func.count(Booking.id))
            .filter(
                Booking.slot_id == slot_id,
                Booking.status == BookingStatus.CONFIRMED,
            )
            .scalar()
        )

        if confirmed_count >= slot.capacity:
            raise SlotFull("Slot is sold out.")

        # 📝 Create booking
        booking = Booking(
            slot_id=slot_id,
            telegram_user_id=telegram_user_id,
            name=name,
            status=BookingStatus.CONFIRMED,
        )

        db.add(booking)
        db.commit()
        db.refresh(booking)

        return booking

    except IntegrityError:
        db.rollback()
        raise AlreadyBooked("User already booked this slot.")

    except Exception:
        db.rollback()
        raise


# ============================================================
# Booking Queries
# ============================================================

def get_user_bookings(db: Session, telegram_user_id: int):
    """
    Return confirmed bookings for a user.
    """

    return (
        db.query(Booking)
        .filter(
            Booking.telegram_user_id == telegram_user_id,
            Booking.status == BookingStatus.CONFIRMED,
        )
        .all()
    )


def cancel_booking(db: Session, booking_id: int):
    """
    Cancel a booking (soft cancel).
    Frees slot capacity since only CONFIRMED bookings are counted.
    """

    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .first()
    )

    if not booking:
        raise BookingNotFound("Booking not found.")

    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)

    return booking


def get_all_confirmed_bookings(db: Session):
    """
    Return all confirmed bookings for export/reporting.
    """

    return (
        db.query(Booking)
        .filter(Booking.status == BookingStatus.CONFIRMED)
        .all()
    )