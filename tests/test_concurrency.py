import threading
from datetime import date, time, timedelta
from services.slot_service import create_slot
from services.booking_service import book_slot, SlotFull


def test_last_seat_concurrency(db_session, session_factory):

    future_date = date.today() + timedelta(days=1)

    slot = create_slot(
        db=db_session,
        slot_date=future_date,
        start_time=time(16, 0),
        end_time=time(17, 0),
        capacity=1,
        title="Concurrency"
    )

    results = []

    def attempt(user_id):
        db = session_factory()  # NEW session per thread
        try:
            book_slot(
                db=db,
                slot_id=slot.id,
                telegram_user_id=user_id,
                name=f"User{user_id}"
            )
            results.append("success")
        except SlotFull:
            results.append("failed")
        finally:
            db.close()

    t1 = threading.Thread(target=attempt, args=(101,))
    t2 = threading.Thread(target=attempt, args=(202,))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results.count("success") == 1
    assert results.count("failed") == 1