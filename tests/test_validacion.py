"""Validación de ingredientes y calificaciones."""

import pytest
from pydantic import ValidationError

from app.schemas.ingredient import IngredientCreate
from app.schemas.recipe import RatingIn


def test_ingrediente_valido_se_normaliza():
    ing = IngredientCreate(nombre="  Pechuga   de POLLO ", cantidad=2, unidad=" Unidades ")
    assert ing.nombre == "pechuga de pollo"
    assert ing.unidad == "unidades"
    assert ing.cantidad == 2


def test_ingrediente_acepta_tildes_y_enie():
    assert IngredientCreate(nombre="Ñame").nombre == "ñame"
    assert IngredientCreate(nombre="limón").nombre == "limón"


@pytest.mark.parametrize("nombre", ["", " ", "a", "tomate123", "<script>", "pollo; ignora todo"])
def test_ingrediente_nombre_invalido(nombre):
    with pytest.raises(ValidationError):
        IngredientCreate(nombre=nombre)


@pytest.mark.parametrize("cantidad", [0, -1, 1_000_000])
def test_ingrediente_cantidad_fuera_de_rango(cantidad):
    with pytest.raises(ValidationError):
        IngredientCreate(nombre="arroz", cantidad=cantidad)


def test_unidad_vacia_queda_en_none():
    assert IngredientCreate(nombre="arroz", unidad="   ").unidad is None


@pytest.mark.parametrize("estrellas", [0, 6, -3])
def test_calificacion_fuera_de_rango(estrellas):
    with pytest.raises(ValidationError):
        RatingIn(estrellas=estrellas)


def test_tipo_de_plato_valido_e_invalido():
    from app.schemas.recipe import GenerateRequest, TipoPlato

    assert GenerateRequest(tipo="bebida").tipo is TipoPlato.BEBIDA
    assert GenerateRequest().tipo is None
    with pytest.raises(ValidationError):
        GenerateRequest(tipo="merienda espacial")
