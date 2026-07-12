import os
import random
from datetime import date
from sqlalchemy import ForeignKey, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_PORT = os.environ["POSTGRES_PORT"]
POSTGRES_DB = os.environ["POSTGRES_DB"]

engine = create_engine(f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")

class Base(DeclarativeBase):
    pass

class BookReference(Base):
    __tablename__ = "book_references"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    author: Mapped[str]
    inventories: Mapped[list["BookInventory"]] = relationship(
        "BookInventory",
        back_populates="reference",
        cascade="all, delete-orphan",
    )


class BookInventory(Base):
    __tablename__ = "book_inventories"
    id: Mapped[int] = mapped_column(primary_key=True)
    is_available: Mapped[bool] = mapped_column(default=True)
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
    rental_date: Mapped[date]
    inventory_id: Mapped[int] = mapped_column(ForeignKey("book_inventories.id"))
    inventory: Mapped["BookInventory"] = relationship(
        "BookInventory",
        back_populates="rentals",
    )


def _ensure_ready(session: Session):
    with session.begin():
        Base.metadata.create_all(session.get_bind())

# ----------- Private API functions -----------
    
def _add_reference(session: Session, name: str, author: str) -> int:
    reference = BookReference(name=name, author=author)
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
    new_inventory = BookInventory(reference_id=reference_id)
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

    rental = BookRental(rental_date=date.today(), inventory_id=inventory.id)
    session.add(rental)
    session.flush()
    return rental.id

def _remove_rental(session: Session, rental_id: int):
    rental = session.get(BookRental, rental_id)
    if rental is None:
        raise ValueError(f"Rental with id {rental_id} not found")
    inventory = session.get(BookInventory, rental.inventory_id)
    if inventory is None:
        raise ValueError(f"Inventory with id {rental.inventory_id} not found")
    inventory.is_available = True
    session.delete(rental)
    session.flush()
    
# ----------- Public API functions -----------
    
def add_book_to_library(session: Session, name: str, author: str, quantity: int):
    with session.begin():
        reference_id = _add_reference(session, name, author)
        for _ in range(quantity):
            _add_inventory(session, reference_id)
        return reference_id

def update_inventory(session: Session, reference_id: int, new_quantity: int):
    with session.begin():
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
                raise ValueError(f"Not enough available inventories to remove. Current available: {len(available_inventories)}, required to remove: {current_quantity - new_quantity}")
            for inv in available_inventories[:current_quantity - new_quantity]:
                _remove_inventory(session, inv.id)
                
        if new_quantity == 0:
            _remove_reference(session, reference_id)

def rent_book(session: Session, reference_id: int):
    with session.begin():
        reference = session.get(BookReference, reference_id)
        if reference is None:
            raise ValueError(f"Reference with id {reference_id} not found")
        
        available_inventory = session.execute(
            select(BookInventory).where(BookInventory.reference_id == reference_id, BookInventory.is_available == True)
        ).scalars().first()
        
        if available_inventory is None:
            raise ValueError(f"No available inventory for reference with id {reference_id}")
        
        return _add_rental(session, available_inventory.id)

def return_book(session: Session, rental_id: int):
    with session.begin():
        _remove_rental(session, rental_id)

def main():
    with Session(engine) as session:
        _ensure_ready(session)
        while True:
            action = random.choice(["add", "update", "rent", "return"])
            if action == "add":
                name = f"Book {random.randint(1, 100)}"
                author = f"Author {random.randint(1, 50)}"
                quantity = random.randint(1, 5)
                add_book_to_library(session, name, author, quantity)
            elif action == "update":
                reference_id = random.randint(1, 10)  # Assuming we have at least 10 references
                new_quantity = random.randint(0, 5)
                try:
                    update_inventory(session, reference_id, new_quantity)
                except ValueError as e:
                    print(e)
            elif action == "rent":
                reference_id = random.randint(1, 10)  # Assuming we have at least 10 references
                try:
                    rent_book(session, reference_id)
                except ValueError as e:
                    print(e)
            elif action == "return":
                rental_id = random.randint(1, 20)  # Assuming we have at least 20 rentals
                try:
                    return_book(session, rental_id)
                except ValueError as e:
                    print(e)
        

if __name__ == "__main__":
    main()