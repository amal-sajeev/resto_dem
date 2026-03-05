# Resto -- White-Label Multi-Restaurant Ordering Platform

A multi-tenant, white-label platform for in-room food ordering, kitchen display, and table reservations. Each client establishment runs on its own subdomain with isolated data, customisable branding, and independently selectable themes -- all managed from a central superadmin dashboard.

Built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.x** (async), and vanilla **HTML/CSS/JS** frontends.

---

## Features

- **Multi-tenancy** -- Subdomain-based tenant isolation. Each establishment gets its own data, staff, and configuration.
- **Theming** -- 5 room themes, 4 kitchen themes, plus fully custom colour palettes. Room and kitchen themes are independently selectable per establishment.
- **Branding** -- Per-establishment name, logo, and colour scheme applied across all pages.
- **QR-based ordering** -- Guests scan a QR code in their room, browse restaurant menus, and place orders.
- **Kitchen display** -- Real-time order board with status pipeline (received, preparing, ready, served). Supports inline order editing.
- **Table reservations** -- Slot-based booking with QR code confirmation.
- **Role-based access** -- Five roles: superadmin, establishment admin, restaurant admin, supervisor, and guest.
- **PII encryption** -- Guest names, phone numbers, and emails are encrypted at rest with AES-256-GCM. Phone lookup uses HMAC-SHA256 blind index.
- **Platform management** -- Superadmin dashboard for creating establishments, seeding admins, toggling activation, and viewing global stats.

---

## Architecture

```mermaid
flowchart LR
    Browser --> SubdomainMW["Establishment Middleware"]
    SubdomainMW -->|"slug lookup"| DB[(PostgreSQL)]
    SubdomainMW --> Router["FastAPI Routers"]
    Router -->|"scoped by establishment_id"| DB
    SuperadminUI["Superadmin Panel\n(manage.domain)"] --> SuperadminAPI["Superadmin Router"]
    SuperadminAPI --> DB
```

Each HTTP request passes through the `EstablishmentMiddleware`, which extracts the tenant slug from the subdomain (or `X-Establishment-Slug` header for development). The middleware resolves the slug to an `Establishment` record and injects the `establishment_id` into the request state. All downstream routers filter queries by this ID, ensuring complete data isolation.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI 0.109+ |
| ASGI server | Uvicorn |
| Database | PostgreSQL (async via asyncpg) |
| ORM | SQLAlchemy 2.x (async sessions) |
| Validation | Pydantic v2, pydantic-settings |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Encryption | AES-256-GCM (cryptography) |
| QR codes | qrcode + Pillow |
| Frontend | Vanilla HTML / CSS / JavaScript |

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (running and accessible)

### Setup

```bash
# Clone and enter the project
cd resto

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env        # Windows (or cp on macOS/Linux)
# Edit .env -- set DATABASE_URL, AES_ENCRYPTION_KEY, JWT_SECRET_KEY

# Create the PostgreSQL database
# e.g. createdb resto_db

# Initialise tables and seed data
python -m scripts.init_db
python -m scripts.seed
python -m scripts.seed_orders       # optional: demo orders

# Start the server
uvicorn app.main:app --reload
```

The API is now running at **http://127.0.0.1:8000/**. Interactive docs are at **/docs**.

---

## Local Development with Subdomains

Since multi-tenancy is subdomain-based, local development requires tenant context. Two options:

### Option 1 -- HTTP header (simplest)

Add the `X-Establishment-Slug` header to your requests:

```bash
curl -H "X-Establishment-Slug: grand-hotel" http://localhost:8000/api/restaurants
```

For browser-based pages, use a browser extension that injects custom headers.

### Option 2 -- Hosts file

Add entries to your system hosts file:

| OS | File |
|---|---|
| Windows | `C:\Windows\System32\drivers\etc\hosts` |
| macOS / Linux | `/etc/hosts` |

```
127.0.0.1  grand-hotel.localhost
127.0.0.1  manage.localhost
```

Then access:

| Page | URL |
|---|---|
| Guest ordering | http://grand-hotel.localhost:8000/room/101 |
| Kitchen display | http://grand-hotel.localhost:8000/kitchen |
| Admin dashboard | http://grand-hotel.localhost:8000/admin |
| Login | http://grand-hotel.localhost:8000/login |
| Superadmin | http://manage.localhost:8000/superadmin |

---

## Default Credentials

After running `python -m scripts.seed`:

| Role | Email | Password |
|---|---|---|
| Superadmin | `super@platform.com` | `super123` |
| Establishment admin | `admin@hotel.com` | `admin123` |
| Restaurant admin | `manager1@hotel.com` -- `manager7@hotel.com` | `staff123` |
| Supervisor | `host1@hotel.com` -- `host7@hotel.com` | `staff123` |

Guest users are created dynamically via OTP phone verification.

---

## Project Structure

```
resto/
├── app/
│   ├── main.py              # FastAPI app, middleware, router registration
│   ├── config.py            # Settings (pydantic-settings)
│   ├── database.py          # Async engine, session factory
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # JWT, auth dependencies
│   ├── encryption.py        # AES-256-GCM, HMAC
│   ├── middleware.py         # Subdomain tenant middleware
│   └── routers/
│       ├── auth.py           # OTP, staff login, superadmin login
│       ├── restaurants.py    # Restaurant CRUD
│       ├── orders.py         # Order CRUD
│       ├── kitchen.py        # Kitchen display API
│       ├── menu_items.py     # Menu item CRUD
│       ├── rooms.py          # Room CRUD
│       ├── tables.py         # Table CRUD
│       ├── reservations.py   # Reservations, slots, QR
│       ├── admin.py          # Staff management
│       ├── branding.py       # Theme & branding API
│       ├── superadmin.py     # Establishment management
│       └── pages.py          # HTML page serving
├── templates/                # Frontend HTML pages
├── static/                   # Static assets (placeholder logo)
├── scripts/                  # DB init, seed, and setup scripts
├── requirements.txt
├── .env.example
└── SPECIFICATION.md          # Full technical specification
```

---

## API Overview

Full API reference is in [SPECIFICATION.md](SPECIFICATION.md). Summary of endpoint groups:

| Prefix | Description | Auth |
|---|---|---|
| `GET /health` | Database health check | None |
| `/api/auth` | OTP login, staff login, superadmin login, `/me` | Mixed |
| `/api/restaurants` | Restaurant CRUD, menu listing | None |
| `/api/orders` | Order creation, listing, cancellation | None |
| `/api/kitchen` | Kitchen order board, status updates, order editing | None |
| `/api/menu-items` | Menu item listing, update, delete | None |
| `/api/rooms` | Room listing and creation | None |
| `/api/tables` | Table CRUD | Staff roles |
| `/api/reservations` | Reservations, time slots, QR confirmation | Mixed |
| `/api/admin` | Staff account management | Establishment admin |
| `/api/branding` | Theme and branding configuration | GET: None, PATCH: Admin |
| `/api/superadmin` | Establishment CRUD, global stats, seed admin | Superadmin |

All data endpoints are automatically scoped to the current establishment via the tenant middleware.

### HTML Pages

| Path | Description |
|---|---|
| `/room/{room_id}` | Guest ordering page |
| `/kitchen` | Kitchen display |
| `/login` | Staff and guest login |
| `/reserve` | Table reservations |
| `/admin` | Establishment admin dashboard |
| `/scanner` | QR code scanner |
| `/superadmin` | Platform superadmin dashboard |

---

## Theming

Each establishment can independently select themes for the room (guest) view and kitchen display.

**Room themes:** `noir-gold` (default), `ivory-elegance`, `midnight-blue`, `clean-minimal`, `emerald-dark`, `custom`

**Kitchen themes:** `kds-classic` (default), `kds-bright`, `kds-midnight`, `kds-paper`, `custom`

The `custom` option allows an establishment admin to define a manual colour palette via the Branding tab in the admin dashboard. Themes are applied client-side using CSS custom properties.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:password@localhost:5432/resto_db` | PostgreSQL connection string |
| `AES_ENCRYPTION_KEY` | `"0" * 64` | 32-byte hex key for PII encryption |
| `JWT_SECRET_KEY` | `change-me-in-production` | JWT signing secret |
| `JWT_EXPIRY_MINUTES` | `1440` | Token lifetime (24 hours) |
| `OTP_EXPIRY_MINUTES` | `5` | OTP code validity |
| `BASE_DOMAIN` | `localhost` | Base domain for subdomain extraction |
| `SUPERADMIN_SUBDOMAIN` | `manage` | Subdomain for superadmin panel |

Copy `.env.example` to `.env` and update the values. Generate secure keys with:

```bash
python -c "import os; print(os.urandom(32).hex())"
```

---

## Database Scripts

| Command | Description |
|---|---|
| `python -m scripts.init_db` | Create tables (no-op if they exist) |
| `python -m scripts.init_db --drop` | Drop and recreate all tables |
| `python -m scripts.reset_db` | Drop and recreate all tables |
| `python -m scripts.seed` | Seed establishment, restaurants, menus, rooms, tables, staff |
| `python -m scripts.seed_orders` | Seed demo orders (`--clear` to delete existing first) |
| `python -m scripts.setup` | Full reset: drop, recreate, seed data and orders |

---

## Seed Data

The seed script creates:

- **1 establishment** -- "Grand Hotel" (slug: `grand-hotel`)
- **40 rooms** -- 101-110, 201-210, 301-310, 401-410
- **7 restaurants** -- Main Restaurant, Sushi Bar, Pool Grill, Rooftop Lounge, Breakfast & Co, The Steakhouse, Lobby Bar
- **~80 menu items** with options and real food images
- **56 tables** across all restaurants
- **1 superadmin** + 1 establishment admin + 14 staff members (7 managers, 7 supervisors)

---

## License

This project is proprietary. All rights reserved.
