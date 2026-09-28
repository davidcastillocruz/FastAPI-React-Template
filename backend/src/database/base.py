"""
Declarative base for all SQLAlchemy models.

Every model in the project should inherit from `Base`. The shared
`MetaData` object applies a consistent naming convention to indexes,
constraints, and keys, which makes migrations readable and avoids
auto-generated names like `ix_5f4a3b2c1d`.

All models must be imported somewhere before running Alembic
autogenerate, otherwise their tables will not be detected. The usual
pattern is to import them in the migrations `env.py` or in a module
that `env.py` imports.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base

# Naming convention applied to all constraints and indexes. Without this,
# Postgres generates opaque names like `email_requests_email_key`, which
# are painful to reference in future migrations.
#
# References:
#   - `ix`: index
#   - `uq`: unique constraint
#   - `ck`: check constraint
#   - `fk`: foreign key
#   - `pk`: primary key
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

# Shared declarative base. Import this in every model module:
#
#     from src.database.base import Base
#
#     class MyModel(Base):
#         __tablename__ = "my_table"
#         ...
Base = declarative_base(metadata=metadata)