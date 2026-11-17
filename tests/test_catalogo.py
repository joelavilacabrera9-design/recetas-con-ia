"""Catálogo de ingredientes: rechaza lo que no es comida y unifica variantes."""

import pytest
from pydantic import ValidationError

from app.schemas.ingredient import IngredientCreate
from app.services import catalogo


@pytest.mark.parametrize("nombre", ["nada", "hola", "asdf", "mesa", "computador"])
def test_rechaza_palabras_que_no_son_ingredientes(nombre):
    with pytest.raises(ValidationError, match="no es un ingrediente reconocido"):
        IngredientCreate(nombre=nombre)


@pytest.mark.parametrize("entrada,esperado", [
    ("Tomates", "tomate"),
    ("limones", "limón"),
    ("frijoles", "fríjol"),
    ("papas criollas", "papa criolla"),
    ("PIMENTON", "pimentón"),
    ("patata", "papa"),
])
def test_unifica_plurales_tildes_y_sinonimos(entrada, esperado):
    assert IngredientCreate(nombre=entrada).nombre == esperado


def test_sugiere_nombre_cuando_hay_error_de_escritura():
    assert "tomate" in catalogo.sugerencias("tomtae")
    with pytest.raises(ValidationError, match="Quisiste decir: .*zanahoria"):
        IngredientCreate(nombre="zanaoria")


def test_listar_esta_ordenado_y_sin_duplicados():
    nombres = catalogo.listar()
    assert len(nombres) == len(set(nombres)) > 200
    assert "arroz" in nombres and "ñame" in nombres
