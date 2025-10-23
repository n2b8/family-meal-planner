from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, DateTime, func, ForeignKey, Float, UniqueConstraint
from .database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipes = relationship("Recipe", back_populates="owner", cascade="all, delete-orphan")
    settings = relationship("Setting", back_populates="owner", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="owner", cascade="all, delete-orphan")

class Ingredient(Base):
    __tablename__ = "ingredients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Global namespace is simplest; if you want per-user ingredients later, add user_id
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    links = relationship("RecipeIngredient", back_populates="ingredient")

class Recipe(Base):
    __tablename__ = "recipes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), index=True)
    cuisine: Mapped[str] = mapped_column(String(100), index=True)
    notes: Mapped[str] = mapped_column(String(1000), default="")

    owner = relationship("User", back_populates="recipes")
    items = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_recipe_per_user_name"),)

class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"))
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id", ondelete="CASCADE"))
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(50), default="")

    recipe = relationship("Recipe", back_populates="items")
    ingredient = relationship("Ingredient", back_populates="links")

    __table_args__ = (UniqueConstraint("recipe_id", "ingredient_id", name="uq_recipe_ing"),)

class Setting(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(255), index=True)
    value: Mapped[str] = mapped_column(String(4000))  # JSON blob

    owner = relationship("User", back_populates="settings")
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_setting_per_user_key"),)

class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    days: Mapped[int] = mapped_column(Integer, default=7)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    locked: Mapped[int] = mapped_column(Integer, default=1)  # 1=locked/active, 0=draft (simple flag)

    owner = relationship("User", back_populates="plans")
    plan_recipes = relationship("PlanRecipe", back_populates="plan", cascade="all, delete-orphan")
    groceries = relationship("GroceryItem", back_populates="plan", cascade="all, delete-orphan")

class PlanRecipe(Base):
    __tablename__ = "plan_recipes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id", ondelete="CASCADE"))
    recipe_id: Mapped[int] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"))
    day_index: Mapped[int] = mapped_column(Integer)  # 0..days-1

    plan = relationship("Plan", back_populates="plan_recipes")
    recipe = relationship("Recipe")

    __table_args__ = (UniqueConstraint("plan_id", "day_index", name="uq_plan_day"),)

class GroceryItem(Base):
    __tablename__ = "grocery_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str] = mapped_column(String(50), default="")
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    checked: Mapped[int] = mapped_column(Integer, default=0)  # 0/1

    plan = relationship("Plan", back_populates="groceries")
