"""Páginas HTML (Jinja2). Los datos se cargan desde la API con JavaScript."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(include_in_schema=False)


def _pagina(request: Request, plantilla: str, titulo: str) -> HTMLResponse:
    return templates.TemplateResponse(request, plantilla, {"titulo": titulo})


@router.get("/")
def inicio():
    return RedirectResponse("/ingredientes")


@router.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return _pagina(request, "login.html", "Iniciar sesión")


@router.get("/registro", response_class=HTMLResponse)
def registro(request: Request):
    return _pagina(request, "register.html", "Crear cuenta")


@router.get("/ingredientes", response_class=HTMLResponse)
def ingredientes(request: Request):
    return _pagina(request, "ingredients.html", "Mi inventario")


@router.get("/recetas", response_class=HTMLResponse)
def recetas(request: Request):
    return _pagina(request, "recipes.html", "Mis recetas")
