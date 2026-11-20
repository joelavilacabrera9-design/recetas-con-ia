from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ingredient, User
from app.schemas.ingredient import IngredientCreate, IngredientOut
from app.security import get_current_user
from app.services import catalogo

router = APIRouter(prefix="/api/ingredients", tags=["Ingredientes"])

MAX_INGREDIENTES = 50


def _obtener(db: Session, ingrediente_id: int, user: User) -> Ingredient:
    ing = db.get(Ingredient, ingrediente_id)
    if ing is None or ing.usuario_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingrediente no encontrado")
    return ing


def _existe_nombre(db: Session, user: User, nombre: str, excluir_id: int | None = None) -> bool:
    q = select(Ingredient.id).where(Ingredient.usuario_id == user.id, Ingredient.nombre == nombre)
    if excluir_id is not None:
        q = q.where(Ingredient.id != excluir_id)
    return db.scalar(q) is not None


def _guardar(db: Session, ing: Ingredient) -> Ingredient:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya tienes ese ingrediente") from None
    db.refresh(ing)
    return ing


@router.get("", response_model=list[IngredientOut])
def listar(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lista el inventario del usuario en orden alfabético."""
    return db.scalars(
        select(Ingredient).where(Ingredient.usuario_id == user.id).order_by(Ingredient.nombre)
    ).all()


@router.post("", response_model=IngredientOut, status_code=status.HTTP_201_CREATED)
def crear(
    datos: IngredientCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Agrega un ingrediente al inventario."""
    if _existe_nombre(db, user, datos.nombre):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya tienes ese ingrediente")
    total = db.scalar(
        select(func.count(Ingredient.id)).where(Ingredient.usuario_id == user.id)
    )
    if total >= MAX_INGREDIENTES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Máximo {MAX_INGREDIENTES} ingredientes"
        )
    ing = Ingredient(usuario_id=user.id, **datos.model_dump())
    db.add(ing)
    return _guardar(db, ing)


@router.get("/catalogo", response_model=list[str])
def catalogo_ingredientes(_: User = Depends(get_current_user)):
    """Ingredientes reconocidos (para autocompletar en el formulario)."""
    return catalogo.listar()


@router.get("/{ingrediente_id}", response_model=IngredientOut)
def obtener(
    ingrediente_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _obtener(db, ingrediente_id, user)


@router.put("/{ingrediente_id}", response_model=IngredientOut)
def actualizar(
    ingrediente_id: int,
    datos: IngredientCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reemplaza nombre, cantidad y unidad de un ingrediente."""
    ing = _obtener(db, ingrediente_id, user)
    if _existe_nombre(db, user, datos.nombre, excluir_id=ing.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya tienes ese ingrediente")
    for campo, valor in datos.model_dump().items():
        setattr(ing, campo, valor)
    return _guardar(db, ing)


@router.delete("/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    ingrediente_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ing = _obtener(db, ingrediente_id, user)
    db.delete(ing)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
