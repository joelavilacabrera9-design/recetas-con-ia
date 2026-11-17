from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    ingredientes: Mapped[list["Ingredient"]] = relationship(  # noqa: F821
        back_populates="usuario", cascade="all, delete-orphan"
    )
    recetas: Mapped[list["Recipe"]] = relationship(  # noqa: F821
        back_populates="usuario", cascade="all, delete-orphan"
    )
