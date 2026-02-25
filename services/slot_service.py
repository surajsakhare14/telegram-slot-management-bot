# services/slot_service.py

from datetime import date, time, datetime
from sqlalchemy.orm import Session

from db.models import Slot, SlotStatus
from services.booking_service import BookingStatus


# ============================================================
# Exceptions
# ============================================================

class SlotAlreadyExists(Exception):
    """Raised when attempting to create a duplicate slot."""
    pass


class SlotInPast(Exception):
    """Raised when attempting to create a slot in the past."""
    pass


class SlotOverlapError(Exception):
    """Raised when slot time overlaps with an existing active slot."""
    pass


class SlotNotFound(Exception):
    """Raised when a slot does not exist."""
    pass


# ============================================================
# Slot Creation
# ============================================================

def create_slot(
    db: Session,
    *,
    slot_date: date,
    start_time: time,
    end_time: time,
    capacity: int,
    title: str | None = None,
) -> Slot:
    """
    Create a new slot.

    Prevent:
    - Past date
    - Past time on current date
    - Overlapping ACTIVE slots
    """

    now = datetime.now()

    # Block past date
    if slot_date < now.date():
        raise SlotInPast("Cannot create slot in the past.")

    # Block past time today
    if slot_date == now.date():
        slot_end_datetime = datetime.combine(slot_date, end_time)
        if slot_end_datetime <= now:
            raise SlotInPast("Cannot create slot in the past.")

    # Overlap check (global policy)
    overlapping_slot = (
        db.query(Slot)
        .filter(
            Slot.date == slot_date,
            Slot.status == SlotStatus.ACTIVE,
            Slot.start_time < end_time,
            Slot.end_time > start_time,
        )
        .first()
    )

    if overlapping_slot:
        raise SlotOverlapError("Slot overlaps with existing slot.")

    slot = Slot(
        title=title,
        date=slot_date,
        start_time=start_time,
        end_time=end_time,
        capacity=capacity,
        status=SlotStatus.ACTIVE,
    )

    db.add(slot)
    db.commit()
    db.refresh(slot)

    return slot


# ============================================================
# Slot Management
# ============================================================

def cancel_slot(db: Session, slot_id: int) -> Slot:
    """
    Cancel slot and cancel all confirmed bookings.
    """

    slot = db.query(Slot).filter(Slot.id == slot_id).first()

    if not slot:
        raise SlotNotFound("Slot not found.")

    # Mark slot as cancelled
    slot.status = SlotStatus.CANCELLED

    # Cancel all confirmed bookings
    for booking in slot.bookings:
        if booking.status == BookingStatus.CONFIRMED:
            booking.status = BookingStatus.CANCELLED

    db.commit()
    db.refresh(slot)

    return slot


def list_slots_by_date(db: Session, slot_date: date):
    """
    Return all ACTIVE slots for a given date.
    """

    return (
        db.query(Slot)
        .filter(
            Slot.date == slot_date,
            Slot.status == SlotStatus.ACTIVE,
        )
        .order_by(Slot.start_time)
        .all()
    )


def get_all_upcoming_slots(db: Session):
    """
    Return all ACTIVE slots ordered by date and time.
    """

    return (
        db.query(Slot)
        .filter(Slot.status == SlotStatus.ACTIVE)
        .order_by(Slot.date, Slot.start_time)
        .all()
    )


def get_slot_with_bookings(db: Session, slot_id: int):
    """
    Fetch a slot along with its related bookings.
    """

    return (
        db.query(Slot)
        .filter(Slot.id == slot_id)
        .first()
    )