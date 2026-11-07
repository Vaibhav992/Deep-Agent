from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.

    Using DeclarativeBase gives us:
    - Type-safe column definitions via Mapped[]
    - Auto table name from class name
    - Single source of truth for Alembic migrations
    """
    pass
