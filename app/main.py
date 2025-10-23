from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from .database import Base, engine
from .models import User
from .deps import current_user
from .auth import router as auth_router
from .routers.recipes import router as recipes_router
from .routers.settings import router as settings_router
from .routers.plans import router as plans_router
from .routers.grocery import router as grocery_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Family Meal Planner", version="0.2.0")

@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})

@app.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email}

# mount routers
app.include_router(auth_router)
app.include_router(recipes_router)
app.include_router(settings_router)
app.include_router(plans_router)
app.include_router(grocery_router)
