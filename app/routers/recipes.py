from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from ..deps import current_user, get_db
from ..models import Recipe, Ingredient, RecipeIngredient, User

router = APIRouter(prefix="/recipes", tags=["recipes"])

class RecipeItemIn(BaseModel):
    ingredient_name: str
    quantity: float
    unit: str = ""

class RecipeIn(BaseModel):
    name: str
    cuisine: str
    notes: str = ""
    items: List[RecipeItemIn] = []

@router.get("", response_model=list[dict])
def list_recipes(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Recipe).filter(Recipe.user_id == user.id).order_by(Recipe.name).all()
    out = []
    for r in rows:
        out.append({
            "id": r.id,
            "name": r.name,
            "cuisine": r.cuisine,
            "notes": r.notes,
            "items": [{"ingredient_name": it.ingredient.name, "quantity": it.quantity, "unit": it.unit} for it in r.items],
        })
    return out

@router.post("", response_model=dict)
def create_recipe(data: RecipeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    existing = db.query(Recipe).filter(Recipe.user_id == user.id, Recipe.name == data.name.strip()).first()
    if existing:
        raise HTTPException(400, "Recipe name already exists.")
    r = Recipe(user_id=user.id, name=data.name.strip(), cuisine=data.cuisine.strip(), notes=data.notes.strip())
    db.add(r); db.flush()

    for i in data.items:
        ing = db.query(Ingredient).filter(Ingredient.name.ilike(i.ingredient_name.strip())).first()
        if not ing:
            ing = Ingredient(name=i.ingredient_name.strip())
            db.add(ing); db.flush()
        db.add(RecipeIngredient(recipe_id=r.id, ingredient_id=ing.id, quantity=float(i.quantity or 0), unit=(i.unit or "").strip()))
    db.commit(); db.refresh(r)
    return {"id": r.id}

@router.patch("/{rid}", response_model=dict)
def update_recipe(rid: int, data: RecipeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.query(Recipe).filter(Recipe.id == rid, Recipe.user_id == user.id).first()
    if not r:
        raise HTTPException(404, "Not found")
    r.name = data.name.strip()
    r.cuisine = data.cuisine.strip()
    r.notes = data.notes.strip()
    for link in list(r.items):
        db.delete(link)
    for i in data.items:
        ing = db.query(Ingredient).filter(Ingredient.name.ilike(i.ingredient_name.strip())).first()
        if not ing:
            ing = Ingredient(name=i.ingredient_name.strip()); db.add(ing); db.flush()
        db.add(RecipeIngredient(recipe_id=r.id, ingredient_id=ing.id, quantity=float(i.quantity or 0), unit=(i.unit or "").strip()))
    db.commit()
    return {"ok": True}

@router.delete("/{rid}", response_model=dict)
def delete_recipe(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.query(Recipe).filter(Recipe.id == rid, Recipe.user_id == user.id).first()
    if not r:
        return {"ok": True}
    db.delete(r); db.commit()
    return {"ok": True}
