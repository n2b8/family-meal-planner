from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from .deps import get_db, current_user
from .models import User
from .security import hash_password, verify_password, make_session_token
from .config import SESSION_COOKIE_NAME, SESSION_COOKIE_SECURE, SESSION_COOKIE_SAMESITE

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterIn(BaseModel):
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")
    u = User(email=email, password_hash=hash_password(data.password))
    db.add(u); db.commit(); db.refresh(u)
    return {"id": u.id, "email": u.email}

@router.post("/login")
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    u = db.query(User).filter(User.email == email).first()
    if not u or not verify_password(data.password, u.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = make_session_token(u.id)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        path="/",
    )
    return {"ok": True}

@router.post("/logout")
def logout(response: Response, user=Depends(current_user)):
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"ok": True}
