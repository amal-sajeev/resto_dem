## Setup

1. **Python 3.11+** and **PostgreSQL** installed.

2. **Copy env and set credentials:**
   ```bash
   copy .env.example .env
   ```
   Edit `.env` and set `DATABASE_URL` to your PostgreSQL connection string (must use `postgresql+asyncpg://`).

3. **Create the database** in PostgreSQL (e.g. `createdb resto_db`), then install deps and create tables:
   ```bash
   pip install -r requirements.txt
   python -m scripts.init_db
   python -m scripts.seed
   python -m scripts.seed_orders        # optional: populate demo orders
   ```

4. **Run the API:**
   ```bash
   uvicorn app.main:app --reload
   ```
   - API root: http://127.0.0.1:8000/
   - Swagger UI: http://127.0.0.1:8000/docs

## API

- `GET /api/restaurants` — list restaurants
- `GET /api/restaurants/{id}` — one restaurant
- `GET /api/restaurants/{id}/menu` — menu for that restaurant
- `POST /api/orders` — create order (body: restaurant_id, room_id, party_size, payment_method, items)
- `GET /api/kitchen/orders?restaurant_id=<uuid>` — orders for kitchen (latest first)
- `PATCH /api/kitchen/orders/{id}` — update order status (body: `{"status": "preparing"|"ready"|"served"}`)
