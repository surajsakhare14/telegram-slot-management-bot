import pytest
from datetime import date, time, timedelta
from services.slot_service import create_slot
from services.booking_service import (
    book_slot,
    SlotFull,
    AlreadyBooked
)


def test_capacity_enforcement(db_session):
    future_date = date.today() + timedelta(days=1)

    slot = create_slot(
        db=db_session,
        slot_date=future_date,
        start_time=time(12, 0),
        end_time=time(13, 0),
        capacity=1,
        title="Capacity Test"
    )

    book_slot(
        db=db_session,
        slot_id=slot.id,
        telegram_user_id=1,
        name="User1"
    )

    with pytest.raises(SlotFull):
        book_slot(
            db=db_session,
            slot_id=slot.id,
            telegram_user_id=2,
            name="User2"
        )


def test_duplicate_booking(db_session):
    future_date = date.today() + timedelta(days=1)

    slot = create_slot(
        db=db_session,
        slot_date=future_date,
        start_time=time(14, 0),
        end_time=time(15, 0),
        capacity=2,
        title="Duplicate Test"
    )

    book_slot(
        db=db_session,
        slot_id=slot.id,
        telegram_user_id=1,
        name="User1"
    )

    with pytest.raises(AlreadyBooked):
        book_slot(
            db=db_session,
            slot_id=slot.id,
            telegram_user_id=1,
            name="User1"
        )