"""Construcción del prompt enviado al LLM."""

import pytest

from app.schemas.ingredient import IngredientCreate
from app.services.llm_service import build_prompt

INVENTARIO = [
    IngredientCreate(nombre="arroz", cantidad=500, unidad="g"),
    IngredientCreate(nombre="huevo", cantidad=4, unidad="unidades"),
    IngredientCreate(nombre="cebolla"),
]


def test_prompt_tiene_system_y_user():
    mensajes = build_prompt(INVENTARIO)
    assert [m["role"] for m in mensajes] == ["system", "user"]


def test_prompt_incluye_todo_el_inventario_con_cantidades():
    user = build_prompt(INVENTARIO)[1]["content"]
    assert "- arroz: 500 g" in user
    assert "- huevo: 4 unidades" in user
    assert "- cebolla" in user


def test_prompt_exige_json_con_los_campos_requeridos():
    system = build_prompt(INVENTARIO)[0]["content"]
    assert "JSON" in system
    for campo in ["nombre", "ingredientes", "pasos", "tiempo_minutos", "dificultad"]:
        assert f'"{campo}"' in system


def test_prompt_incluye_porciones_y_preferencias():
    user = build_prompt(INVENTARIO, preferencias="sin picante", porciones=4)[1]["content"]
    assert "Porciones: 4" in user
    assert 'Preferencias: "sin picante"' in user


def test_prompt_sin_preferencias_no_las_menciona():
    user = build_prompt(INVENTARIO)[1]["content"]
    assert "Preferencias" not in user


def test_prompt_con_inventario_vacio_falla():
    with pytest.raises(ValueError):
        build_prompt([])


def test_prompt_pide_evitar_recetas_recientes():
    user = build_prompt(INVENTARIO, evitar=["Salteado de arroz", "Sopa de huevo"])[1]["content"]
    assert "DIFERENTE" in user
    assert "- Salteado de arroz" in user
    assert "- Sopa de huevo" in user


def test_prompt_no_obliga_a_usar_todos_los_ingredientes():
    system = build_prompt(INVENTARIO)[0]["content"]
    assert "NO es obligatorio usar todos" in system


def test_prompt_incluye_tipo_de_plato():
    user = build_prompt(INVENTARIO, tipo="postre")[1]["content"]
    assert "Tipo de plato: postre" in user
    assert "Tipo de plato" not in build_prompt(INVENTARIO)[1]["content"]
