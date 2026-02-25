# db/models.py

import enum
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Date,
    Time,
    DateTime,
    ForeignKey,
    Enum,
    CheckConstraint,
    UniqueConstraint,
    Index,
    func
)
from sqlalchemy.orm import relationship
from .base import Base


# -----------------------------
# ENUM DEFINITIONS
# -----------------------------

class SlotStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"


class BookingStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


# -----------------------------
# SLOT MODEL
# -----------------------------

class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True)

    title = Column(String(255), nullable=True)

    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    capacity = Column(Integer, nullable=False)

    status = Column(
        Enum(SlotStatus, name="slot_status"),
        nullable=False,
        default=SlotStatus.ACTIVE
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationship
    bookings = relationship(
        "Booking",
        back_populates="slot",
        cascade="all, delete-orphan"
    )

    # Table-level constraints
    __table_args__ = (
        CheckConstraint("capacity > 0", name="check_capacity_positive"),
        CheckConstraint("end_time > start_time", name="check_valid_time_range"),
        Index("idx_slot_date", "date"),
    )


# -----------------------------
# BOOKING MODEL
# -----------------------------

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)

    slot_id = Column(
        Integer,
        ForeignKey("slots.id", ondelete="CASCADE"),
        nullable=False
    )

    telegram_user_id = Column(
        BigInteger,   # Telegram IDs can exceed 32-bit integer
        nullable=False,
        index=True
    )

    name = Column(String(255), nullable=False)

    status = Column(
        Enum(BookingStatus, name="booking_status"),
        nullable=False,
        default=BookingStatus.CONFIRMED
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationship
    slot = relationship("Slot", back_populates="bookings")

    # Prevent duplicate booking by same user for same slot
    __table_args__ = (
        Index(
            "unique_confirmed_booking",
            "slot_id",
            "telegram_user_id",
            unique=True,
            postgresql_where=(status == BookingStatus.CONFIRMED)
        ),
    )