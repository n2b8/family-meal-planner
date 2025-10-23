from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..deps import current_user, get_db
from ..models import User, GroceryItem, Plan

router = APIRouter(prefix="/grocery", tags=["grocery"])

@router.post("/{item_id}/toggle", response_model=dict)
def toggle_item(item_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    gi = db.query(GroceryItem).filter(GroceryItem.id == item_id).first()
    if not gi:
        raise HTTPException(404, "Not found")
    # Ownership check via plan
    plan = db.query(Plan).filter(Plan.id == gi.plan_id, Plan.user_id == user.id).first()
    if not plan:
        raise HTTPException(403, "Forbidden")
    gi.checked = 0 if gi.checked else 1
    db.commit()
    return {"id": gi.id, "checked": bool(gi.checked)}
