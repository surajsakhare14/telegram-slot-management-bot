from datetime import date, time, timedelta
import pytest
from services.slot_service import create_slot, SlotOverlapError, SlotInPast


def test_create_slot_success(db_session):
    slot = create_slot(
        db=db_session,
        slot_date=date.today() + timedelta(days=1),  # future-safe
        start_time=time(10, 0),
        end_time=time(11, 0),
        capacity=2,
        title="Test"
    )

    assert slot.id is not None
    assert slot.capacity == 2


def test_overlap_prevention(db_session):
    future_date = date.today() + timedelta(days=1)

    create_slot(
        db=db_session,
        slot_date=future_date,
        start_time=time(10, 0),
        end_time=time(11, 0),
        capacity=2,
        title="Test"
    )

    with pytest.raises(SlotOverlapError):
        create_slot(
            db=db_session,
            slot_date=future_date,
            start_time=time(10, 30),
            end_time=time(11, 30),
            capacity=2,
            title="Overlap"
        )


def test_past_slot_prevention(db_session):
    with pytest.raises(SlotInPast):
        create_slot(
            db=db_session,
            slot_date=date.today() - timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            capacity=2,
            title="Past"
        )