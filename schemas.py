"""
Database Schemas for Cooking App

Each Pydantic model maps to a MongoDB collection (lowercased class name).
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# Users are minimal for this demo (no auth flow). A real app would add auth fields.
class User(BaseModel):
    name: str
    email: str
    avatar_url: Optional[str] = None

class Nutrition(BaseModel):
    calories: Optional[int] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: Optional[int] = None

class Ingredient(BaseModel):
    name: str
    amount: Optional[str] = None  # e.g., "2 cups"

class Recipe(BaseModel):
    title: str
    description: Optional[str] = None
    ingredients: List[Ingredient]
    steps: List[str]
    cuisine: Optional[str] = None
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    prep_time_min: int = Field(..., ge=0)
    cook_time_min: int = Field(0, ge=0)
    dietary: List[str] = []  # e.g., ["vegan", "gluten-free"]
    tags: List[str] = []
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    rating: float = 0.0
    rating_count: int = 0
    nutrition: Optional[Nutrition] = None

class Review(BaseModel):
    recipe_id: str
    user_name: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class Favorite(BaseModel):
    user_email: str
    recipe_id: str

class Cooked(BaseModel):
    user_email: str
    recipe_id: str

class SavedRecipe(BaseModel):
    user_email: str
    recipe_id: str

class ShoppingList(BaseModel):
    user_email: str
    items: List[str]
