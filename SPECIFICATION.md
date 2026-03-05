# White-Label Multi-Restaurant Ordering Platform -- Technical Specification

## 1. Overview

A white-label, multi-tenant backend and frontend for in-room ordering, kitchen display, and table reservations. Each client establishment operates on its own subdomain with isolated data, customisable branding, and independently selectable themes. A platform-level superadmin manages all establishments from a central dashboard.

Guests scan a QR code in their room, choose a restaurant, browse the menu, and place an order for delivery. Staff view incoming orders on a kitchen display and move them through a status pipeline. The system also supports table reservations with QR-code confirmation.

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
| Multi-tenancy | Subdomain-based routing via Starlette middleware |

---

## 2. Project Structure

```
resto/
├── .env.example              # Template for environment variables
├── .gitignore
├── README.md
├── SPECIFICATION.md           # This file
├── requirements.txt           # Python dependencies
│
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app, middleware registration, router registration
│   ├── config.py              # Settings loaded from .env via pydantic-settings
│   ├── database.py            # Async SQLAlchemy engine, session factory, get_db dependency
│   ├── models.py              # SQLAlchemy ORM models and enums
│   ├── schemas.py             # Pydantic request/response schemas
│   ├── auth.py                # JWT creation, auth dependencies (user, superadmin, role, establishment)
│   ├── encryption.py          # AES-256-GCM encrypt/decrypt, HMAC phone_hash
│   ├── middleware.py           # EstablishmentMiddleware: subdomain tenant resolution
│   │
│   └── routers/
│       ├── __init__.py
│       ├── auth.py            # OTP request/verify, staff login, superadmin login, /me
│       ├── restaurants.py     # Restaurant CRUD and menu listing (establishment-scoped)
│       ├── orders.py          # Order creation, listing, cancellation (establishment-scoped)
│       ├── kitchen.py         # Kitchen order list, status updates, order editing
│       ├── menu_items.py      # Menu item listing, update, delete
│       ├── rooms.py           # Room listing and creation (establishment-scoped)
│       ├── tables.py          # Table CRUD (role-protected)
│       ├── reservations.py    # Reservation CRUD, slots, confirm via QR, QR image
│       ├── admin.py           # Staff account management (establishment_admin only)
│       ├── branding.py        # Public branding GET, admin branding PATCH
│       ├── superadmin.py      # Establishment CRUD, seed admin, global stats
│       └── pages.py           # Serves HTML templates for all UIs
│
├── scripts/
│   ├── init_db.py             # Creates tables (optional --drop to drop first)
│   ├── reset_db.py            # Drops all tables, then recreates them
│   ├── seed.py                # Seeds establishment, rooms, restaurants, menus, tables, staff, superadmin
│   ├── seed_orders.py         # Seeds demo orders (supports --clear flag)
│   └── setup.py               # Runs reset_db + seed + seed_orders in sequence
│
├── static/
│   └── placeholder-logo.svg   # Default SVG logo placeholder
│
├── templates/
│   ├── room.html              # Guest ordering page (themed per establishment)
│   ├── kitchen.html           # Kitchen display page (themed per establishment)
│   ├── login.html             # Staff/guest login page
│   ├── reserve.html           # Table reservation page
│   ├── admin.html             # Establishment admin panel (includes Branding tab)
│   ├── scanner.html           # QR code scanner page
│   └── superadmin.html        # Platform superadmin dashboard
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
| `BASE_DOMAIN` | `str` | `"localhost"` | Base domain for subdomain extraction by the tenant middleware. |
| `SUPERADMIN_SUBDOMAIN` | `str` | `"manage"` | Subdomain reserved for the platform superadmin panel. |

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
| `UserRole` | `superadmin`, `normal_user`, `establishment_admin`, `restaurant_admin`, `supervisor` |
| `ReservationStatus` | `pending`, `confirmed`, `cancelled`, `completed`, `no_show` |

All enums extend both `str` and `enum.Enum`, so they serialize as strings in JSON responses.

### Models (`app/models.py`)

All primary keys are `UUID` with `default=uuid4`. Foreign keys use `ondelete="CASCADE"` unless noted. All models inherit from `Base` (SQLAlchemy `DeclarativeBase`).

#### Establishment (`establishments`)

The top-level tenant model. All data (restaurants, rooms, users) is scoped to an establishment.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `name` | String(255) | NOT NULL |
| `slug` | String(128) | UNIQUE, NOT NULL |
| `logo_url` | String(512) | nullable |
| `room_theme` | String(64) | NOT NULL, default `"noir-gold"` |
| `kitchen_theme` | String(64) | NOT NULL, default `"kds-classic"` |
| `custom_room_colors` | JSON | nullable |
| `custom_kitchen_colors` | JSON | nullable |
| `is_active` | Boolean | NOT NULL, default True |
| `created_at` | DateTime | default `utcnow()` |

Relationships: `restaurants`, `rooms`, `users`.

#### Restaurant (`restaurants`)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `establishment_id` | UUID | FK -> establishments.id (CASCADE), NOT NULL |
| `name` | String(255) | NOT NULL |
| `description` | Text | nullable |
| `image_url` | String(512) | nullable |
| `open_from` | Time | nullable |
| `open_until` | Time | nullable |

Relationships: `establishment`, `menu_items`, `orders`, `tables`, `reservations`.

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
| `establishment_id` | UUID | FK -> establishments.id (CASCADE), NOT NULL |
| `room_number` | String(32) | NOT NULL |
| `display_name` | String(128) | nullable |

Composite unique constraint: `(establishment_id, room_number)`. Orders reference rooms by `room_id` string, not by FK.

Relationships: `establishment`.

#### User (`users`)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `establishment_id` | UUID | FK -> establishments.id (CASCADE), nullable |
| `encrypted_name` | Text | NOT NULL (AES-256-GCM encrypted) |
| `encrypted_phone` | Text | nullable (AES-256-GCM encrypted) |
| `phone_hash` | String(64) | UNIQUE, nullable (HMAC-SHA256 blind index) |
| `encrypted_email` | Text | nullable (AES-256-GCM encrypted) |
| `password_hash` | String(255) | nullable (bcrypt hash, staff only) |
| `role` | Enum(UserRole) | NOT NULL, default `normal_user` |
| `restaurant_id` | UUID | FK -> restaurants.id (SET NULL), nullable |
| `is_active` | Boolean | NOT NULL, default True |
| `created_at` | DateTime | default `utcnow()` |

`establishment_id` is nullable because superadmin users are not tied to any establishment.

Relationships: `establishment`, `reservations`.

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
    Establishment ||--o{ Restaurant : "has"
    Establishment ||--o{ Room : "has"
    Establishment ||--o{ UserEntity : "has"

    Restaurant ||--o{ MenuItem : "has"
    Restaurant ||--o{ OrderEntity : "receives"
    Restaurant ||--o{ TableEntity : "has"
    Restaurant ||--o{ Reservation : "has"

    MenuItem ||--o{ MenuItemOption : "has"
    MenuItem ||--o{ OrderItem : "referenced by"

    OrderEntity ||--o{ OrderItem : "contains"
    OrderItem ||--o{ OrderItemOption : "has"
    OrderItemOption }o--|| MenuItemOption : "references"

    UserEntity ||--o{ Reservation : "makes"
    TableEntity ||--o{ Reservation : "booked for"

    Establishment {
        UUID id PK
        string name
        string slug
        string logo_url
        string room_theme
        string kitchen_theme
        json custom_room_colors
        json custom_kitchen_colors
        boolean is_active
        datetime created_at
    }

    Restaurant {
        UUID id PK
        UUID establishment_id FK
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

    OrderEntity {
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
        UUID establishment_id FK
        string room_number
        string display_name
    }

    UserEntity {
        UUID id PK
        UUID establishment_id FK
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

## 5. Multi-Tenancy Architecture

### Subdomain-Based Routing

Each establishment is identified by a unique `slug` and accessed via a subdomain:

```
https://<slug>.<BASE_DOMAIN>/
```

Examples:
- `grand-hotel.example.com` -- the "Grand Hotel" establishment
- `seaside-resort.example.com` -- the "Seaside Resort" establishment
- `manage.example.com` -- the superadmin panel

### Middleware (`app/middleware.py`)

The `EstablishmentMiddleware` (Starlette `BaseHTTPMiddleware`) runs on every request and:

1. **Skips** infrastructure paths: `/health`, `/docs`, `/openapi.json`, `/redoc`.
2. **Checks for a dev override**: if the `X-Establishment-Slug` header is present, uses its value as the slug (for local development without real subdomains).
3. **Extracts the subdomain** from the `Host` header by stripping the `BASE_DOMAIN` and taking the first subdomain segment.
4. **Resolves the slug**:
   - If it matches `SUPERADMIN_SUBDOMAIN` (default: `manage`), sets `request.state.is_superadmin_panel = True`.
   - If it is `www` or empty, passes through without tenant context.
   - Otherwise, queries the database for an `Establishment` with that slug.
5. **Sets request state**:
   - `request.state.establishment` -- the full `Establishment` ORM object (or `None`).
   - `request.state.establishment_id` -- the UUID (or `None`).
   - `request.state.is_superadmin_panel` -- boolean.
6. **Returns 404** if the slug does not match any establishment, or **403** if the establishment is inactive.

### Data Isolation

All data-access endpoints use the `get_establishment_id(request)` dependency to extract the tenant UUID from `request.state` and filter queries accordingly. This ensures that:

- A restaurant created under Establishment A is invisible to requests on Establishment B's subdomain.
- Room numbers are unique per establishment (composite unique constraint).
- Staff users belong to a specific establishment via `establishment_id` FK.
- Superadmin users have `establishment_id = NULL` and are not tied to any tenant.

### Local Development

Since real subdomains require DNS configuration, development offers two approaches:

1. **Header fallback**: Send an `X-Establishment-Slug: grand-hotel` header with requests. The middleware treats this as the subdomain.
2. **Hosts file**: Add entries like `127.0.0.1 grand-hotel.localhost` to the system hosts file, then access `http://grand-hotel.localhost:8000/`.

---

## 6. Authentication and Authorization

Implemented in `app/auth.py` and `app/routers/auth.py`.

### Mechanisms

1. **OTP (guests):** A guest submits their phone number to `POST /api/auth/otp/request`, receives a 6-digit code (logged to console and returned in the response for demo purposes). They verify it via `POST /api/auth/otp/verify`, which finds or creates a `User` record and returns a JWT.

2. **Email + password (staff):** Staff accounts are created by an `establishment_admin` via `POST /api/admin/staff` with a bcrypt-hashed password. Staff log in via `POST /api/auth/login`. The system decrypts every staff user's email to find a match (acceptable for the small staff set; for scale, add an `email_hash` column).

3. **Email + password (superadmin):** Superadmin users log in via `POST /api/auth/superadmin-login`, which searches specifically for users with the `superadmin` role.

4. **JWT tokens:** Signed with HS256 using `JWT_SECRET_KEY`. The payload contains:
   - `sub` -- user UUID
   - `role` -- user role string
   - `exp` -- expiration timestamp
   - `eid` -- establishment UUID (if the user belongs to an establishment)
   - `rid` -- restaurant UUID (if the user is scoped to a specific restaurant)

   Default expiry is 24 hours. Tokens are sent in the `Authorization: Bearer <token>` header.

### Roles

| Role | Scope | Description |
|---|---|---|
| `superadmin` | Platform-wide | Platform operator. Manages all establishments. Not tied to any establishment. Bypasses all role checks. |
| `establishment_admin` | Per-establishment | Client admin. Manages staff, restaurants, branding, tables, and reservations for their establishment. |
| `restaurant_admin` | Per-restaurant | Manages a single restaurant. Can manage tables and reservations for their restaurant. |
| `supervisor` | Per-restaurant | Restaurant floor staff. Can confirm reservations and update reservation status. |
| `normal_user` | Per-establishment | Guests. Created via OTP. Can make reservations and view their own. |

### FastAPI Dependencies

| Dependency | Behavior |
|---|---|
| `get_current_user` | Decodes JWT from `Authorization` header. Returns `User` or raises 401. |
| `get_optional_user` | Same as above but returns `None` instead of raising 401 when no token is present. |
| `get_current_superadmin` | Wraps `get_current_user`. Returns the user if their role is `superadmin`, otherwise raises 403. |
| `require_role(*roles)` | Factory. Returns the user if their role is in `roles`. Superadmins always pass. Otherwise raises 403. |
| `get_establishment_id(request)` | Reads `request.state.establishment_id` set by the middleware. Raises 400 if missing. |

### Auth Requirements by Router

| Router | Auth |
|---|---|
| `restaurants`, `orders`, `kitchen`, `menu_items`, `rooms`, `pages` | None (public) |
| `tables` | `require_role(establishment_admin, restaurant_admin)` |
| `reservations` | Mixed: `/slots` is public; CRUD requires `get_current_user`; confirm/status-update requires staff roles |
| `admin` | `require_role(establishment_admin)` |
| `branding` | GET is public; PATCH requires `require_role(establishment_admin)` |
| `superadmin` | `get_current_superadmin` on all endpoints |
| `auth` | Only `GET /me` requires `get_current_user` |

---

## 7. Encryption and Security (`app/encryption.py`)

PII fields (name, phone, email) are never stored in plaintext. The module provides three functions:

| Function | Purpose |
|---|---|
| `encrypt(plaintext) -> str` | AES-256-GCM encryption. Generates a random 12-byte nonce, encrypts, and returns `base64(nonce \|\| ciphertext \|\| tag)`. |
| `decrypt(token) -> str` | Reverses the above. Splits the base64-decoded bytes into nonce (first 12 bytes) and ciphertext+tag (rest), then decrypts. |
| `phone_hash(phone) -> str` | HMAC-SHA256 blind index using the AES key. Returns a 64-char hex digest. Used to look up users by phone number without decrypting every record. |

Password hashing uses bcrypt via `passlib.context.CryptContext`.

---

## 8. Theming System

### Overview

The platform supports per-establishment theming for both the guest-facing room view and the kitchen display. Themes are applied client-side via CSS custom properties (`:root` variables) set by JavaScript on page load.

### Room Themes (5 presets + custom)

| Theme ID | Style |
|---|---|
| `noir-gold` | Dark background with gold accents (default) |
| `ivory-elegance` | Light cream/ivory with warm tones |
| `midnight-blue` | Deep blue with silver accents |
| `clean-minimal` | White background with minimal grey/black |
| `emerald-dark` | Dark background with emerald green accents |
| `custom` | Uses colors from `custom_room_colors` JSON |

### Kitchen Themes (4 presets + custom)

| Theme ID | Style |
|---|---|
| `kds-classic` | Dark theme optimised for kitchen display (default) |
| `kds-bright` | Light, high-contrast for well-lit kitchens |
| `kds-midnight` | Very dark with blue tones |
| `kds-paper` | Paper-like light background |
| `custom` | Uses colors from `custom_kitchen_colors` JSON |

### How Themes Are Applied

1. Each HTML template defines the full set of theme presets as a JavaScript object mapping theme IDs to CSS variable key-value pairs.
2. On page load, the frontend calls `GET /api/branding` to fetch the establishment's selected theme and any custom colors.
3. JavaScript iterates over the selected theme's variables and applies them to `document.documentElement.style`, overriding the `:root` defaults.
4. If the theme is `custom`, the variables from `custom_room_colors` or `custom_kitchen_colors` (stored as JSON in the `Establishment` record) are applied instead.

### Branding

Each establishment can configure:
- **Name** -- displayed in page headers and titles.
- **Logo URL** -- shown in headers; falls back to `static/placeholder-logo.svg`.
- **Room theme** and **kitchen theme** -- independently selectable.
- **Custom color palettes** -- JSON objects with CSS variable overrides for `custom` themes.

All configuration is managed via the Branding tab in the admin dashboard or the `/api/branding` PATCH endpoint.

---

## 9. API Reference

All API routes are prefixed with `/api` except the HTML page routes. The app is created in `app/main.py` and registers routers in this order: restaurants, orders, kitchen, menu_items, rooms, auth, tables, reservations, admin, branding, superadmin, pages.

All data endpoints (restaurants, orders, rooms, kitchen, tables, reservations, menu_items, admin) filter queries by `establishment_id` extracted from the request state, ensuring complete data isolation between tenants.

### Root Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/` | None | Returns JSON with links to docs. |
| `GET` | `/health` | None | Runs `SELECT 1` against the database. Returns `{"status": "ok"}` or 503 `{"status": "unhealthy"}`. |

### 9.1 Auth (`/api/auth`)

| Method | Path | Auth | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/otp/request` | None | `OTPRequest { phone }` | `{ message, expires_in_seconds, demo_code }` |
| `POST` | `/otp/verify` | None | `OTPVerify { phone, code, name? }` | `AuthResponse { access_token, token_type, user }` |
| `POST` | `/login` | None | `StaffLogin { email, password }` | `AuthResponse` |
| `POST` | `/superadmin-login` | None | `StaffLogin { email, password }` | `AuthResponse` |
| `GET` | `/me` | JWT | -- | `UserResponse` |

**Notes:**
- OTP verify finds or creates a `User`. If the phone hash matches an existing user, it reuses that user. If `name` is provided, it updates the user's encrypted name.
- Staff login iterates over all active staff users (excluding superadmins) and decrypts their email to find a match, then verifies the bcrypt password hash. Scoped to the current establishment.
- Superadmin login searches only for users with the `superadmin` role.

### 9.2 Restaurants (`/api/restaurants`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `` | None | -- | `list[RestaurantResponse]` |
| `POST` | `` | None | `RestaurantCreate { name, description?, image_url?, open_from?, open_until? }` | `RestaurantResponse` |
| `GET` | `/{restaurant_id}` | None | -- | `RestaurantResponse` |
| `PATCH` | `/{restaurant_id}` | None | `RestaurantUpdate` (all fields optional) | `RestaurantResponse` |
| `GET` | `/{restaurant_id}/menu` | None | -- | `list[MenuItemResponse]` (ordered by category, name; includes options) |
| `POST` | `/{restaurant_id}/menu-items` | None | `MenuItemCreate` | `MenuItemResponse` |

All queries are filtered by the current establishment.

### 9.3 Orders (`/api/orders`)

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

### 9.4 Kitchen (`/api/kitchen`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `/orders` | None | Query: `restaurant_id` (required) | `list[OrderListResponse]` (excludes cancelled, newest first) |
| `PATCH` | `/orders/{order_id}` | None | `OrderStatusUpdate { status }` | `OrderListResponse` |
| `PUT` | `/orders/{order_id}/edit` | None | `KitchenOrderEdit { notes?, items_to_add, items_to_update, items_to_remove }` | `OrderListResponse` |

**Notes:**
- Kitchen edit supports adding new items (with options), updating quantity/notes on existing items, and removing items -- all in a single request. The subtotal is recalculated after every edit.
- Cannot edit cancelled or served orders.

### 9.5 Menu Items (`/api/menu-items`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `` | None | Query: `restaurant_id?` | `list[MenuItemResponse]` (ordered by category, name; includes options) |
| `PATCH` | `/{menu_item_id}` | None | `MenuItemUpdate` (all fields optional) | `MenuItemResponse` |
| `DELETE` | `/{menu_item_id}` | None | -- | 204 No Content |

### 9.6 Rooms (`/api/rooms`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `` | None | -- | `list[RoomResponse]` (ordered by room_number) |
| `GET` | `/{room_id}` | None | -- (room_id is the room_number string) | `RoomResponse` |
| `POST` | `` | None | `RoomCreate { room_number, display_name? }` | `RoomResponse` (409 if room_number already exists for this establishment) |

### 9.7 Tables (`/api/tables`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `` | None | Query: `restaurant_id` (required), `active_only?` (default true) | `list[TableResponse]` |
| `POST` | `` | `establishment_admin` or `restaurant_admin` | `TableCreate { restaurant_id, table_number, capacity }` | `TableResponse` (201) |
| `PATCH` | `/{table_id}` | `establishment_admin` or `restaurant_admin` | `TableUpdate { table_number?, capacity?, is_active? }` | `TableResponse` |
| `DELETE` | `/{table_id}` | `establishment_admin` or `restaurant_admin` | -- | 204 (soft-delete: sets `is_active = False`) |

**Notes:**
- `restaurant_admin` users can only manage tables belonging to their own restaurant (enforced by comparing `user.restaurant_id` against the table's `restaurant_id`).

### 9.8 Reservations (`/api/reservations`)

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

### 9.9 Admin (`/api/admin`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `POST` | `/staff` | `establishment_admin` | `StaffCreate { name, email, password, role, restaurant_id? }` | `StaffResponse` (201) |
| `GET` | `/staff` | `establishment_admin` | -- | `list[StaffResponse]` (all staff for this establishment, ordered by created_at) |
| `PATCH` | `/staff/{user_id}` | `establishment_admin` | `StaffUpdate { name?, email?, role?, restaurant_id?, is_active? }` | `StaffResponse` |
| `DELETE` | `/staff/{user_id}` | `establishment_admin` | -- | 204 (soft-delete: sets `is_active = False`) |

**Notes:**
- Cannot create users with `normal_user` role through this endpoint (those are created via OTP).
- Staff passwords are hashed with bcrypt on creation. Name and email are AES-encrypted.
- All queries are scoped to the current establishment.

### 9.10 Branding (`/api/branding`)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `` | None | -- | `BrandingResponse { name, logo_url, room_theme, kitchen_theme, custom_room_colors, custom_kitchen_colors }` |
| `PATCH` | `` | `establishment_admin` | `BrandingUpdate` (all fields optional) | `BrandingResponse` |

**Notes:**
- GET returns the branding for the establishment resolved from the current subdomain/header.
- PATCH validates theme IDs against allowed values. Valid room themes: `noir-gold`, `ivory-elegance`, `midnight-blue`, `clean-minimal`, `emerald-dark`, `custom`. Valid kitchen themes: `kds-classic`, `kds-bright`, `kds-midnight`, `kds-paper`, `custom`.
- Superadmins can update any establishment's branding. Establishment admins can only update their own.

### 9.11 Superadmin (`/api/superadmin`)

All endpoints require `get_current_superadmin` authentication.

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `/establishments` | Superadmin | -- | `list[EstablishmentResponse]` (newest first) |
| `POST` | `/establishments` | Superadmin | `EstablishmentCreate { name, slug }` | `EstablishmentResponse` (201) |
| `GET` | `/establishments/{est_id}` | Superadmin | -- | `EstablishmentResponse` |
| `PATCH` | `/establishments/{est_id}` | Superadmin | `EstablishmentUpdate { name?, slug?, is_active? }` | `EstablishmentResponse` |
| `POST` | `/establishments/{est_id}/seed-admin` | Superadmin | `SeedAdminCreate { name, email, password }` | `StaffResponse` (201) |
| `GET` | `/stats` | Superadmin | -- | `EstablishmentStats { total_establishments, active_establishments, total_orders, total_restaurants }` |

**Notes:**
- `slug` must match the pattern `^[a-z0-9][a-z0-9\-]*[a-z0-9]$` and must be unique.
- `seed-admin` creates an `establishment_admin` user tied to the specified establishment.
- Activating/deactivating an establishment controls whether its subdomain is accessible (inactive establishments return 403).

### 9.12 HTML Pages (no `/api` prefix)

| Method | Path | Template | Description |
|---|---|---|---|
| `GET` | `/room/{room_id}` | `room.html` | Guest ordering page |
| `GET` | `/kitchen` | `kitchen.html` | Kitchen display |
| `GET` | `/login` | `login.html` | Staff/guest login |
| `GET` | `/reserve` | `reserve.html` | Table reservation |
| `GET` | `/admin` | `admin.html` | Establishment admin dashboard |
| `GET` | `/scanner` | `scanner.html` | QR code scanner |
| `GET` | `/superadmin` | `superadmin.html` | Platform superadmin dashboard |

Templates are read from `templates/` at the project root. The pages router reads the HTML file from disk and returns it as an `HTMLResponse`. All templates load branding (logo, name, theme) dynamically via `GET /api/branding` on page load.

---

## 10. Pydantic Schemas (`app/schemas.py`)

All response schemas use `model_config = {"from_attributes": True}` for ORM compatibility. Key schemas by domain:

### Establishment

- `EstablishmentCreate` -- `name` (required), `slug` (required, pattern: `^[a-z0-9][a-z0-9\-]*[a-z0-9]$`).
- `EstablishmentUpdate` -- optional `name`, `slug`, `is_active`.
- `EstablishmentResponse` -- `id`, `name`, `slug`, `logo_url`, `room_theme`, `kitchen_theme`, `is_active`, `created_at`.
- `EstablishmentStats` -- `total_establishments`, `active_establishments`, `total_orders`, `total_restaurants`.

### Branding

- `BrandingResponse` -- `name`, `logo_url`, `room_theme`, `kitchen_theme`, `custom_room_colors`, `custom_kitchen_colors`.
- `BrandingUpdate` -- all fields optional: `name`, `logo_url`, `room_theme`, `kitchen_theme`, `custom_room_colors`, `custom_kitchen_colors`.

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
- `UserResponse` -- `id`, `name`, `phone?`, `email?`, `role`, `establishment_id?`, `restaurant_id?`, `is_active`, `created_at`.

### Table

- `TableCreate` -- `restaurant_id`, `table_number` (1-32 chars), `capacity` (1-50).
- `TableUpdate` -- all fields optional.
- `TableResponse` -- `id`, `restaurant_id`, `table_number`, `capacity`, `is_active`.

### Reservation

- `ReservationCreate` -- `restaurant_id`, `table_id`, `reservation_date`, `reservation_time` (must be on the hour), `party_size` (1-50), `notes?`.
- `ReservationResponse` -- all fields plus `confirmation_code`, `user_name?`, `restaurant_name?`, `table_number?` (joined from related models).
- `ReservationStatusUpdate` -- `status: ReservationStatus`.
- `SlotsResponse` -- `slots: list[str]` (e.g. `["10:00", "11:00", ...]`), `booked: dict[str, list[UUID]]` (slot -> list of booked table IDs).

### Staff / Admin

- `StaffCreate` -- `name` (1-128 chars), `email` (5-255 chars), `password` (min 6 chars), `role`, `restaurant_id?`.
- `StaffUpdate` -- all fields optional.
- `StaffResponse` -- `id`, `name`, `email?`, `role`, `establishment_id?`, `restaurant_id?`, `is_active`, `created_at`.

### Superadmin

- `SeedAdminCreate` -- `name` (1-128 chars), `email` (5-255 chars), `password` (min 6 chars). Used to create an initial `establishment_admin` for a new establishment.

---

## 11. Setup and Development

### Prerequisites

- Python 3.11+
- PostgreSQL (running and accessible)

### Initial Setup

```bash
# 1. Clone the repository and navigate into it
cd resto

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
# Edit .env and set DATABASE_URL, AES_ENCRYPTION_KEY, JWT_SECRET_KEY, BASE_DOMAIN

# 5. Create the database in PostgreSQL
# e.g. createdb resto_db

# 6. Initialize tables and seed data
python -m scripts.init_db           # Create tables
python -m scripts.seed              # Seed establishment, restaurants, rooms, menus, tables, staff, superadmin
python -m scripts.seed_orders       # Seed demo orders (optional)

# Or run all at once (drops and recreates everything):
python -m scripts.setup
```

If you change the database schema (models), use `--drop` to drop and recreate tables:

```bash
python -m scripts.init_db --drop
python -m scripts.seed
```

### Running the Server

```bash
uvicorn app.main:app --reload
```

- API root: http://127.0.0.1:8000/
- Swagger UI (interactive docs): http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

### Accessing Establishments Locally

Since multi-tenancy is subdomain-based, local development requires one of:

**Option 1 -- HTTP header (simplest):**

Use a tool like curl, Postman, or a browser extension to add the `X-Establishment-Slug` header:

```bash
curl -H "X-Establishment-Slug: grand-hotel" http://localhost:8000/api/restaurants
```

**Option 2 -- Hosts file:**

Add entries to your system hosts file (`C:\Windows\System32\drivers\etc\hosts` on Windows, `/etc/hosts` on macOS/Linux):

```
127.0.0.1  grand-hotel.localhost
127.0.0.1  manage.localhost
```

Then access:
- Guest page: http://grand-hotel.localhost:8000/room/101
- Kitchen: http://grand-hotel.localhost:8000/kitchen
- Admin: http://grand-hotel.localhost:8000/admin
- Superadmin: http://manage.localhost:8000/superadmin

### Database Scripts

| Command | Description |
|---|---|
| `python -m scripts.init_db` | Creates all tables (no-op if they exist). |
| `python -m scripts.init_db --drop` | Drops all tables and recreates them. **Destroys all data.** |
| `python -m scripts.reset_db` | Drops all tables and recreates them. **Destroys all data.** |
| `python -m scripts.seed` | Seeds default establishment, rooms, restaurants, menu items, tables, staff, and superadmin. |
| `python -m scripts.seed_orders` | Seeds demo orders. Pass `--clear` to delete existing orders first. |
| `python -m scripts.setup` | Runs reset_db, seed, and seed_orders in sequence. Full clean slate. |

### Seed Data

After running `python -m scripts.seed`, the database is populated with:

| Data | Details |
|---|---|
| Establishments | 1: "Grand Hotel" (slug: `grand-hotel`) |
| Rooms | 40 rooms: 101-110, 201-210, 301-310, 401-410 |
| Restaurants | 7: Main Restaurant, Sushi Bar, Pool Grill, Rooftop Lounge, Breakfast & Co, The Steakhouse, Lobby Bar |
| Menu items | ~80 items across all restaurants, with options/add-ons on many items |
| Tables | 56 total (6-10 per restaurant, capacities of 2, 4, or 6) |
| Staff | 1 superadmin + 1 establishment admin + 7 restaurant admins + 7 supervisors |

#### Default Login Credentials

| Role | Email | Password |
|---|---|---|
| Superadmin | `super@platform.com` | `super123` |
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
| 403 | Authenticated but insufficient role permissions, or establishment is inactive |
| 404 | Resource not found, or establishment slug not recognised |
| 409 | Conflict (e.g. duplicate room number, duplicate slug, double-booked table) |
| 422 | Pydantic validation failure (automatic from FastAPI) |
| 503 | Database health check failure |

Pydantic validation errors (422) return a different structure with a `detail` array describing each field error.

---

## 12. Known Gaps and Future Work

| Area | Current State | Recommendation |
|---|---|---|
| **CORS** | No `CORSMiddleware` is configured. Works because HTML templates are served from the same origin. | Add `CORSMiddleware` in `app/main.py` if a separate frontend is introduced. |
| **Tests** | No test suite exists. | Add `pytest` + `httpx` (for `AsyncClient`) and write tests against the API endpoints. |
| **Migrations** | No Alembic or other migration tool. Schema changes require dropping and recreating all tables. | Add Alembic for incremental schema migrations once the schema stabilises. |
| **Real-time updates** | Kitchen display uses polling (client-side `setInterval`). | Add WebSockets or Server-Sent Events for live order updates. |
| **OTP delivery** | OTP codes are returned in the API response and logged to the console. | Integrate an SMS provider (Twilio, etc.) for production. |
| **Staff email lookup** | Staff login scans and decrypts every staff user's email to find a match. | Add an `email_hash` blind index column to the `users` table (like `phone_hash`). |
| **Rate limiting** | No rate limiting on any endpoints, including OTP request and login. | Add middleware or dependency-based rate limiting. |
| **Logging** | Minimal logging (only OTP codes printed to console). | Add structured logging with a library like `structlog` or Python's `logging` module. |
| **Static files** | Templates are read from disk on every request via `Path.read_text()`. No caching. | Use FastAPI's `StaticFiles` mount or add template caching for production. |
| **Docker** | No containerisation. | Add `Dockerfile` and `docker-compose.yml` for consistent deployment. |
| **HTTPS** | No TLS configuration. Subdomains in production require a wildcard SSL certificate. | Configure a reverse proxy (nginx, Caddy) with `*.yourdomain.com` certificate. |

### Key Design Decisions

- **Subdomain multi-tenancy:** Each establishment is accessed via its own subdomain. This provides clean URL separation, easy per-tenant branding, and potential for CDN/reverse-proxy-level routing. The `X-Establishment-Slug` header fallback allows development without DNS configuration.
- **Client-side theming:** Themes are applied via JavaScript + CSS custom properties rather than server-side template rendering. This keeps the backend simple (serving static HTML) while allowing real-time theme preview in the admin UI.
- **No migration tool:** Schema changes are applied by dropping and recreating tables. Alembic should be added before production deployment to preserve data across schema changes.
- **Soft deletes:** Staff users and tables use `is_active = False` instead of hard deletes. The `DELETE` endpoints for staff and tables both perform soft deletes.
- **No WebSockets:** The kitchen display uses periodic polling. A future enhancement could add WebSockets or SSE for real-time order updates.
- **Demo-mode OTP:** The OTP code is returned in the API response and logged to the console. In production, this would be sent via SMS.
- **Staff email lookup:** Staff login decrypts all staff emails to find a match. For a larger staff set, add an `email_hash` blind index column (similar to `phone_hash`).
- **Nullable establishment_id on User:** Superadmin users are not tied to any establishment, so `establishment_id` is nullable on the `users` table.
