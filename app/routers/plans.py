from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict
from sqlalchemy.orm import Session
from ..deps import current_user, get_db
from ..models import User, Plan, PlanRecipe, GroceryItem
from ..planner import create_plan

router = APIRouter(prefix="/plans", tags=["plans"])

class PlanIn(BaseModel):
    days: int = 7
    cuisine_caps: Dict[str, int] | None = None

@router.post("", response_model=dict)
def generate_plan(data: PlanIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if data.days < 1 or data.days > 14:
        raise HTTPException(400, "days must be between 1 and 14")
    plan = create_plan(db, user.id, data.days, data.cuisine_caps)
    return {"id": plan.id, "days": plan.days}

@router.get("/{pid}", response_model=dict)
def get_plan(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.id == pid, Plan.user_id == user.id).first()
    if not plan:
        raise HTTPException(404, "Not found")
    recipes = db.query(PlanRecipe).filter(PlanRecipe.plan_id == plan.id).order_by(PlanRecipe.day_index).all()
    groceries = db.query(GroceryItem).filter(GroceryItem.plan_id == plan.id).order_by(GroceryItem.name).all()
    return {
        "id": plan.id,
        "days": plan.days,
        "recipes": [{"day_index": pr.day_index, "id": pr.recipe_id, "name": pr.recipe.name, "cuisine": pr.recipe.cuisine} for pr in recipes],
        "groceries": [{"id": g.id, "name": g.name, "unit": g.unit, "quantity": g.quantity, "checked": bool(g.checked)} for g in groceries],
    }
