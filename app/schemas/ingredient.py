"""Validación de ingredientes del inventario.

1. El nombre se normaliza (minúsculas, espacios simples) y solo admite letras,
   espacios y guiones. Esto también limita la inyección de instrucciones en el
   prompt del LLM a través del inventario.
2. Al crear o editar, el nombre debe existir en el catálogo de ingredientes
   (app/services/catalogo.py). Así se rechazan entradas como "nada" o "hola",
   se unifican plurales ("tomates" -> "tomate") y se sugiere el nombre correcto
   cuando hay errores de escritura.
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services import catalogo

_LETRAS = "a-záéíóúüñ"
NOMBRE_RE = re.compile(rf"^[{_LETRAS}][{_LETRAS} \-]*[{_LETRAS}]$")
UNIDAD_RE = re.compile(rf"^[{_LETRAS}\. ]+$")


def _normalizar(texto: str) -> str:
    return " ".join(texto.split()).lower()


class IngredientBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=50, examples=["tomate"])
    cantidad: float | None = Field(default=None, gt=0, le=100_000, examples=[3])
    unidad: str | None = Field(default=None, max_length=20, examples=["unidades"])

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_formato_nombre(cls, v):
        if not isinstance(v, str):
            raise ValueError("El nombre debe ser texto")
        v = _normalizar(v)
        if len(v) >= 2 and not NOMBRE_RE.match(v):
            raise ValueError("El nombre solo puede contener letras, espacios y guiones")
        return v

    @field_validator("unidad", mode="before")
    @classmethod
    def validar_unidad(cls, v):
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("La unidad debe ser texto")
        v = _normalizar(v)
        if v == "":
            return None
        if not UNIDAD_RE.match(v):
            raise ValueError("La unidad solo puede contener letras, puntos y espacios")
        return v


class IngredientCreate(IngredientBase):
    """Datos para crear o editar: el nombre debe ser un ingrediente reconocido."""

    @field_validator("nombre")
    @classmethod
    def validar_en_catalogo(cls, v: str) -> str:
        encontrado = catalogo.buscar(v)
        if encontrado:
            return encontrado
        opciones = catalogo.sugerencias(v)
        mensaje = f"«{v}» no es un ingrediente reconocido."
        if opciones:
            mensaje += " ¿Quisiste decir: " + ", ".join(opciones) + "?"
        else:
            mensaje += " Escribe el nombre de un alimento, por ejemplo: arroz, tomate o pollo."
        raise ValueError(mensaje)


class IngredientOut(IngredientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    creado_en: datetime
