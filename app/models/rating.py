from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Rating(Base):
    __tablename__ = "calificaciones"
    __table_args__ = (
        UniqueConstraint("receta_id", "usuario_id", name="uq_calificacion_receta_usuario"),
        CheckConstraint("estrellas BETWEEN 1 AND 5", name="ck_estrellas_rango"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    receta_id: Mapped[int] = mapped_column(
        ForeignKey("recetas.id", ondelete="CASCADE"), index=True
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    estrellas: Mapped[int] = mapped_column(SmallInteger)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    receta: Mapped["Recipe"] = relationship(back_populates="calificacion")  # noqa: F821
