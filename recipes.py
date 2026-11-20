from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Ingredient, Rating, Recipe, User
from app.schemas.recipe import GenerateRequest, RatingIn, RatingOut, RecipeOut
from app.security import get_current_user
from app.services.llm_service import LLMServiceError, get_llm_service

router = APIRouter(prefix="/api/recipes", tags=["Recetas"])


def _a_salida(receta: Recipe) -> RecipeOut:
    return RecipeOut(
        id=receta.id,
        nombre=receta.nombre,
        ingredientes=receta.ingredientes,
        pasos=receta.pasos,
        tiempo_minutos=receta.tiempo_minutos,
        dificultad=receta.dificultad,
        inventario_usado=receta.inventario_usado,
        modelo_llm=receta.modelo_llm,
        calificacion=receta.calificacion.estrellas if receta.calificacion else None,
        creado_en=receta.creado_en,
    )


def _obtener(db: Session, receta_id: int, user: User) -> Recipe:
    receta = db.get(Recipe, receta_id)
    if receta is None or receta.usuario_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receta no encontrada")
    return receta


@router.post("/generate", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def generar(
    datos: GenerateRequest | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    llm=Depends(get_llm_service),
):
    """Genera una receta con el LLM a partir del inventario actual y la guarda."""
    datos = datos or GenerateRequest()
    inventario = db.scalars(
        select(Ingredient).where(Ingredient.usuario_id == user.id).order_by(Ingredient.nombre)
    ).all()
    if not inventario:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Tu inventario está vacío. Agrega ingredientes antes de generar una receta.",
        )

    # Nombres de las últimas recetas, para pedir algo distinto.
    recientes = db.scalars(
        select(Recipe.nombre)
        .where(Recipe.usuario_id == user.id)
        .order_by(Recipe.creado_en.desc(), Recipe.id.desc())
        .limit(5)
    ).all()

    try:
        receta_llm = llm.generate_recipe(
            inventario,
            datos.preferencias,
            datos.porciones,
            evitar=list(recientes),
            tipo=datos.tipo.value if datos.tipo else None,
        )
    except LLMServiceError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    receta = Recipe(
        usuario_id=user.id,
        **receta_llm.model_dump(mode="json"),
        inventario_usado=[i.nombre for i in inventario],
        modelo_llm=llm.model_name,
    )
    db.add(receta)
    db.commit()
    db.refresh(receta)
    return _a_salida(receta)


@router.get("", response_model=list[RecipeOut])
def historial(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Historial de recetas generadas, de la más reciente a la más antigua."""
    recetas = db.scalars(
        select(Recipe)
        .where(Recipe.usuario_id == user.id)
        .options(selectinload(Recipe.calificacion))
        .order_by(Recipe.creado_en.desc(), Recipe.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [_a_salida(r) for r in recetas]


@router.get("/{receta_id}", response_model=RecipeOut)
def detalle(
    receta_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _a_salida(_obtener(db, receta_id, user))


@router.put("/{receta_id}/rating", response_model=RatingOut)
def calificar(
    receta_id: int,
    datos: RatingIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Califica una receta de 1 a 5 estrellas (crea o actualiza la calificación)."""
    receta = _obtener(db, receta_id, user)
    if receta.calificacion is None:
        receta.calificacion = Rating(usuario_id=user.id, estrellas=datos.estrellas)
    else:
        receta.calificacion.estrellas = datos.estrellas
    db.commit()
    return RatingOut(receta_id=receta.id, estrellas=datos.estrellas)


@router.delete("/{receta_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    receta_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Elimina una receta del historial (y su calificación)."""
    receta = _obtener(db, receta_id, user)
    db.delete(receta)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
