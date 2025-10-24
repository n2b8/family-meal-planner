from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import json

from .deps import get_db, current_user, current_user_optional
from .models import User, Recipe, Ingredient, RecipeIngredient, Setting, Plan, PlanRecipe, GroceryItem
from .planner import create_plan

router = APIRouter()

# Jinja templates
templates = Jinja2Templates(directory="app/templates")

# ---------- Auth pages ----------
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: Optional[User] = Depends(current_user_optional)):
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("auth_login.html", {"request": request})

@router.post("/login")
def login_post(request: Request):
    # Handled by /auth/login JSON API from JS fetch. Keep route for completeness or redirect.
    return RedirectResponse("/login", status_code=303)

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user: Optional[User] = Depends(current_user_optional)):
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("auth_register.html", {"request": request})

@router.post("/logout")
def logout_form():
    # The /auth/logout API is used by JS; this exists for graceful POST fallback.
    return RedirectResponse("/login", status_code=303)

# ---------- Home / Plan ----------
@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    # Load caps (safe JSON parse)
    caps_rec = db.query(Setting).filter(Setting.user_id == user.id, Setting.key == "cuisine_caps").first()
    try:
        caps = (json.loads(caps_rec.value) if caps_rec and caps_rec.value else {}) or {}
    except Exception:
        caps = {}

    # Get latest plan (if any)
    current_plan = (
        db.query(Plan)
        .filter(Plan.user_id == user.id)
        .order_by(Plan.id.desc())
        .first()
    )

    plan_data = None
    if current_plan:
        recipes = (
            db.query(PlanRecipe)
            .filter(PlanRecipe.plan_id == current_plan.id)
            .order_by(PlanRecipe.day_index)
            .all()
        )
        groceries = (
            db.query(GroceryItem)
            .filter(GroceryItem.plan_id == current_plan.id)
            .order_by(GroceryItem.name)
            .all()
        )
        plan_data = {"plan": current_plan, "recipes": recipes, "groceries": groceries}

    # Always render the template; never return empty content
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "user": user, "caps": caps, "plan": plan_data}
    )

@router.post("/plan/new")
def plan_new(days: int = Form(7), request: Request = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    # replace any existing plan for simplicity (one active plan per user)
    old = db.query(Plan).filter(Plan.user_id == user.id).all()
    for p in old:
        db.delete(p)
    db.commit()
    try:
        create_plan(db, user.id, days, None)
    except ValueError:
        # e.g., no recipes yet
        return RedirectResponse("/recipes", status_code=303)
    return RedirectResponse("/", status_code=303)

@router.post("/plan/reroll")
def plan_reroll(user: User = Depends(current_user), db: Session = Depends(get_db)):
    # delete and recreate
    current = db.query(Plan).filter(Plan.user_id == user.id).order_by(Plan.id.desc()).first()
    days = current.days if current else 7
    if current:
        db.delete(current); db.commit()
    create_plan(db, user.id, days, None)
    return RedirectResponse("/", status_code=303)

# ---------- Grocery checkbox toggle ----------
@router.post("/grocery/toggle")
def grocery_toggle(item_id: int = Form(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    gi = db.query(GroceryItem).filter(GroceryItem.id == item_id).first()
    if not gi:
        raise HTTPException(404, "Not found")
    plan = db.query(Plan).filter(Plan.id == gi.plan_id, Plan.user_id == user.id).first()
    if not plan:
        raise HTTPException(403, "Forbidden")
    gi.checked = 0 if gi.checked else 1
    db.commit()
    return RedirectResponse("/", status_code=303)

# ---------- Settings (Cuisine caps) ----------
@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    rec = db.query(Setting).filter(Setting.user_id == user.id, Setting.key == "cuisine_caps").first()
    text = rec.value if rec else "{}"
    return templates.TemplateResponse("settings.html", {"request": request, "user": user, "caps_json": text})

@router.post("/settings")
def settings_save(cuisine_caps_json: str = Form("{}"), user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        parsed = json.loads(cuisine_caps_json)
        assert isinstance(parsed, dict)
        for k, v in parsed.items():
            assert isinstance(k, str) and isinstance(v, int) and v >= 0
    except Exception:
        raise HTTPException(400, "Invalid JSON for cuisine caps. Use e.g. {\"Mexican\":2, \"Asian\":1}")
    rec = db.query(Setting).filter(Setting.user_id == user.id, Setting.key == "cuisine_caps").first()
    if not rec:
        rec = Setting(user_id=user.id, key="cuisine_caps", value=json.dumps(parsed))
        db.add(rec)
    else:
        rec.value = json.dumps(parsed)
    db.commit()
    return RedirectResponse("/settings", status_code=303)

# ---------- Recipes ----------
@router.get("/recipes", response_class=HTMLResponse)
def recipes_list(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    recipes = db.query(Recipe).filter(Recipe.user_id == user.id).order_by(Recipe.name).all()
    return templates.TemplateResponse("recipes.html", {"request": request, "user": user, "recipes": recipes})

@router.get("/recipes/new", response_class=HTMLResponse)
def recipes_new(request: Request, user: User = Depends(current_user)):
    return templates.TemplateResponse("recipe_form.html", {"request": request, "user": user, "recipe": None, "items_json": "[]"} )

@router.post("/recipes/new")
def recipes_create(
    name: str = Form(...),
    cuisine: str = Form(...),
    notes: str = Form(""),
    items_json: str = Form("[]"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    try:
        items = json.loads(items_json)
    except Exception:
        items = []
    r = Recipe(user_id=user.id, name=name.strip(), cuisine=cuisine.strip(), notes=notes.strip())
    db.add(r); db.flush()
    for item in items:
        iname = (item.get("ingredient_name") or "").strip()
        if not iname:
            continue
        ing = db.query(Ingredient).filter(Ingredient.name.ilike(iname)).first()
        if not ing:
            ing = Ingredient(name=iname); db.add(ing); db.flush()
        db.add(RecipeIngredient(recipe_id=r.id, ingredient_id=ing.id,
                                quantity=float(item.get("quantity") or 0), unit=(item.get("unit") or "").strip()))
    db.commit()
    return RedirectResponse("/recipes", status_code=303)

@router.get("/recipes/{rid}", response_class=HTMLResponse)
def recipes_edit(rid: int, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.query(Recipe).filter(Recipe.id == rid, Recipe.user_id == user.id).first()
    if not r:
        raise HTTPException(404, "Not found")
    items = [{
        "ingredient_name": link.ingredient.name,
        "quantity": link.quantity,
        "unit": link.unit
    } for link in r.items]
    return templates.TemplateResponse("recipe_form.html", {"request": request, "user": user, "recipe": r, "items_json": json.dumps(items)})

@router.post("/recipes/{rid}")
def recipes_update(
    rid: int,
    name: str = Form(...),
    cuisine: str = Form(...),
    notes: str = Form(""),
    items_json: str = Form("[]"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    r = db.query(Recipe).filter(Recipe.id == rid, Recipe.user_id == user.id).first()
    if not r:
        raise HTTPException(404, "Not found")
    r.name = name.strip()
    r.cuisine = cuisine.strip()
    r.notes = notes.strip()
    for link in list(r.items):
        db.delete(link)
    try:
        items = json.loads(items_json)
    except Exception:
        items = []
    for item in items:
        iname = (item.get("ingredient_name") or "").strip()
        if not iname:
            continue
        ing = db.query(Ingredient).filter(Ingredient.name.ilike(iname)).first()
        if not ing:
            ing = Ingredient(name=iname); db.add(ing); db.flush()
        db.add(RecipeIngredient(recipe_id=r.id, ingredient_id=ing.id,
                                quantity=float(item.get("quantity") or 0), unit=(item.get("unit") or "").strip()))
    db.commit()
    return RedirectResponse("/recipes", status_code=303)

@router.post("/recipes/{rid}/delete")
def recipes_delete(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.query(Recipe).filter(Recipe.id == rid, Recipe.user_id == user.id).first()
    if r:
        db.delete(r); db.commit()
    return RedirectResponse("/recipes", status_code=303)
