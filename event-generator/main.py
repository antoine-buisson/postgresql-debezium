import os
import random
import sys
import time
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import ForeignKey, create_engine, func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

POSTGRES_USER_EVENT_GENERATOR = os.environ["POSTGRES_USER_EVENT_GENERATOR"]
POSTGRES_PASSWORD_EVENT_GENERATOR = os.environ["POSTGRES_PASSWORD_EVENT_GENERATOR"]
POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_PORT = os.environ["POSTGRES_PORT"]
POSTGRES_DB_MAIN = os.environ["POSTGRES_DB_MAIN"]
SLEEP_SECONDS = float(os.getenv("GENERATOR_SLEEP_SECONDS", "1.2"))
DB_STARTUP_TIMEOUT_SECONDS = int(os.getenv("GENERATOR_DB_STARTUP_TIMEOUT_SECONDS", "60"))

engine = create_engine(
    f"postgresql://{POSTGRES_USER_EVENT_GENERATOR}:{POSTGRES_PASSWORD_EVENT_GENERATOR}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB_MAIN}"
)


class Base(DeclarativeBase):
    pass


class BookReference(Base):
    __tablename__ = "book_references"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    author: Mapped[str]
    genre: Mapped[str] = mapped_column(default="general")
    publication_year: Mapped[int] = mapped_column(default=2000)
    price: Mapped[float] = mapped_column(default=19.99)
    is_featured: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[date] = mapped_column(default=date.today)

    inventories: Mapped[list["BookInventory"]] = relationship(
        "BookInventory",
        back_populates="reference",
        cascade="all, delete-orphan",
    )


class BookInventory(Base):
    __tablename__ = "book_inventories"

    id: Mapped[int] = mapped_column(primary_key=True)
    is_available: Mapped[bool] = mapped_column(default=True)
    condition: Mapped[str] = mapped_column(default="good")
    shelf_location: Mapped[str] = mapped_column(default="A-01")
    purchase_price: Mapped[float] = mapped_column(default=12.5)
    last_checked_out: Mapped[Optional[date]] = mapped_column(default=None, nullable=True)
    reference_id: Mapped[int] = mapped_column(ForeignKey("book_references.id"))

    reference: Mapped["BookReference"] = relationship(
        "BookReference",
        back_populates="inventories",
    )
    rentals: Mapped[list["BookRental"]] = relationship(
        "BookRental",
        back_populates="inventory",
        cascade="all, delete-orphan",
    )


class BookRental(Base):
    __tablename__ = "book_rentals"

    id: Mapped[int] = mapped_column(primary_key=True)
    rental_date: Mapped[date] = mapped_column(default=date.today)
    due_date: Mapped[date] = mapped_column(default=lambda: date.today() + timedelta(days=7))
    return_date: Mapped[Optional[date]] = mapped_column(default=None, nullable=True)
    customer_name: Mapped[str] = mapped_column(default="anonymous")
    late_fee: Mapped[float] = mapped_column(default=0.0)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("book_inventories.id"))

    inventory: Mapped["BookInventory"] = relationship(
        "BookInventory",
        back_populates="rentals",
    )


def _wait_for_database() -> None:
    deadline = time.time() + DB_STARTUP_TIMEOUT_SECONDS
    while True:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except OperationalError:
            if time.time() >= deadline:
                raise
            time.sleep(2)


def _ensure_ready(session: Session):
    bind = session.get_bind()
    Base.metadata.drop_all(bind)
    Base.metadata.create_all(bind)


ADJECTIVES = ["Silent", "Midnight", "Hidden", "Neon", "Velvet", "Golden", "Winter", "Quantum"]
NOUNS = ["Archive", "Harbor", "Cipher", "Echo", "Orchid", "Circuit", "Labyrinth", "Ridge"]
AUTHORS = ["Ada Sol", "Mina Cruz", "Noah Bell", "Lina Hart", "Jonas Pike", "Sage Kim"]
GENRES = ["Sci-Fi", "Fantasy", "Mystery", "Biography", "History", "Romance", "Tech"]
LOCATIONS = ["A-01", "A-02", "B-11", "B-12", "C-03", "C-05"]
CUSTOMERS = ["Ava", "Ben", "Cara", "Drew", "Elia", "Finn", "Gabe", "Hana"]


def _generate_book_name() -> str:
    return f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)}"


def _generate_author() -> str:
    return random.choice(AUTHORS)


def _generate_genre() -> str:
    return random.choice(GENRES)


def _generate_price() -> float:
    return round(random.uniform(8.0, 35.0), 2)


# ----------- Private API functions -----------

def _add_reference(session: Session, name: str, author: str, genre: str, publication_year: int, price: float) -> int:
    reference = BookReference(
        name=name,
        author=author,
        genre=genre,
        publication_year=publication_year,
        price=price,
        is_featured=random.choice([True, False]),
        created_at=date.today(),
    )
    session.add(reference)
    session.flush()
    return reference.id


def _remove_reference(session: Session, reference_id: int):
    reference = session.get(BookReference, reference_id)
    if reference is None:
        raise ValueError(f"Reference with id {reference_id} not found")
    if reference.inventories:
        raise ValueError(f"Reference with id {reference_id} has associated inventories and cannot be removed")
    session.delete(reference)
    session.flush()


def _add_inventory(session: Session, reference_id: int) -> int:
    reference = session.get(BookReference, reference_id)
    if reference is None:
        raise ValueError(f"Reference with id {reference_id} not found")

    new_inventory = BookInventory(
        reference_id=reference_id,
        condition=random.choice(["new", "good", "excellent", "damaged"]),
        shelf_location=random.choice(LOCATIONS),
        purchase_price=round(reference.price * random.uniform(0.5, 0.9), 2),
    )
    session.add(new_inventory)
    session.flush()
    return new_inventory.id


def _remove_inventory(session: Session, inventory_id: int):
    inventory = session.get(BookInventory, inventory_id)
    if inventory is None:
        raise ValueError(f"Inventory with id {inventory_id} not found")
    if not inventory.is_available:
        raise ValueError(f"Inventory with id {inventory_id} is currently rented and cannot be removed")
    session.delete(inventory)
    session.flush()


def _add_rental(session: Session, inventory_id: int) -> int:
    inventory = session.get(BookInventory, inventory_id)
    if inventory is None:
        raise ValueError(f"Inventory with id {inventory_id} not found")
    if not inventory.is_available:
        raise ValueError(f"Inventory with id {inventory_id} is not available for rental")

    rental = BookRental(
        rental_date=date.today(),
        due_date=date.today() + timedelta(days=random.randint(5, 14)),
        customer_name=random.choice(CUSTOMERS),
        late_fee=0.0,
        inventory_id=inventory.id,
    )
    inventory.is_available = False
    inventory.last_checked_out = date.today()
    session.add(rental)
    session.flush()
    return rental.id


def _return_rental(session: Session, rental_id: int):
    rental = session.get(BookRental, rental_id)
    if rental is None:
        raise ValueError(f"Rental with id {rental_id} not found")
    if rental.return_date is not None:
        raise ValueError(f"Rental with id {rental_id} already returned")

    inventory = session.get(BookInventory, rental.inventory_id)
    if inventory is None:
        raise ValueError(f"Inventory with id {rental.inventory_id} not found")

    rental.return_date = date.today()
    inventory.is_available = True
    if rental.return_date > rental.due_date:
        rental.late_fee = round(random.uniform(1.0, 4.5), 2)
    session.flush()


# ----------- Public API functions -----------

def add_book_to_library(session: Session, name: str, author: str, quantity: int):
    reference_id = _add_reference(
        session,
        name=name,
        author=author,
        genre=_generate_genre(),
        publication_year=random.randint(1980, 2025),
        price=_generate_price(),
    )
    for _ in range(quantity):
        _add_inventory(session, reference_id)
    return reference_id


def update_inventory(session: Session, reference_id: int, new_quantity: int):
    reference = session.get(BookReference, reference_id)
    if reference is None:
        raise ValueError(f"Reference with id {reference_id} not found")

    current_quantity = len(reference.inventories)
    if new_quantity > current_quantity:
        for _ in range(new_quantity - current_quantity):
            _add_inventory(session, reference_id)
    elif new_quantity < current_quantity:
        available_inventories = [inv for inv in reference.inventories if inv.is_available]
        if len(available_inventories) < (current_quantity - new_quantity):
            raise ValueError(
                f"Not enough available inventories to remove. Current available: {len(available_inventories)}, required to remove: {current_quantity - new_quantity}"
            )
        for inv in available_inventories[: current_quantity - new_quantity]:
            _remove_inventory(session, inv.id)

    if new_quantity == 0:
        _remove_reference(session, reference_id)


def rent_book(session: Session, reference_id: int):
    reference = session.get(BookReference, reference_id)
    if reference is None:
        raise ValueError(f"Reference with id {reference_id} not found")

    available_inventory = session.execute(
        select(BookInventory)
        .where(BookInventory.reference_id == reference_id, BookInventory.is_available.is_(True))
        .order_by(BookInventory.id)
    ).scalars().first()

    if available_inventory is None:
        raise ValueError(f"No available inventory for reference with id {reference_id}")

    return _add_rental(session, available_inventory.id)


def return_book(session: Session, rental_id: int):
    _return_rental(session, rental_id)


def _state_summary(session: Session) -> dict[str, int]:
    reference_count = session.scalar(select(func.count(BookReference.id))) or 0
    inventory_count = session.scalar(select(func.count(BookInventory.id))) or 0
    available_inventory_count = session.scalar(
        select(func.count(BookInventory.id)).where(BookInventory.is_available.is_(True))
    ) or 0
    active_rental_count = session.scalar(
        select(func.count(BookRental.id)).where(BookRental.return_date.is_(None))
    ) or 0
    return {
        "references": reference_count,
        "inventories": inventory_count,
        "available": available_inventory_count,
        "active_rentals": active_rental_count,
    }


def _choose_next_action(session: Session) -> str:
    state = _state_summary(session)

    if state["references"] == 0:
        return "add"

    if state["active_rentals"] > 0 and random.random() < 0.35:
        return "return"

    if state["available"] > 0 and random.random() < 0.45:
        return "rent"

    if state["references"] >= 1 and state["inventories"] < state["references"] * 2 and random.random() < 0.30:
        return "update"

    if random.random() < 0.25:
        return "add"

    return random.choice(["update", "rent", "return"])


def main():
    _wait_for_database()
    with Session(engine) as session:
        _ensure_ready(session)
        while True:
            action = _choose_next_action(session)
            try:
                if action == "add":
                    name = _generate_book_name()
                    author = _generate_author()
                    quantity = random.randint(1, 3)
                    add_book_to_library(session, name, author, quantity)
                    print(f"Added {quantity} copy/copies of '{name}' by {author}", flush=True)
                elif action == "update":
                    reference_ids = session.execute(select(BookReference.id)).scalars().all()
                    if not reference_ids:
                        continue
                    reference_id = random.choice(reference_ids)
                    current_reference = session.get(BookReference, reference_id)
                    current_quantity = len(current_reference.inventories) if current_reference else 0
                    new_quantity = max(0, current_quantity + random.randint(-1, 2))
                    update_inventory(session, reference_id, new_quantity)
                    print(f"Updated stock for reference {reference_id} to {new_quantity}", flush=True)
                elif action == "rent":
                    reference_ids = session.execute(select(BookReference.id)).scalars().all()
                    if not reference_ids:
                        continue
                    reference_id = random.choice(reference_ids)
                    rental_id = rent_book(session, reference_id)
                    print(f"Rented book from reference {reference_id} as rental {rental_id}", flush=True)
                elif action == "return":
                    active_rentals = session.execute(
                        select(BookRental.id).where(BookRental.return_date.is_(None))
                    ).scalars().all()
                    if not active_rentals:
                        continue
                    rental_id = random.choice(active_rentals)
                    return_book(session, rental_id)
                    print(f"Returned rental {rental_id}", flush=True)

                session.commit()
            except Exception as exc:
                session.rollback()
                print(exc, flush=True)

            time.sleep(SLEEP_SECONDS + random.uniform(-0.2, 0.3))


if __name__ == "__main__":
    main()