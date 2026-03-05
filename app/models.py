import enum
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class PaymentMethod(str, enum.Enum):
    room_bill = "room_bill"
    pay_now = "pay_now"


class OrderStatus(str, enum.Enum):
    received = "received"
    preparing = "preparing"
    ready = "ready"
    served = "served"
    cancelled = "cancelled"


class UserRole(str, enum.Enum):
    normal_user = "normal_user"
    establishment_admin = "establishment_admin"
    restaurant_admin = "restaurant_admin"
    supervisor = "supervisor"


class ReservationStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"
    no_show = "no_show"


from sqlalchemy.orm import DeclarativeBase


def utc_now() -> datetime:
    return datetime.utcnow()


class Base(DeclarativeBase):
    pass


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    open_from: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    open_until: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    menu_items: Mapped[list["MenuItem"]] = relationship("MenuItem", back_populates="restaurant")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="restaurant")
    tables: Mapped[list["Table"]] = relationship("Table", back_populates="restaurant")
    reservations: Mapped[list["Reservation"]] = relationship("Reservation", back_populates="restaurant")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    restaurant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    allergens: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    requires_option_selection: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="menu_items")
    options: Mapped[list["MenuItemOption"]] = relationship(
        "MenuItemOption", back_populates="menu_item", cascade="all, delete-orphan"
    )
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="menu_item")


class MenuItemOption(Base):
    __tablename__ = "menu_item_options"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    menu_item_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    price_delta: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))

    menu_item: Mapped["MenuItem"] = relationship("MenuItem", back_populates="options")
    order_item_options: Mapped[list["OrderItemOption"]] = relationship(
        "OrderItemOption", back_populates="menu_item_option"
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    restaurant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    room_id: Mapped[str] = mapped_column(String(32), nullable=False)
    party_size: Mapped[int] = mapped_column(nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod), nullable=False, default=PaymentMethod.room_bill
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), nullable=False, default=OrderStatus.received
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utc_now)

    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    room_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    menu_item_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    menu_item: Mapped["MenuItem"] = relationship("MenuItem", back_populates="order_items")
    options: Mapped[list["OrderItemOption"]] = relationship(
        "OrderItemOption", back_populates="order_item", cascade="all, delete-orphan"
    )


class OrderItemOption(Base):
    __tablename__ = "order_item_options"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_item_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False
    )
    menu_item_option_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_item_options.id", ondelete="CASCADE"), nullable=False
    )

    order_item: Mapped["OrderItem"] = relationship("OrderItem", back_populates="options")
    menu_item_option: Mapped["MenuItemOption"] = relationship(
        "MenuItemOption", back_populates="order_item_options"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    encrypted_name: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone_hash: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    encrypted_email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.normal_user)
    restaurant_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utc_now)

    reservations: Mapped[list["Reservation"]] = relationship("Reservation", back_populates="user")


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    restaurant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    table_number: Mapped[str] = mapped_column(String(32), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="tables")
    reservations: Mapped[list["Reservation"]] = relationship("Reservation", back_populates="table")


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    restaurant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    table_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tables.id", ondelete="CASCADE"), nullable=False
    )
    reservation_date: Mapped[date] = mapped_column(Date, nullable=False)
    reservation_time: Mapped[time] = mapped_column(Time, nullable=False)
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus), nullable=False, default=ReservationStatus.pending
    )
    confirmation_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="reservations")
    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="reservations")
    table: Mapped["Table"] = relationship("Table", back_populates="reservations")


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    phone_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
