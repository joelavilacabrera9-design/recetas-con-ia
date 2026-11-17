"""Esquemas de recetas.

`RecipeLLM` es el contrato que debe cumplir la respuesta del LLM: si el JSON
no lo cumple, se rechaza antes de guardarlo en la base de datos.
"""

import unicodedata
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Dificultad(str, Enum):
    FACIL = "fácil"
    MEDIA = "media"
    DIFICIL = "difícil"


_DIFICULTAD_ALIAS = {
    "facil": Dificultad.FACIL,
    "baja": Dificultad.FACIL,
    "easy": Dificultad.FACIL,
    "media": Dificultad.MEDIA,
    "medio": Dificultad.MEDIA,
    "intermedia": Dificultad.MEDIA,
    "medium": Dificultad.MEDIA,
    "dificil": Dificultad.DIFICIL,
    "alta": Dificultad.DIFICIL,
    "hard": Dificultad.DIFICIL,
}


def _sin_tildes(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


class RecipeIngredient(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    cantidad: str = Field(min_length=1, max_length=50)

    @field_validator("cantidad", mode="before")
    @classmethod
    def cantidad_a_texto(cls, v):
        # El LLM a veces devuelve números (2) en lugar de texto ("2 unidades").
        if isinstance(v, (int, float)):
            return str(v)
        return v


class RecipeLLM(BaseModel):
    nombre: str = Field(min_length=3, max_length=150)
    ingredientes: list[RecipeIngredient] = Field(min_length=1, max_length=30)
    pasos: list[str] = Field(min_length=1, max_length=30)
    tiempo_minutos: int = Field(ge=1, le=1440)
    dificultad: Dificultad

    @field_validator("pasos")
    @classmethod
    def pasos_no_vacios(cls, v: list[str]) -> list[str]:
        pasos = [p.strip() for p in v]
        if any(not p for p in pasos):
            raise ValueError("Los pasos no pueden estar vacíos")
        return pasos

    @field_validator("dificultad", mode="before")
    @classmethod
    def normalizar_dificultad(cls, v):
        if isinstance(v, str):
            clave = _sin_tildes(v.strip().lower())
            if clave in _DIFICULTAD_ALIAS:
                return _DIFICULTAD_ALIAS[clave]
        return v


class TipoPlato(str, Enum):
    DESAYUNO = "desayuno"
    ALMUERZO = "almuerzo"
    CENA = "cena"
    POSTRE = "postre"
    BEBIDA = "bebida"
    ACOMPANAMIENTO = "acompañamiento"


class GenerateRequest(BaseModel):
    """Parámetros opcionales de generación (no es un chat: campos acotados)."""

    tipo: TipoPlato | None = Field(default=None, examples=["almuerzo"])

    preferencias: str | None = Field(
        default=None, max_length=120, examples=["vegetariana, sin picante"]
    )
    porciones: int = Field(default=2, ge=1, le=12)

    @field_validator("preferencias")
    @classmethod
    def limpiar_preferencias(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = " ".join(v.split())
        return v or None


class RecipeOut(RecipeLLM):
    id: int
    inventario_usado: list[str]
    modelo_llm: str
    calificacion: int | None = None
    creado_en: datetime


class RatingIn(BaseModel):
    estrellas: int = Field(ge=1, le=5)


class RatingOut(BaseModel):
    receta_id: int
    estrellas: int
