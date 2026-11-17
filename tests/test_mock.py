"""El simulador (LLM_MOCK=true) genera recetas variadas y válidas."""

from app.schemas.ingredient import IngredientCreate
from app.services.llm_service import MockLLMService

INVENTARIO = [
    IngredientCreate(nombre="yuca", cantidad=2, unidad="unidades"),
    IngredientCreate(nombre="huevo", cantidad=4),
    IngredientCreate(nombre="cebolla"),
]


def test_mock_genera_platos_distintos():
    mock = MockLLMService(seed=1)
    nombres = {mock.generate_recipe(INVENTARIO).nombre for _ in range(10)}
    assert len(nombres) >= 5


def test_mock_no_repite_recetas_recientes():
    mock = MockLLMService(seed=2)
    recientes = []
    for _ in range(8):
        receta = mock.generate_recipe(INVENTARIO, evitar=recientes[-5:])
        assert receta.nombre not in recientes[-5:]
        recientes.append(receta.nombre)
