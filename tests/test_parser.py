"""Parseo y validación de la respuesta del LLM."""

import json

import pytest

from app.schemas.recipe import Dificultad
from app.services.llm_service import LLMResponseFormatError, parse_recipe_response

RECETA = {
    "nombre": "Arroz con huevo",
    "ingredientes": [
        {"nombre": "arroz", "cantidad": "200 g"},
        {"nombre": "huevo", "cantidad": 2},
    ],
    "pasos": ["Cocina el arroz.", "Fríe los huevos.", "Sirve."],
    "tiempo_minutos": 25,
    "dificultad": "fácil",
}


def test_parsea_json_limpio():
    receta = parse_recipe_response(json.dumps(RECETA))
    assert receta.nombre == "Arroz con huevo"
    assert receta.tiempo_minutos == 25
    assert receta.dificultad is Dificultad.FACIL
    assert len(receta.pasos) == 3


def test_convierte_cantidad_numerica_a_texto():
    receta = parse_recipe_response(json.dumps(RECETA))
    assert receta.ingredientes[1].cantidad == "2"


def test_parsea_json_dentro_de_bloque_de_codigo_y_texto():
    texto = "Claro, aquí tienes:\n```json\n" + json.dumps(RECETA) + "\n```\n¡Buen provecho!"
    assert parse_recipe_response(texto).nombre == "Arroz con huevo"


def test_parsea_json_rodeado_de_texto_sin_bloque():
    texto = "Receta: " + json.dumps(RECETA) + " Fin."
    assert parse_recipe_response(texto).nombre == "Arroz con huevo"


@pytest.mark.parametrize("valor,esperado", [
    ("Facil", Dificultad.FACIL),
    ("MEDIA", Dificultad.MEDIA),
    ("dificil", Dificultad.DIFICIL),
    ("hard", Dificultad.DIFICIL),
])
def test_normaliza_dificultad(valor, esperado):
    datos = {**RECETA, "dificultad": valor}
    assert parse_recipe_response(json.dumps(datos)).dificultad is esperado


def test_acepta_alias_de_campos():
    datos = {**RECETA}
    datos["nombre_plato"] = datos.pop("nombre")
    datos["tiempo_estimado"] = datos.pop("tiempo_minutos")
    receta = parse_recipe_response(json.dumps(datos))
    assert receta.nombre == "Arroz con huevo"
    assert receta.tiempo_minutos == 25


@pytest.mark.parametrize("texto", [
    "",
    "No puedo ayudarte con eso.",
    "{nombre: arroz}",
    "[1, 2, 3]",
])
def test_rechaza_respuestas_que_no_son_json_objeto(texto):
    with pytest.raises(LLMResponseFormatError):
        parse_recipe_response(texto)


@pytest.mark.parametrize("campo", ["nombre", "ingredientes", "pasos", "tiempo_minutos", "dificultad"])
def test_rechaza_si_falta_un_campo_obligatorio(campo):
    datos = {k: v for k, v in RECETA.items() if k != campo}
    with pytest.raises(LLMResponseFormatError):
        parse_recipe_response(json.dumps(datos))


def test_rechaza_valores_invalidos():
    for cambio in [{"tiempo_minutos": -5}, {"dificultad": "imposible"}, {"pasos": []}]:
        with pytest.raises(LLMResponseFormatError):
            parse_recipe_response(json.dumps({**RECETA, **cambio}))
