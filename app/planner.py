import random
from collections import defaultdict
from typing import Dict, List
from sqlalchemy.orm import Session
from .models import Recipe, Plan, PlanRecipe, GroceryItem, Setting
import json

def _caps_for_user(db: Session, user_id: int) -> Dict[str, int]:
    rec = db.query(Setting).filter(Setting.user_id == user_id, Setting.key == "cuisine_caps").first()
    if not rec:
        return {}
    try:
        return json.loads(rec.value) or {}
    except Exception:
        return {}

def choose_week(recipes: List[Recipe], days: int, caps: Dict[str, int]) -> List[Recipe]:
    # Group in insertion order (recipes is already ordered by id ascending)
    by_cuisine: Dict[str, List[Recipe]] = defaultdict(list)
    for r in recipes:
        by_cuisine[r.cuisine].append(r)

    chosen: List[Recipe] = []

    # First pass: satisfy caps in deterministic order
    for cuisine, cap in caps.items():
        if cap <= 0:
            continue
        pool = by_cuisine.get(cuisine, [])
        chosen.extend(pool[:cap])

    # Second pass: fill remaining with any recipes not yet chosen, still respecting caps
    for r in recipes:
        if len(chosen) >= days:
            break
        if r in chosen:
            continue
        if r.cuisine in caps:
            already = sum(1 for x in chosen if x.cuisine == r.cuisine)
            if already >= caps[r.cuisine]:
                continue
        chosen.append(r)

    return chosen[:days]

def aggregate_groceries(recipes: List[Recipe]) -> Dict[tuple, dict]:
    agg = {}
    for r in recipes:
        for it in r.items:
            name = it.ingredient.name.strip()
            unit = (it.unit or "").strip().lower()
            key = (name.lower(), unit)
            if key not in agg:
                agg[key] = {"name": name, "unit": unit, "quantity": 0.0}
            agg[key]["quantity"] += float(it.quantity or 0.0)
    return agg

def create_plan(db: Session, user_id: int, days: int, caps_override: Dict[str, int] | None = None) -> Plan:
    caps = caps_override if caps_override is not None else _caps_for_user(db, user_id)
    recipes = db.query(Recipe).filter(Recipe.user_id == user_id).order_by(Recipe.id.asc()).all()
    if not recipes:
        raise ValueError("No recipes found for user.")
    chosen = choose_week(recipes, days, caps)
    plan = Plan(user_id=user_id, days=days, locked=1)
    db.add(plan); db.flush()

    for idx, r in enumerate(chosen):
        db.add(PlanRecipe(plan_id=plan.id, recipe_id=r.id, day_index=idx))

    agg = aggregate_groceries(chosen)
    for (_, _), meta in agg.items():
        db.add(GroceryItem(plan_id=plan.id, name=meta["name"], unit=meta["unit"], quantity=round(meta["quantity"], 2), checked=0))

    db.commit(); db.refresh(plan)
    return plan
