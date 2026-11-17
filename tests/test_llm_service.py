"""Cliente del LLM con un transporte HTTP simulado (sin llamadas reales)."""

import json

import httpx
import pytest

from app.schemas.ingredient import IngredientCreate
from app.services.llm_service import LLMService, LLMServiceError

INVENTARIO = [IngredientCreate(nombre="papa", cantidad=3, unidad="unidades")]

RECETA = {
    "nombre": "Papas salteadas",
    "ingredientes": [{"nombre": "papa", "cantidad": "3 unidades"}],
    "pasos": ["Pela y corta las papas.", "Saltéalas con aceite."],
    "tiempo_minutos": 30,
    "dificultad": "fácil",
}


def _respuesta(contenido: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": contenido}}]})


def _servicio(handler) -> LLMService:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return LLMService(api_key="test", model="modelo-prueba", client=client)


def test_envia_inventario_y_devuelve_receta():
    peticiones = []

    def handler(request: httpx.Request):
        peticiones.append(json.loads(request.content))
        assert request.headers["Authorization"] == "Bearer test"
        return _respuesta(json.dumps(RECETA))

    receta = _servicio(handler).generate_recipe(INVENTARIO)
    assert receta.nombre == "Papas salteadas"
    cuerpo = peticiones[0]
    assert cuerpo["model"] == "modelo-prueba"
    assert cuerpo["response_format"] == {"type": "json_object"}
    assert "papa: 3 unidades" in cuerpo["messages"][1]["content"]


def test_reintenta_una_vez_si_la_respuesta_no_es_json():
    respuestas = iter([_respuesta("Lo siento, no sé."), _respuesta(json.dumps(RECETA))])
    receta = _servicio(lambda _: next(respuestas)).generate_recipe(INVENTARIO)
    assert receta.tiempo_minutos == 30


def test_error_http_del_proveedor_lanza_llmserviceerror():
    servicio = _servicio(lambda _: httpx.Response(429, json={"error": "rate limit"}))
    with pytest.raises(LLMServiceError):
        servicio.generate_recipe(INVENTARIO)


def test_sin_api_key_lanza_error():
    servicio = LLMService(api_key="", model="x")
    with pytest.raises(LLMServiceError):
        servicio.generate_recipe(INVENTARIO)
