# System Design Document  
Telegram Slot Management Bot  

Author: Suraj Sakhare  

---

# 1️⃣ System Overview

This project implements a Telegram-based slot booking system with:

- Admin-controlled slot creation and cancellation
- User booking and cancellation flows
- Capacity enforcement
- Concurrency-safe booking logic
- CSV export for reporting
- Past-time validation
- Notification support

The system is designed with production-oriented principles including:

- Transactional integrity
- Concurrency safety
- Database-level constraints
- Clean layered architecture
- Deterministic test isolation

---

# 2️⃣ High-Level Architecture

The application follows a layered architecture:


Telegram UI (bot/)
↓
Business Logic (services/)
↓
Data Layer (SQLAlchemy ORM)
↓
PostgreSQL Database


---

## Layer Responsibilities

### 🟢 bot/
- Telegram handlers
- Conversation flows
- Admin authorization checks
- User interaction logic
- Notification triggering
- No business rule implementation

### 🟡 services/
- Core business logic
- Booking validation
- Capacity enforcement
- Overlap prevention
- Past-time validation
- Concurrency control
- Transaction management

### 🔵 db/
- SQLAlchemy models
- Session management
- Database schema definitions
- Constraints & indexes

This separation ensures:
- Testability
- Maintainability
- Clear responsibility boundaries
- Clean dependency flow

---

# 3️⃣ Database Design

## Slot Table

Fields:
- id
- title
- date
- start_time
- end_time
- capacity
- status (ACTIVE / CANCELLED)
- created_at

Constraints:
- `capacity > 0`
- `end_time > start_time`

### Overlap Policy (Design Decision)

The system enforces a **global overlap policy per date**.

No two ACTIVE slots may overlap on the same date, regardless of title.

This simplifies:
- Capacity management
- Time window clarity
- Concurrency correctness

---

## Booking Table

Fields:
- id
- slot_id (ForeignKey)
- telegram_user_id
- name
- status (CONFIRMED / CANCELLED)
- created_at

---

## Important Constraint

Partial Unique Index:


(slot_id, telegram_user_id)
WHERE status = 'CONFIRMED'


Reason:
- Prevent duplicate confirmed bookings
- Allow cancel → re-book flow
- Enforce rule at database level
- Protect against race conditions

---

# 4️⃣ Concurrency Strategy

## Problem

Two users attempting to book the last available seat simultaneously can cause overbooking.

## Solution

Booking logic uses:

1. `SELECT ... FOR UPDATE` on the Slot row
2. Transaction boundary inside service layer
3. Count confirmed bookings within the same transaction
4. Capacity check before insertion
5. Commit transaction atomically

Flow:

Thread A locks slot row  
Thread B waits  
Thread A commits booking  
Thread B re-checks capacity  
Thread B fails if full  

This guarantees strict correctness under concurrent booking attempts.

Concurrency behavior is verified using multi-threaded pytest tests.

---

# 5️⃣ Past-Time Validation

The system prevents:

- Creating slots in the past
- Creating slots whose end time has already passed (same day)
- Booking slots whose end time has already passed

Validation rule:

A slot is considered expired if:

- `slot_date < today`
OR
- `slot_date == today AND slot_end_time <= current_time`

This ensures real-world correctness.

---

# 6️⃣ Business Rules Enforcement

Business rules are enforced at two levels:

## Application Level
- Slot cannot be in the past
- No overlapping ACTIVE slots
- Cannot book cancelled slot
- Capacity validation
- Cannot book expired slot

## Database Level
- Check constraints
- Foreign keys
- Partial unique index
- Transaction isolation

This layered enforcement prevents logic bypass.

---

# 7️⃣ Notifications Design

Notifications are triggered at handler level:

- On booking confirmation → user notified
- On booking cancellation → user notified
- On admin cancelling slot → all confirmed users notified

When admin cancels a slot:
- Slot status → CANCELLED
- All confirmed bookings → CANCELLED
- Users are notified
- Cancelled bookings excluded from export

---

# 8️⃣ Admin Authorization

Admin access is restricted using Telegram User IDs.

- `ADMIN_TELEGRAM_IDS` stored in environment variables
- Verified inside handler logic
- UI visibility does not equal authorization

Security principle:
Always validate server-side, never trust client UI state.

---

# 9️⃣ CSV Export Design

CSV export:

- Fetches only CONFIRMED bookings
- Excludes cancelled bookings
- Generated in memory using `StringIO`
- No temporary files
- Sent directly via Telegram API

This avoids disk dependency and ensures clean execution.

---

# 🔟 Testing Strategy

## Test Database Isolation

Tests use a separate PostgreSQL database:

`telegram_slot_test_db`

Each test:
- Runs in isolation
- Uses fresh schema
- Does not touch production DB

---

## Test Coverage

- Slot creation validation
- Overlap prevention
- Past-slot prevention
- Duplicate booking prevention
- Capacity enforcement
- Cancellation flow
- Concurrency race condition test

Tests use future dates to remain deterministic.

---

# 11️⃣ Why PostgreSQL?

PostgreSQL was chosen for:

- Strong transaction support
- Row-level locking
- Partial indexes
- Reliable concurrency handling
- Production-grade reliability

---

# 12️⃣ Why Not Store Remaining Capacity?

Remaining capacity is calculated dynamically.

Reason:
- Avoid redundant state
- Prevent inconsistency
- Single source of truth remains Booking table
- Eliminates synchronization complexity

---

# 13️⃣ UX Design Considerations

- Inline keyboard is primary navigation
- Fallback text commands supported
- Remaining seats displayed in slot listing
- Clear confirmation messages for all actions

---

# 14️⃣ Scalability Considerations

For higher traffic:

- Switch polling → webhook
- Enable connection pooling
- Introduce caching layer
- Add async DB support
- Deploy behind reverse proxy
- Add structured logging

Current design prioritizes correctness and clarity.

---

# 15️⃣ Conclusion

The system prioritizes:

- Data integrity
- Concurrency correctness
- Clean architecture
- Separation of concerns
- Production-grade testing
- Deterministic behavior

It is designed to remain correct under concurrent usage and is structured for future extensibility.
