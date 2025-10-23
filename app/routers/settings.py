from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict
from sqlalchemy.orm import Session
from ..deps import current_user, get_db
from ..models import Setting, User
import json

router = APIRouter(prefix="/settings", tags=["settings"])

class CapsIn(BaseModel):
    cuisine_caps: Dict[str, int] = {}

@router.post("/caps", response_model=dict)
def set_caps(data: CapsIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    rec = db.query(Setting).filter(Setting.user_id == user.id, Setting.key == "cuisine_caps").first()
    payload = json.dumps(data.cuisine_caps)
    if not rec:
        rec = Setting(user_id=user.id, key="cuisine_caps", value=payload)
        db.add(rec)
    else:
        rec.value = payload
    db.commit()
    return {"ok": True}
