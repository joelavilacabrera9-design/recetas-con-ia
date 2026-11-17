from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Recipe(Base):
    __tablename__ = "recetas"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(150))
    # Lista de {"nombre": str, "cantidad": str}
    ingredientes: Mapped[list] = mapped_column(JSON)
    # Lista de pasos (str) en orden
    pasos: Mapped[list] = mapped_column(JSON)
    tiempo_minutos: Mapped[int] = mapped_column(Integer)
    dificultad: Mapped[str] = mapped_column(String(10))
    # Copia de los nombres del inventario usado al generar (trazabilidad)
    inventario_usado: Mapped[list] = mapped_column(JSON)
    modelo_llm: Mapped[str] = mapped_column(String(120))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usuario: Mapped["User"] = relationship(back_populates="recetas")  # noqa: F821
    calificacion: Mapped[Optional["Rating"]] = relationship(  # noqa: F821, UP007
        back_populates="receta", cascade="all, delete-orphan", uselist=False
    )
