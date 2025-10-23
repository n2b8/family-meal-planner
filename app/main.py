from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from .database import Base, engine
from .models import User
from .deps import current_user
from .auth import router as auth_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Family Meal Planner", version="0.1.0")

@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})

@app.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email}

app.include_router(auth_router)
