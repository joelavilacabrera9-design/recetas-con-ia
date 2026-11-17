"""Pruebas de endpoints con TestClient, SQLite en memoria y LLM simulado."""


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_favicon_disponible(client):
    resp = client.get("/favicon.ico")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/x-icon"


def test_registro_duplicado_y_login_incorrecto(client):
    datos = {"email": "luis@correo.co", "nombre": "Luis", "password": "clave1234"}
    assert client.post("/api/auth/register", json=datos).status_code == 201
    assert client.post("/api/auth/register", json=datos).status_code == 409
    resp = client.post(
        "/api/auth/login", data={"username": "luis@correo.co", "password": "otra12345"}
    )
    assert resp.status_code == 401


def test_endpoints_protegidos_sin_token(client):
    assert client.get("/api/ingredients").status_code == 401
    assert client.post("/api/recipes/generate", json={}).status_code == 401


def test_crud_de_ingredientes(auth_client):
    resp = auth_client.post("/api/ingredients", json={"nombre": "Tomate", "cantidad": 3})
    assert resp.status_code == 201
    ing_id = resp.json()["id"]
    assert resp.json()["nombre"] == "tomate"

    # Duplicado y nombre inválido
    assert auth_client.post("/api/ingredients", json={"nombre": "tomate"}).status_code == 409
    assert auth_client.post("/api/ingredients", json={"nombre": "123"}).status_code == 422
    resp = auth_client.post("/api/ingredients", json={"nombre": "nada"})
    assert resp.status_code == 422
    assert "no es un ingrediente reconocido" in resp.text
    # "Tomates" se unifica con "tomate", por eso es duplicado
    assert auth_client.post("/api/ingredients", json={"nombre": "Tomates"}).status_code == 409

    resp = auth_client.put(
        f"/api/ingredients/{ing_id}", json={"nombre": "tomate", "cantidad": 5, "unidad": "unidades"}
    )
    assert resp.status_code == 200 and resp.json()["cantidad"] == 5

    assert len(auth_client.get("/api/ingredients").json()) == 1
    assert auth_client.delete(f"/api/ingredients/{ing_id}").status_code == 204
    assert auth_client.get("/api/ingredients").json() == []


def test_catalogo_de_ingredientes(auth_client):
    resp = auth_client.get("/api/ingredients/catalogo")
    assert resp.status_code == 200
    assert "tomate" in resp.json()


def test_generar_sin_inventario_devuelve_400(auth_client):
    assert auth_client.post("/api/recipes/generate", json={}).status_code == 400


def test_flujo_completo_generar_calificar_eliminar(auth_client):
    auth_client.post("/api/ingredients", json={"nombre": "arroz", "cantidad": 500, "unidad": "g"})
    auth_client.post("/api/ingredients", json={"nombre": "huevo", "cantidad": 4})

    assert auth_client.post("/api/recipes/generate", json={"tipo": "merienda"}).status_code == 422
    resp = auth_client.post("/api/recipes/generate", json={"porciones": 2, "tipo": "almuerzo"})
    assert resp.status_code == 201
    receta = resp.json()
    for campo in ["nombre", "ingredientes", "pasos", "tiempo_minutos", "dificultad"]:
        assert campo in receta
    assert receta["inventario_usado"] == ["arroz", "huevo"]
    assert receta["calificacion"] is None

    # Calificar (1 a 5) y validar rango
    rid = receta["id"]
    assert auth_client.put(f"/api/recipes/{rid}/rating", json={"estrellas": 4}).status_code == 200
    assert auth_client.put(f"/api/recipes/{rid}/rating", json={"estrellas": 9}).status_code == 422
    assert auth_client.put(f"/api/recipes/{rid}/rating", json={"estrellas": 5}).status_code == 200

    historial = auth_client.get("/api/recipes").json()
    assert len(historial) == 1 and historial[0]["calificacion"] == 5

    assert auth_client.delete(f"/api/recipes/{rid}").status_code == 204
    assert auth_client.get("/api/recipes").json() == []
    assert auth_client.get(f"/api/recipes/{rid}").status_code == 404


def test_un_usuario_no_ve_recetas_de_otro(auth_client):
    auth_client.post("/api/ingredients", json={"nombre": "papa"})
    rid = auth_client.post("/api/recipes/generate", json={}).json()["id"]

    auth_client.post(
        "/api/auth/register",
        json={"email": "otro@correo.co", "nombre": "Otro", "password": "clave1234"},
    )
    token = auth_client.post(
        "/api/auth/login", data={"username": "otro@correo.co", "password": "clave1234"}
    ).json()["access_token"]
    auth_client.headers["Authorization"] = f"Bearer {token}"

    assert auth_client.get(f"/api/recipes/{rid}").status_code == 404
    assert auth_client.delete(f"/api/recipes/{rid}").status_code == 404
    assert auth_client.get("/api/recipes").json() == []
