from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import User
from .config import SESSION_COOKIE_NAME
from .security import read_session_token

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    uid = read_session_token(token)
    if not uid:
        return None
    return db.get(User, uid)

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = current_user_optional(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user
