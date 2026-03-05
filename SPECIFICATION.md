# Hotel Multi-Restaurant Ordering System — Backend Specification

## 1. Overview

This is the backend for a hotel in-room ordering system. Guests scan a QR code in their room, choose a restaurant, browse the menu, and place an order for delivery to their room. Staff view incoming orders on a kitchen display and move them through a status pipeline. The system also supports table reservations with QR-code confirmation.

### Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.109+ |
| Server | Uvicorn (ASGI) |
| Database | PostgreSQL (async via asyncpg) |
| ORM | SQLAlchemy 2.x with async sessions |
| Validation & Config | Pydantic v2, pydantic-settings |
| Authentication | JWT (HS256) via python-jose, bcrypt via passlib |
| Encryption | AES-256-GCM via the `cryptography` library |
| QR Codes | `qrcode` + Pillow |

---

## 2. Project Structure

```
restoback/
├── .env.example              # Template for environment variables
├── .gitignore
├── README.md
├── SPECIFICATION.md           # This file
├── requirements.txt           # Python dependencies
│
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app, router registration, root/health endpoints
│   ├── config.py              # Settings loaded from .env via pydantic-settings
│   ├── database.py            # Async SQLAlchemy engine, session factory, get_db dependency
│   ├── models.py              # SQLAlchemy ORM models and enums
│   ├── schemas.py             # Pydantic request/response schemas
│   ├── auth.py                # JWT creation, get_current_user, require_role dependencies
│   ├── encryption.py          # AES-256-GCM encrypt/decrypt, HMAC phone_hash
│   │
│   └── routers/
│       ├── __init__.py
│       ├── auth.py            # OTP request/verify, staff login, /me
│       ├── restaurants.py     # Restaurant CRUD and menu listing
│       ├── orders.py          # Order creation, listing, cancellation
│       ├── kitchen.py         # Kitchen order list, status updates, order editing
│       ├── menu_items.py      # Menu item listing, update, delete
│       ├── rooms.py           # Room listing and creation
│       ├── tables.py          # Table CRUD (role-protected)
│       ├── reservations.py    # Reservation CRUD, slots, confirm via QR, QR image
│       ├── admin.py           # Staff account management (establishment_admin only)
│       └── pages.py           # Serves HTML templates for guest, kitchen, admin UIs
│
├── scripts/
│   ├── init_db.py             # Creates all tables via Base.metadata.create_all
│   ├── reset_db.py            # Drops all tables, then recreates them
│   ├── seed.py                # Seeds rooms, restaurants, menu items, tables, staff users
│   ├── seed_orders.py         # Seeds demo orders (supports --clear flag)
│   └── setup.py               # Runs reset_db + seed + seed_orders in sequence
│
├── templates/
│   ├── room.html              # Guest ordering page
│   ├── kitchen.html           # Kitchen display page
│   ├── login.html             # Staff/guest login page
│   ├── reserve.html           # Table reservation page
│   ├── admin.html             # Admin panel page
│   └── scanner.html           # QR code scanner page
│
└── extracted/                 # Reference copies of HTML and router code (not used at runtime)
```

---

## 3. Configuration

Settings are managed by `app/config.py` using `pydantic-settings`. All values are loaded from a `.env` file (copy `.env.example` to `.env`).

| Variable | Type | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | `str` | `postgresql+asyncpg://user:password@localhost:5432/resto_db` | PostgreSQL connection string. A validator auto-converts `postgresql://` to `postgresql+asyncpg://` if the async driver prefix is missing. |
| `AES_ENCRYPTION_KEY` | `str` | `"0" * 64` | 32-byte hex key for AES-256-GCM encryption of PII. Generate with `python -c "import os; print(os.urandom(32).hex())"`. |
| `JWT_SECRET_KEY` | `str` | `"change-me-in-production"` | Secret for signing JWT tokens. |
| `JWT_EXPIRY_MINUTES` | `int` | `1440` (24 hours) | JWT token lifetime. |
| `OTP_EXPIRY_MINUTES` | `int` | `5` | How long a one-time password stays valid. |

The `Settings` class is instantiated as a module-level singleton `settings` and imported throughout the app.

---

## 4. Database

### Engine and Sessions (`app/database.py`)

- **Engine:** `create_async_engine` with the configured `DATABASE_URL`, `echo=False`.
- **Session factory:** `async_sessionmaker` producing `AsyncSession` instances with `expire_on_commit=False`, `autocommit=False`, `autoflush=False`.
- **`get_db()` dependency:** Yields a session. Commits on success, rolls back on exception, closes in `finally`.

### Enums

| Enum | Values |
|---|---|
| `PaymentMethod` | `room_bill`, `pay_now` |
| `OrderStatus` | `received`, `preparing`, `ready`, `served`, `cancelled` |
| `UserRole` | `normal_user`, `establishment_admin`, `restaurant_admin`, `supervisor` |
| `ReservationStatus` | `pending`, `confirmed`, `cancelled`, `completed`, `no_show` |

All enums extend both `str` and `enum.Enum`, so they serialize as strings in JSON responses.

### Models (`app/models.py`)

All primary keys are `UUID` with `default=uuid4`. Foreign keys use `ondelete="CASCADE"` unless noted. All models inherit from `Base` (SQLAlchemy `DeclarativeBase`).

#### Restaurant (`restaurants`)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `name` | String(255) | NOT NULL |
| `description` | Text | nullable |
| `image_url` | String(512) | nullable |
| `open_from` | Time | nullable |
| `open_until` | Time | nullable |

Relationships: `menu_items`, `orders`, `tables`, `reservations`.

#### MenuItem (`menu_items`)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `restaurant_id` | UUID | FK -> restaurants.id (CASCADE), NOT NULL |
| `name` | String(255) | NOT NULL |
| `description` | Text | nullable |
| `price` | Numeric(10,2) | NOT NULL |
| `category` | String(128) | NOT NULL |
| `image_url` | String(512) | nullable |
| `allergens` | String(255) | nullable |
| `requires_option_selection` | Boolean | NOT NULL, default False |

Relationships: `restaurant`, `options` (MenuItemOption, cascade all/delete-orphan), `order_items`.

#### MenuItemOption (`menu_item_options`)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `menu_item_id` | UUID | FK -> menu_items.id (CASCADE), NOT NULL |
| `label` | String(128) | NOT NULL |
| `price_delta` | Numeric(10,2) | NOT NULL, default 0 |

Relationships: `menu_item`, `order_item_options`.

#### Order (`orders`)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `restaurant_id` | UUID | FK -> restaurants.id (CASCADE), NOT NULL |
| `room_id` | String(32) | NOT NULL (plain string, not a FK) |
| `party_size` | Integer | NOT NULL |
| `payment_method` | Enum(PaymentMethod) | NOT NULL, default `room_bill` |
| `status` | Enum(OrderStatus) | NOT NULL, default `received` |
| `subtotal` | Numeric(10,2) | NOT NULL |
| `notes` | Text | nullable |
| `created_at` | DateTime | default `utcnow()` |

Relationships: `restaurant`, `items` (OrderItem, cascade all/delete-orphan).

#### OrderItem (`order_items`)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `order_id` | UUID | FK -> orders.id (CASCADE), NOT NULL |
| `menu_item_id` | UUID | FK -> menu_items.id (CASCADE), NOT NULL |
| `name` | String(255) | NOT NULL (snapshot of menu item name at time of order) |
| `unit_price` | Numeric(10,2) | NOT NULL (base price + selected option deltas) |
| `quantity` | Integer | NOT NULL |
| `notes` | Text | nullable |

Relationships: `order`, `menu_item`, `options` (OrderItemOption, cascade all/delete-orphan).

#### OrderItemOption (`order_item_options`)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `order_item_id` | UUID | FK -> order_items.id (CASCADE), NOT NULL |
| `menu_item_option_id` | UUID | FK -> menu_item_options.id (CASCADE), NOT NULL |

Relationships: `order_item`, `menu_item_option`.

#### Room (`rooms`)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `room_number` | String(32) | UNIQUE, NOT NULL |
| `display_name` | String(128) | nullable |

No relationships defined. Orders reference rooms by `room_id` string, not by FK.

#### User (`users`)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `encrypted_name` | Text | NOT NULL (AES-256-GCM encrypted) |
| `encrypted_phone` | Text | nullable (AES-256-GCM encrypted) |
| `phone_hash` | String(64) | UNIQUE, nullable (HMAC-SHA256 blind index) |
| `encrypted_email` | Text | nullable (AES-256-GCM encrypted) |
| `password_hash` | String(255) | nullable (bcrypt hash, staff only) |
| `role` | Enum(UserRole) | NOT NULL, default `normal_user` |
| `restaurant_id` | UUID | FK -> restaurants.id (SET NULL), nullable |
| `is_active` | Boolean | NOT NULL, default True |
| `created_at` | DateTime | default `utcnow()` |

Relationships: `reservations`.

#### Table (`tables`)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `restaurant_id` | UUID | FK -> restaurants.id (CASCADE), NOT NULL |
| `table_number` | String(32) | NOT NULL |
| `capacity` | Integer | NOT NULL, default 4 |
| `is_active` | Boolean | NOT NULL, default True |

Relationships: `restaurant`, `reservations`.

#### Reservation (`reservations`)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK -> users.id (CASCADE), NOT NULL |
| `restaurant_id` | UUID | FK -> restaurants.id (CASCADE), NOT NULL |
| `table_id` | UUID | FK -> tables.id (CASCADE), NOT NULL |
| `reservation_date` | Date | NOT NULL |
| `reservation_time` | Time | NOT NULL |
| `party_size` | Integer | NOT NULL |
| `status` | Enum(ReservationStatus) | NOT NULL, default `pending` |
| `confirmation_code` | String(64) | UNIQUE, NOT NULL (generated via `secrets.token_urlsafe(16)`) |
| `notes` | Text | nullable |
| `created_at` | DateTime | default `utcnow()` |

Relationships: `user`, `restaurant`, `table`.

#### OTPCode (`otp_codes`)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `phone_hash` | String(64) | NOT NULL, indexed |
| `code` | String(6) | NOT NULL |
| `expires_at` | DateTime | NOT NULL |
| `is_used` | Boolean | NOT NULL, default False |

No relationships.

### Entity Relationship Diagram

```mermaid
erDiagram
    Restaurant ||--o{ MenuItem : "has"
    Restaurant ||--o{ Order : "receives"
    Restaurant ||--o{ TableEntity : "has"
    Restaurant ||--o{ Reservation : "has"

    MenuItem ||--o{ MenuItemOption : "has"
    MenuItem ||--o{ OrderItem : "referenced by"

    Order ||--o{ OrderItem : "contains"
    OrderItem ||--o{ OrderItemOption : "has"
    OrderItemOption }o--|| MenuItemOption : "references"

    UserEntity ||--o{ Reservation : "makes"
    TableEntity ||--o{ Reservation : "booked for"

    Restaurant {
        UUID id PK
        string name
        text description
        time open_from
        time open_until
    }

    MenuItem {
        UUID id PK
        UUID restaurant_id FK
        string name
        decimal price
        string category
        boolean requires_option_selection
    }

    MenuItemOption {
        UUID id PK
        UUID menu_item_id FK
        string label
        decimal price_delta
    }

    Order {
        UUID id PK
        UUID restaurant_id FK
        string room_id
        int party_size
        enum payment_method
        enum status
        decimal subtotal
        datetime created_at
    }

    OrderItem {
        UUID id PK
        UUID order_id FK
        UUID menu_item_id FK
        string name
        decimal unit_price
        int quantity
    }

    OrderItemOption {
        UUID id PK
        UUID order_item_id FK
        UUID menu_item_option_id FK
    }

    Room {
        UUID id PK
        string room_number
        string display_name
    }

    UserEntity {
        UUID id PK
        text encrypted_name
        text encrypted_phone
        string phone_hash
        enum role
        boolean is_active
    }

    TableEntity {
        UUID id PK
        UUID restaurant_id FK
        string table_number
        int capacity
        boolean is_active
    }

    Reservation {
        UUID id PK
        UUID user_id FK
        UUID restaurant_id FK
        UUID table_id FK
        date reservation_date
        time reservation_time
        int party_size
        enum status
        string confirmation_code
    }

    OTPCode {
        UUID id PK
        string phone_hash
        string code
        datetime expires_at
        boolean is_used
    }
```

---

## 5. Authentication and Authorization

Implemented in `app/auth.py` and `app/routers/auth.py`.

### Mechanisms

1. **OTP (guests):** A guest submits their phone number to `POST /api/auth/otp/request`, receives a 6-digit code (logged to console and returned in the response for demo purposes). They verify it via `POST /api/auth/otp/verify`, which finds or creates a `User` record and returns a JWT.

2. **Email + password (staff):** Staff accounts are created by an `establishment_admin` via `POST /api/admin/staff` with a bcrypt-hashed password. Staff log in via `POST /api/auth/login`. The system decrypts every staff user's email to find a match (acceptable for the small staff set; for scale, add an `email_hash` column).

3. **JWT tokens:** Signed with HS256 using `JWT_SECRET_KEY`. The payload contains `sub` (user UUID), `role`, `exp`, and optionally `rid` (restaurant UUID for restaurant-scoped staff). Default expiry is 24 hours. Tokens are sent in the `Authorization: Bearer <token>` header.

### Roles

| Role | Description |
|---|---|
| `normal_user` | Guests. Created via OTP. Can make reservations and view their own. |
| `supervisor` | Restaurant floor staff. Can confirm reservations and update reservation status. |
| `restaurant_admin` | Manages a single restaurant. Can manage tables and reservations for their restaurant. |
| `establishment_admin` | Hotel-level admin. Full access to staff CRUD, all tables, and all reservations. |

### FastAPI Dependencies

| Dependency | Behavior |
|---|---|
| `get_current_user` | Decodes JWT from `Authorization` header. Returns `User` or raises 401. |
| `get_optional_user` | Same as above but returns `None` instead of raising 401 when no token is present. |
| `require_role(*roles)` | Wraps `get_current_user`. Returns the user if their role is in `roles`, otherwise raises 403. |

### Auth Requirements by Router

| Router | Auth |
|---|---|
| `restaurants`, `orders`, `kitchen`, `menu_items`, `rooms`, `pages` | None (public) |
| `tables` | `require_role(establishment_admin, restaurant_admin)` |
| `reservations` | Mixed: `/slots` is public; CRUD requires `get_current_user`; confirm/status-update requires staff roles |
| `admin` | `require_role(establishment_admin)` |
| `auth` | Only `GET /me` requires `get_current_user` |

---

## 6. Encryption and Security (`app/encryption.py`)

PII fields (name, phone, email) are never stored in plaintext. The module provides three functions:

| Function | Purpose |
|---|---|
| `encrypt(plaintext) -> str` | AES-256-GCM encryption. Generates a random 12-byte nonce, encrypts, and returns `base64(nonce \|\| ciphertext \|\| tag)`. |
| `decrypt(token) -> str` | Reverses the above. Splits the base64-decoded bytes into nonce (first 12 bytes) and ciphertext+tag (rest), then decrypts. |
| `phone_hash(phone) -> str` | HMAC-SHA256 blind index using the AES key. Returns a 64-char hex digest. Used to look up users by phone number without decrypting every record. |

Password hashing uses bcrypt via `passlib.context.CryptContext`.

---

## 7. API Reference

All API routes are prefixed with `/api` except the HTML page routes. The app is created in `app/main.py` and registers routers in this order: restaurants, orders, kitchen, menu_items, rooms, auth, tables, reservations, admin, pages.

### Root Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/` | None | Returns JSON with links to docs, guest page, kitchen, etc. |
| `GET` | `/health` | None | Runs `SELECT 1` against the database. Returns `{"status": "ok"}` or 503 `{"status": "unhealthy"}`. |

### 7.1 Auth (`/api/auth`)

| Method | Path | Auth | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/otp/request` | None | `OTPRequest { phone }` | `{ message, expires_in_seconds, demo_code }` |
| `POST` | `/otp/verify` | None | `OTPVerify { phone, code, name? }` | `AuthResponse { access_token, token_type, user }` |
| `POST` | `/login` | None | `StaffLogin { email, password }` | `AuthResponse` |
| `GET` | `/me` | JWT | -- | `UserResponse` |

**Notes:**
- OTP verify finds or creates a `User`. If the phone hash matches an existing user, it reuses that user. If `name` is provided, it updates the user's encrypted name.
- Staff login iterates over all active staff users and decrypts their email to find a match, then verifies the bcrypt password hash.

### 7.2 Restaurants (`/api/restaurants`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `` | None | -- | `list[RestaurantResponse]` |
| `POST` | `` | None | `RestaurantCreate { name, description?, image_url?, open_from?, open_until? }` | `RestaurantResponse` |
| `GET` | `/{restaurant_id}` | None | -- | `RestaurantResponse` |
| `PATCH` | `/{restaurant_id}` | None | `RestaurantUpdate` (all fields optional) | `RestaurantResponse` |
| `GET` | `/{restaurant_id}/menu` | None | -- | `list[MenuItemResponse]` (ordered by category, name; includes options) |
| `POST` | `/{restaurant_id}/menu-items` | None | `MenuItemCreate` | `MenuItemResponse` |

### 7.3 Orders (`/api/orders`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `` | None | Query: `room_id?`, `restaurant_id?`, `status?`, `in_progress?` (bool), `from_date?`, `to_date?` | `list[OrderListResponse]` |
| `GET` | `/{order_id}` | None | -- | `OrderResponse` |
| `POST` | `` | None | `OrderCreate { restaurant_id, room_id, party_size, payment_method, items, notes? }` | `OrderResponse` |
| `PATCH` | `/{order_id}/cancel` | None | -- | `OrderResponse` |

**Notes:**
- Order creation validates that all `menu_item_id` values belong to the specified restaurant, enforces `requires_option_selection` if set, calculates `unit_price` as base price + sum of selected option `price_delta` values, and computes `subtotal`.
- The `in_progress=true` filter returns orders with status in (`received`, `preparing`, `ready`).
- Cancellation is only allowed when the order status is `received`, `preparing`, or `ready`.

### 7.4 Kitchen (`/api/kitchen`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `/orders` | None | Query: `restaurant_id` (required) | `list[OrderListResponse]` (excludes cancelled, newest first) |
| `PATCH` | `/orders/{order_id}` | None | `OrderStatusUpdate { status }` | `OrderListResponse` |
| `PUT` | `/orders/{order_id}/edit` | None | `KitchenOrderEdit { notes?, items_to_add, items_to_update, items_to_remove }` | `OrderListResponse` |

**Notes:**
- Kitchen edit supports adding new items (with options), updating quantity/notes on existing items, and removing items -- all in a single request. The subtotal is recalculated after every edit.
- Cannot edit cancelled or served orders.

### 7.5 Menu Items (`/api/menu-items`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `` | None | Query: `restaurant_id?` | `list[MenuItemResponse]` (ordered by category, name; includes options) |
| `PATCH` | `/{menu_item_id}` | None | `MenuItemUpdate` (all fields optional) | `MenuItemResponse` |
| `DELETE` | `/{menu_item_id}` | None | -- | 204 No Content |

### 7.6 Rooms (`/api/rooms`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `` | None | -- | `list[RoomResponse]` (ordered by room_number) |
| `GET` | `/{room_id}` | None | -- (room_id is the room_number string) | `RoomResponse` |
| `POST` | `` | None | `RoomCreate { room_number, display_name? }` | `RoomResponse` (409 if room_number already exists) |

### 7.7 Tables (`/api/tables`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `` | None | Query: `restaurant_id` (required), `active_only?` (default true) | `list[TableResponse]` |
| `POST` | `` | `establishment_admin` or `restaurant_admin` | `TableCreate { restaurant_id, table_number, capacity }` | `TableResponse` (201) |
| `PATCH` | `/{table_id}` | `establishment_admin` or `restaurant_admin` | `TableUpdate { table_number?, capacity?, is_active? }` | `TableResponse` |
| `DELETE` | `/{table_id}` | `establishment_admin` or `restaurant_admin` | -- | 204 (soft-delete: sets `is_active = False`) |

**Notes:**
- `restaurant_admin` users can only manage tables belonging to their own restaurant (enforced by comparing `user.restaurant_id` against the table's `restaurant_id`).

### 7.8 Reservations (`/api/reservations`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `/slots` | None | Query: `restaurant_id` (required), `date` (required) | `SlotsResponse { slots: list[str], booked: dict[str, list[UUID]] }` |
| `POST` | `` | JWT | `ReservationCreate { restaurant_id, table_id, reservation_date, reservation_time, party_size, notes? }` | `ReservationResponse` (201) |
| `GET` | `` | JWT | Query: `restaurant_id?`, `date?`, `status?` | `list[ReservationResponse]` |
| `GET` | `/{reservation_id}` | JWT | -- | `ReservationResponse` |
| `PATCH` | `/{reservation_id}/cancel` | JWT | -- | `ReservationResponse` |
| `POST` | `/confirm/{confirmation_code}` | Staff role | -- | `ReservationResponse` |
| `PATCH` | `/{reservation_id}/status` | Staff role | `ReservationStatusUpdate { status }` | `ReservationResponse` |
| `GET` | `/{reservation_id}/qr` | JWT or `token` query param | -- | PNG image (streamed) |

**Notes:**
- `reservation_time` must be on the hour (enforced by a Pydantic model validator).
- Slot generation uses the restaurant's `open_from`/`open_until` times to produce hourly slots.
- Conflict detection prevents double-booking the same table at the same date+time.
- `normal_user` can only see/cancel their own reservations. Staff see all (or those in their restaurant).
- The QR endpoint accepts a `token` query parameter as an alternative to the `Authorization` header, since browsers cannot set headers on `<img src>` tags.
- The QR code data is the URL `{base_url}/api/reservations/confirm/{confirmation_code}`.

### 7.9 Admin (`/api/admin`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `POST` | `/staff` | `establishment_admin` | `StaffCreate { name, email, password, role, restaurant_id? }` | `StaffResponse` (201) |
| `GET` | `/staff` | `establishment_admin` | -- | `list[StaffResponse]` (all staff users, ordered by created_at) |
| `PATCH` | `/staff/{user_id}` | `establishment_admin` | `StaffUpdate { name?, email?, role?, restaurant_id?, is_active? }` | `StaffResponse` |
| `DELETE` | `/staff/{user_id}` | `establishment_admin` | -- | 204 (soft-delete: sets `is_active = False`) |

**Notes:**
- Cannot create users with `normal_user` role through this endpoint (those are created via OTP).
- Staff passwords are hashed with bcrypt on creation. Name and email are AES-encrypted.

### 7.10 HTML Pages (no `/api` prefix)

| Method | Path | Template |
|---|---|---|
| `GET` | `/room/{room_id}` | `templates/room.html` |
| `GET` | `/kitchen` | `templates/kitchen.html` |
| `GET` | `/login` | `templates/login.html` |
| `GET` | `/reserve` | `templates/reserve.html` |
| `GET` | `/admin` | `templates/admin.html` |
| `GET` | `/scanner` | `templates/scanner.html` |

Templates are read from `templates/` at the project root. The pages router in `app/routers/pages.py` reads the HTML file from disk and returns it as an `HTMLResponse`. The `room_id` path parameter is available in the URL but the HTML file itself is static (the frontend JavaScript extracts the room ID from the URL).

---

## 8. Pydantic Schemas (`app/schemas.py`)

All response schemas use `model_config = {"from_attributes": True}` for ORM compatibility. Key schemas by domain:

### Restaurant

- `RestaurantCreate` -- name (required), description, image_url, open_from, open_until.
- `RestaurantUpdate` -- all fields optional.
- `RestaurantResponse` -- adds `id: UUID`.

### Menu

- `MenuItemCreate` -- name, price, category (required); description, image_url, allergens, requires_option_selection optional. Also takes `restaurant_id`.
- `MenuItemUpdate` -- all fields optional.
- `MenuItemResponse` -- full item with `id`, `restaurant_id`, and nested `options: list[MenuItemOptionResponse]`.
- `MenuItemOptionResponse` -- `id`, `label`, `price_delta`.

### Orders

- `OrderItemCreate` -- `menu_item_id`, `quantity` (>= 1), `notes?`, `option_ids?`.
- `OrderCreate` -- `restaurant_id`, `room_id`, `party_size` (1-50), `payment_method`, `items` (min 1), `notes?`.
- `OrderResponse` / `OrderListResponse` -- full order with nested `items` list, each containing nested `options`.
- `OrderItemResponse` -- `id`, `menu_item_id`, `name`, `unit_price`, `quantity`, `notes`, `options`.
- `OrderItemOptionResponse` -- `id`, `menu_item_option_id`, `label?`, `price_delta?`.
- `OrderStatusUpdate` -- `status: OrderStatus`.

### Kitchen

- `KitchenItemAdd` -- same shape as `OrderItemCreate`.
- `KitchenItemUpdate` -- `item_id`, `quantity?`, `notes?`.
- `KitchenOrderEdit` -- `notes?`, `items_to_add`, `items_to_update`, `items_to_remove` (list of UUIDs).

### Room

- `RoomCreate` -- `room_number`, `display_name?`.
- `RoomResponse` -- `id`, `room_number`, `display_name?`.

### Auth

- `OTPRequest` -- `phone` (7-20 chars).
- `OTPVerify` -- `phone`, `code` (exactly 6 chars), `name?` (1-128 chars).
- `StaffLogin` -- `email`, `password`.
- `AuthResponse` -- `access_token`, `token_type` (default "bearer"), `user: UserResponse`.
- `UserResponse` -- `id`, `name`, `phone?`, `email?`, `role`, `restaurant_id?`, `is_active`, `created_at`.

### Table

- `TableCreate` -- `restaurant_id`, `table_number` (1-32 chars), `capacity` (1-50).
- `TableUpdate` -- all fields optional.
- `TableResponse` -- `id`, `restaurant_id`, `table_number`, `capacity`, `is_active`.

### Reservation

- `ReservationCreate` -- `restaurant_id`, `table_id`, `reservation_date`, `reservation_time` (must be on the hour), `party_size` (1-50), `notes?`.
- `ReservationResponse` -- all fields plus `confirmation_code`, `user_name?`, `restaurant_name?`, `table_number?` (joined from related models).
- `ReservationStatusUpdate` -- `status: ReservationStatus`.
- `SlotsResponse` -- `slots: list[str]` (e.g. `["10:00", "11:00", ...]`), `booked: dict[str, list[UUID]]` (slot -> list of booked table IDs).

### Staff/Admin

- `StaffCreate` -- `name` (1-128 chars), `email` (5-255 chars), `password` (min 6 chars), `role`, `restaurant_id?`.
- `StaffUpdate` -- all fields optional.
- `StaffResponse` -- `id`, `name`, `email?`, `role`, `restaurant_id?`, `is_active`, `created_at`.

---

## 9. Setup and Development

### Prerequisites

- Python 3.11+
- PostgreSQL (running and accessible)

### Initial Setup

```bash
# 1. Clone the repository and navigate into it
cd restoback

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
# Edit .env and set DATABASE_URL, AES_ENCRYPTION_KEY, JWT_SECRET_KEY

# 5. Create the database in PostgreSQL
# e.g. createdb resto_db

# 6. Initialize tables and seed data
python -m scripts.init_db           # Create tables
python -m scripts.seed              # Seed restaurants, rooms, menus, tables, staff
python -m scripts.seed_orders       # Seed demo orders (optional)

# Or run all at once (drops and recreates everything):
python -m scripts.setup
```

### Running the Server

```bash
uvicorn app.main:app --reload
```

- API root: http://127.0.0.1:8000/
- Swagger UI (interactive docs): http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json
- Guest page: http://127.0.0.1:8000/room/101
- Kitchen display: http://127.0.0.1:8000/kitchen

### Database Scripts

| Command | Description |
|---|---|
| `python -m scripts.init_db` | Creates all tables (no-op if they exist). |
| `python -m scripts.reset_db` | Drops all tables and recreates them. **Destroys all data.** |
| `python -m scripts.seed` | Seeds rooms, restaurants, menu items (with options), tables, and staff accounts. |
| `python -m scripts.seed_orders` | Seeds demo orders. Pass `--clear` to delete existing orders first. |
| `python -m scripts.setup` | Runs reset_db, seed, and seed_orders in sequence. Full clean slate. |

### Seed Data

After running `python -m scripts.seed`, the database is populated with:

| Data | Details |
|---|---|
| Rooms | 40 rooms: 101-110, 201-210, 301-310, 401-410 |
| Restaurants | 7: Main Restaurant, Sushi Bar, Pool Grill, Rooftop Lounge, Breakfast & Co, The Steakhouse, Lobby Bar |
| Menu items | ~80 items across all restaurants, with options/add-ons on many items |
| Tables | 56 total (6-10 per restaurant, capacities of 2, 4, or 6) |
| Staff | 1 establishment admin + 7 restaurant admins + 7 supervisors |

#### Default Login Credentials

| Role | Email | Password |
|---|---|---|
| Establishment admin | `admin@hotel.com` | `admin123` |
| Restaurant admin (per restaurant) | `manager1@hotel.com` through `manager7@hotel.com` | `staff123` |
| Supervisor (per restaurant) | `host1@hotel.com` through `host7@hotel.com` | `staff123` |

Guest users are created dynamically via OTP verification (no pre-seeded guest accounts).

### Error Response Format

The API uses FastAPI's default error structure. All error responses return JSON:

```json
{
  "detail": "Human-readable error message"
}
```

Common HTTP status codes used:

| Code | Meaning |
|---|---|
| 400 | Validation error or business rule violation |
| 401 | Missing or invalid JWT token |
| 403 | Authenticated but insufficient role permissions |
| 404 | Resource not found |
| 409 | Conflict (e.g. duplicate room number, double-booked table) |
| 422 | Pydantic validation failure (automatic from FastAPI) |
| 503 | Database health check failure |

Pydantic validation errors (422) return a different structure with a `detail` array describing each field error.

---

## 10. Known Gaps and Future Work

These are areas that a new developer should be aware of:

| Area | Current State | Recommendation |
|---|---|---|
| **CORS** | No `CORSMiddleware` is configured. The HTML templates are served from the same origin so this works, but any separate frontend (e.g. React/Vue on a different port) will be blocked by the browser. | Add `CORSMiddleware` in `app/main.py` with appropriate `allow_origins`. |
| **Tests** | No test suite exists. No `pytest` configuration, no test files. | Add `pytest` + `httpx` (for `AsyncClient`) and write tests against the API endpoints. |
| **Migrations** | No Alembic or other migration tool. Schema changes require dropping and recreating all tables. | Add Alembic for incremental schema migrations once the schema stabilizes. |
| **Real-time updates** | Kitchen display uses polling (client-side `setInterval`). | Add WebSockets or Server-Sent Events for live order updates. |
| **OTP delivery** | OTP codes are returned in the API response and logged to the console. | Integrate an SMS provider (Twilio, etc.) for production. |
| **Staff email lookup** | Staff login scans and decrypts every staff user's email to find a match. | Add an `email_hash` blind index column to the `users` table (like `phone_hash`). |
| **Rate limiting** | No rate limiting on any endpoints, including OTP request and login. | Add middleware or dependency-based rate limiting. |
| **Logging** | Minimal logging (only OTP codes printed to console). | Add structured logging with a library like `structlog` or Python's `logging` module. |
| **Static files** | Templates are read from disk on every request via `Path.read_text()`. No caching or static file serving. | Consider using FastAPI's `StaticFiles` mount or adding template caching for production. |

### Key Design Decisions

- **No migration tool:** Schema changes are applied by dropping and recreating tables (`scripts/reset_db.py`). Consider adding Alembic if the schema stabilizes and production data must be preserved.
- **Soft deletes:** Staff users and tables use `is_active = False` instead of hard deletes. The `DELETE` endpoints for `/api/admin/staff/{id}` and `/api/tables/{id}` both perform soft deletes.
- **No WebSockets:** The kitchen display uses periodic polling. A future enhancement could add WebSockets or SSE for real-time order updates.
- **Demo-mode OTP:** The OTP code is returned in the API response and logged to the console. In production, this would be sent via SMS.
- **Staff email lookup:** Staff login decrypts all staff emails to find a match. For a larger staff set, add an `email_hash` blind index column (similar to `phone_hash`).
