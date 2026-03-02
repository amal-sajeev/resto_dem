import enum
from datetime import datetime, time
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text, Time
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
