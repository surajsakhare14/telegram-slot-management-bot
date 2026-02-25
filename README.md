# Telegram Slot Management Bot  
**BirdVision Assignment Submission**

A production-ready Telegram-based slot booking system built with transactional integrity, concurrency safety, and clean layered architecture.

---

## 🛠 Tech Stack

- Python 3.12
- python-telegram-bot (v20+)
- PostgreSQL
- SQLAlchemy ORM
- Alembic (migrations)
- Pytest (unit + concurrency tests)

---

# 🚀 Features

## 👤 User Features

- View available slots (next 7 days)
- View remaining seat count per slot
- Book a slot
- Prevent duplicate booking
- Capacity enforcement
- Cancel booking
- Re-book after cancellation
- Prevent booking past time slots
- Inline keyboard navigation
- Fallback text command support

---

## 🛠 Admin Features

- Create slot (multi-step conversation flow)
- Prevent overlapping slots
- Prevent creating expired slots
- List all active slots
- View slot details:
  - Capacity
  - Confirmed bookings
  - Remaining seats
- Cancel slot (cancels all confirmed bookings)
- Export confirmed bookings as CSV

---

# 🔔 Notifications

The system sends automatic notifications:

- ✅ On booking confirmation → user receives confirmation
- ❌ On booking cancellation → user receives confirmation
- 🚨 On admin cancelling a slot → all users with confirmed bookings are notified

---

# 🏗 Architecture Overview

The system follows a clean layered architecture:


bot/ → Telegram handlers (UI layer)
services/ → Business logic
db/ → Models & session management
tests/ → Unit & integration tests


---

## 🎯 Design Principles

- Separation of concerns
- Transaction-safe booking logic
- Database-level constraints
- Concurrency-safe operations
- Test isolation (separate test DB)
- Deterministic business rules

---

# 🧠 Concurrency Strategy

Booking logic ensures race-condition safety using:

- `SELECT ... FOR UPDATE` (row-level locking)
- Capacity validation inside same transaction
- Partial unique index on confirmed bookings
- Transaction boundary inside service layer

This guarantees:

- No overbooking
- No duplicate confirmed booking
- Safe concurrent booking attempts

Concurrency behavior is verified using a multi-threaded pytest test.

---

# 🗄 Database Design

## Slot Table

Fields:
- date
- start_time
- end_time
- capacity
- status (ACTIVE / CANCELLED)

Constraints:
- `capacity > 0`
- `end_time > start_time`

---

## Booking Table

Fields:
- slot_id (FK)
- telegram_user_id
- name
- status (CONFIRMED / CANCELLED)

---

## 🔒 Important Constraint

Partial unique index:


(slot_id, telegram_user_id)
WHERE status = 'CONFIRMED'


This allows:
- Cancel → Re-book
- Prevent duplicate confirmed bookings

---

# 📌 Overlap Policy

**Global overlap policy per date.**

No two ACTIVE slots may overlap on the same date, regardless of title.

---

# ⏳ Past-Time Validation

The system prevents:

- Creating slots in the past
- Creating slots earlier than current time on the same day
- Booking slots that have already ended

This ensures real-world booking correctness.

---

# ⚙️ Setup Instructions

## 1️⃣ Clone Repository

```bash
git clone <repo_url>
cd telegram-slot-bot

2️⃣ Create Virtual Environment
python -m venv venv
venv\Scripts\activate   # Windows

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Setup PostgreSQL

Create production DB:

CREATE DATABASE telegram_slot_db;

Create test DB:

CREATE DATABASE telegram_slot_test_db;

5️⃣ Configure Environment Variables

Copy example file:

cp .env.example .env

Update .env:

BOT_TOKEN=your_telegram_bot_token
ADMIN_TELEGRAM_IDS=your_telegram_user_id
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/telegram_slot_db
TEST_DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/telegram_slot_test_db

6️⃣ Run Migrations
alembic upgrade head

7️⃣ Start Bot
python -m bot.main

🧪 Running Tests

Tests use a separate PostgreSQL test database.

pytest

Test coverage includes:

Slot creation validation

Overlap prevention

Past-slot prevention

Capacity enforcement

Duplicate booking prevention

Concurrency integration test

📤 CSV Export

Admin can export confirmed bookings as CSV:

Generated in memory

No temporary files

Includes slot and user details

Cancelled bookings are excluded

📡 API / curl Usage

This project is a Telegram bot and does not expose REST endpoints.

Example Telegram Bot API usage:

curl -X POST https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "<CHAT_ID>", "text": "Test message"}'

🔒 Security

Admin access restricted via Telegram User ID

Authorization enforced at handler level

Business rules enforced at DB level

Concurrency-safe booking transactions

Test DB isolated from production DB

📊 Evaluation Highlights

Clean layered architecture

Strict transactional integrity

Concurrency-safe booking logic

Database-level enforcement

Deterministic test suite

Production-ready structure

👤 Author

Suraj Sakhare
Backend Developer
