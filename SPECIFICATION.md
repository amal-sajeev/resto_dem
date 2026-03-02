# Hotel Multi-Restaurant Ordering System — Specification

## Overview

A demo web application for a hotel where guests can order food from multiple in-hotel restaurants via a QR code in their room. Orders are sent to the respective kitchen, and guests can pay on the spot or add the cost to their room bill. The system includes a **guest ordering flow** and a **kitchen display view**.

---

## 1. Guest Flow (Room → Order)

### 1.1 Entry Point: QR Code in Room

- **QR code** in each room links to a web app (e.g. `https://hotel-order.example.com/room/{roomId}` or a short code).
- Scanning opens the app in the browser (mobile-first; works on tablet/desktop too).
- **Room identification**: The URL or a one-time token identifies the room so:
  - Orders can be charged to the room bill if the guest chooses.
  - The kitchen/delivery knows where to send the order (room number).

### 1.2 Restaurant Selection

- After opening the link, the guest sees **all in-hotel restaurants** (e.g. “Main Restaurant”, “Sushi Bar”, “Pool Grill”, “Room Service”).
- **UI**: Cards or list with:
  - Restaurant name
  - Short description or tagline
  - Image/thumbnail
  - Optional: opening hours, “busy” indicator
- **Interaction**: Tap/click one restaurant to proceed to its menu.
- **Animation**: Smooth transition (e.g. slide or fade) into the menu view.

### 1.3 “How Many People?” (Party Size)

- Before or at the start of ordering, ask **“How many people?”** (e.g. 1–20 or 1–10 with a stepper).
- **Purpose**:
  - Kitchen can plan quantities and prep.
  - Optional: suggest “for 2” / “for 4” portion sizes or set defaults.
- **Persistence**: Remember for the session; allow changing before confirming the order.

### 1.4 Menu & Ordering

- **Menu** is specific to the selected restaurant:
  - Categories (e.g. Starters, Mains, Desserts, Drinks).
  - Each item: name, short description, price, image (optional).
  - Allergens or dietary tags optional for demo.
- **Actions**:
  - Add to cart (with quantity).
  - View cart: list of items, quantities, subtotal.
  - Edit quantities or remove items.
- **UI**: Smooth animations (add-to-cart feedback, cart badge updates, subtle motion). Clear typography and spacing.

### 1.5 Checkout & Payment

- **Checkout** step shows:
  - Order summary (items, quantities, party size).
  - **Subtotal** (and tax if applicable).
- **Payment choice** (two clear options):
  1. **Add to room bill** — charge to the room linked to the QR (show room number for confirmation).
  2. **Pay now** — pay immediately (for demo: card form or “Pay at counter” / “Cash at delivery”).
- **Place order**: Button to send the order to the kitchen. Success state with clear confirmation (e.g. “Order sent to [Restaurant]. You’ll receive it at Room XXX.”).

### 1.6 Order Confirmation & Status (Optional for demo)

- After placing: show order ID and short message.
- Optional: simple status like “Received”, “Preparing”, “On the way” (can be simulated or driven by kitchen actions later).

---

## 2. Kitchen View

### 2.1 Purpose

- **Kitchen display** for staff: see incoming orders for their restaurant in real time (or via refresh/polling in demo).

### 2.2 Layout & Data

- **Orders listed by latest first** (newest at top).
- Each order card/row shows:
  - **Order ID** (and optionally time received).
  - **Room number** (or “Table X” if you add table service later).
  - **Party size** (“For 2”, “For 4”, etc.).
  - **Items** with quantities (e.g. “2× Caesar Salad”, “1× Grilled Salmon”).
  - **Special requests** (if you add a notes field).
  - **Payment**: “Room bill” or “Paid”.
- **Actions** (at least for demo):
  - Mark as **“Preparing”** / **“Ready”** / **“Served”** (or a single “Done”) to move orders down the list or to a “Completed” section.

### 2.3 Real-time or Polling

- **Demo**: Periodic refresh (e.g. every 10–15 seconds) or a “Refresh” button is enough.
- **Future**: WebSockets or server-sent events for live updates.

### 2.4 Access Control

- Kitchen view is on a separate route (e.g. `/kitchen`) or subdomain.
- Optional: simple PIN or password so only staff can open it.

---

## 3. UI/UX Requirements

### 3.1 Aesthetic & Feel

- **Flashy, smooth, animated**:
  - Transitions between: Restaurant list → Menu → Cart → Checkout.
  - Micro-interactions: buttons, add-to-cart, cart badge.
  - Subtle motion (e.g. staggered list appearance, gentle hover/focus states).
- **Good aesthetic**:
  - Consistent color palette (e.g. dark theme for a “premium” feel, or light with strong accents).
  - Clear hierarchy: headings, body text, prices.
  - High-quality placeholder images for restaurants and dishes if no assets.

### 3.2 Responsiveness

- **Mobile-first**: Optimized for phone (what guests will use in the room).
- **Tablet**: Comfortable on tablet for both guest and kitchen.
- **Desktop**: Usable on larger screens for kitchen or admin.

### 3.3 Performance

- Fast initial load after scanning QR.
- Smooth 60fps-style animations (use CSS transforms/opacity, avoid layout thrashing).

---

## 4. Technical Scope (Demo)

### 4.1 In Scope for Demo

- Static or simple backend: e.g. JSON menus, in-memory or file-based order store.
- One hotel, multiple restaurants, each with a menu.
- Guest flow: QR → restaurant choice → party size → menu → cart → payment choice → place order.
- Kitchen view: list orders by latest, show room, party size, items; simple status actions.
- No real payment processing (mock “Add to bill” / “Pay now”).
- No real auth (room can be inferred from URL or a dropdown for demo).

### 4.2 Out of Scope (Unless You Want to Extend)

- Real POS or PMS integration (e.g. charging the room in the hotel’s real system).
- Real payment gateway.
- User accounts or login.
- Inventory or recipe costing.
- Multi-property or multi-hotel.

---

## 5. Data Model (Suggested)

### 5.1 Restaurant

- `id`, `name`, `description`, `imageUrl`, optional `openFrom` / `openUntil`.

### 5.2 Menu Item

- `id`, `restaurantId`, `name`, `description`, `price`, `category`, optional `imageUrl`, optional `allergens`.

### 5.3 Order

- `id`, `restaurantId`, `roomId` (or room number), `partySize`, `items` (array of `{ menuItemId, name, quantity, unitPrice }`), `subtotal`, `paymentMethod` (“room_bill” | “pay_now”), `status` (“received” | “preparing” | “ready” | “served”), `createdAt`.

---

## 6. Summary Checklist

| Feature | Description |
|--------|-------------|
| QR in room | Links to app with room context |
| Multiple restaurants | Guest picks one restaurant |
| Party size | “How many people?” for kitchen planning |
| Menu per restaurant | Browse and add items, cart with quantities |
| Payment options | Add to room bill or pay now (mock) |
| Send to kitchen | Order appears in kitchen view |
| Kitchen view | Orders by latest, room, party size, items, status actions |
| UI | Flashy, smooth, animated, strong aesthetic, mobile-first |

This specification is ready to be used for implementation (e.g. React/Next.js or Vue front end, optional Node/Python backend for orders and kitchen updates).
