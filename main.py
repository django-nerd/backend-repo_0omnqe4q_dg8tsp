import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson.objectid import ObjectId
import random

from database import db, create_document, get_documents
from schemas import Recipe as RecipeSchema, Review as ReviewSchema, Favorite as FavoriteSchema, ShoppingList as ShoppingListSchema, SavedRecipe as SavedRecipeSchema, Cooked as CookedSchema

app = FastAPI(title="CookBook API", description="Modern cooking backend with recipes, filters, and user features")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers
class RecipeCreate(BaseModel):
    recipe: RecipeSchema


def to_obj_id(id_str: str):
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")


@app.get("/")
def root():
    return {"message": "CookBook API running"}


@app.get("/test")
def test_database():
    info = {"backend": "running", "db": "disconnected", "collections": []}
    try:
        if db is None:
            return info
        info["db"] = "connected"
        info["collections"] = db.list_collection_names()
    except Exception as e:
        info["db_error"] = str(e)
    return info


UNSPLASH = [
    "https://images.unsplash.com/photo-1523986371872-9d3ba2e2f642?q=80&w=1600&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1604908554007-5a2f89bdf3ee?q=80&w=1600&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1542444459-db63c9f6b3c6?q=80&w=1600&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1551183053-bf91a1d81141?q=80&w=1600&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1544025162-d76694265947?q=80&w=1600&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=1600&auto=format&fit=crop",
]

CUISINES = ["Italian","American","Mexican","Indian","Thai","Chinese","French","Japanese","Mediterranean"]
DIETS = ["vegan","vegetarian","gluten-free","dairy-free","keto","paleo"]
TAGS = ["quick","healthy","comfort","weeknight","spicy","low-carb","one-pot"]

# Seed demo recipes with images
@app.post("/api/seed")
def seed():
    if db is None:
        raise HTTPException(500, "Database not available")
    count = db["recipe"].count_documents({})
    if count >= 24:
        return {"message": "Already seeded", "count": count}

    titles = [
        "Creamy Tomato Pasta","Lemon Herb Chicken","Vegan Buddha Bowl","Spicy Tofu Stir-fry","Garlic Butter Shrimp","Mushroom Risotto","Avocado Toast Deluxe","Beef Tacos","Margherita Pizza","Quinoa Salad","Teriyaki Salmon","Chicken Curry","Pancakes Stack","Greek Gyros","Pad Thai","Shakshuka","Falafel Wrap","Burrito Bowl","Caprese Salad","Ramen Bowl","Pesto Pasta","BBQ Chicken","Veggie Omelette","Citrus Salmon"
    ]

    demo_recipes: List[dict] = []
    for t in titles:
        ing = [
            {"name": "salt", "amount": "to taste"},
            {"name": "pepper", "amount": "to taste"},
            {"name": "garlic", "amount": f"{random.randint(1,4)} cloves"},
        ]
        ing += [{"name": random.choice(["chicken","beef","tofu","shrimp","pasta","quinoa","rice","tomato","onion","lemon","spinach"]), "amount": f"{random.randint(1,3)} cups"} for _ in range(3)]
        steps = [
            "Prep ingredients.",
            "Cook main components.",
            "Combine, season and serve warm.",
        ]
        demo_recipes.append({
            "title": t,
            "description": f"Delicious {t.lower()} made easy with pantry staples.",
            "ingredients": ing,
            "steps": steps,
            "cuisine": random.choice(CUISINES),
            "difficulty": random.choice(["easy","medium","hard"]),
            "prep_time_min": random.randint(5,25),
            "cook_time_min": random.randint(5,35),
            "dietary": random.sample(DIETS, k=random.randint(0,2)),
            "tags": random.sample(TAGS, k=random.randint(1,3)),
            "image_url": random.choice(UNSPLASH),
            "rating": round(random.uniform(3.8, 5.0), 1),
            "rating_count": random.randint(10, 800),
            "nutrition": {"calories": random.randint(250, 700), "protein_g": random.randint(8,40), "carbs_g": random.randint(20,90), "fat_g": random.randint(5,30)}
        })

    for r in demo_recipes:
        create_document("recipe", r)
    return {"message": "Seeded", "count": len(demo_recipes)}


# Recipes CRUD and filters
@app.get("/api/recipes")
def list_recipes(
    q: Optional[str] = None,
    ingredients: Optional[str] = None, # comma-separated
    difficulty: Optional[str] = None,
    cuisine: Optional[str] = None,
    max_prep: Optional[int] = Query(None, ge=0),
    dietary: Optional[str] = None,  # comma-separated
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    limit: int = Query(30, ge=1, le=100)
):
    if db is None:
        raise HTTPException(500, "Database not available")

    filt = {}
    if q:
        filt["title"] = {"$regex": q, "$options": "i"}
    if ingredients:
        ing_list = [i.strip().lower() for i in ingredients.split(",") if i.strip()]
        filt["ingredients.name"] = {"$all": ing_list}
    if difficulty:
        filt["difficulty"] = difficulty
    if cuisine:
        filt["cuisine"] = cuisine
    if max_prep is not None:
        filt["prep_time_min"] = {"$lte": max_prep}
    if dietary:
        filt["dietary"] = {"$all": [d.strip().lower() for d in dietary.split(",") if d.strip()]}
    if min_rating is not None:
        filt["rating"] = {"$gte": min_rating}

    items = list(db["recipe"].find(filt).limit(limit))
    for it in items:
        it["id"] = str(it.pop("_id"))
    return {"items": items}


@app.get("/api/recipes/{recipe_id}")
def get_recipe(recipe_id: str):
    if db is None:
        raise HTTPException(500, "Database not available")
    doc = db["recipe"].find_one({"_id": to_obj_id(recipe_id)})
    if not doc:
        raise HTTPException(404, "Recipe not found")
    doc["id"] = str(doc.pop("_id"))
    # attach reviews
    reviews = list(db["review"].find({"recipe_id": recipe_id}))
    for r in reviews:
        r["id"] = str(r.pop("_id"))
    doc["reviews"] = reviews
    return doc


@app.post("/api/recipes")
def create_recipe(payload: RecipeCreate):
    if db is None:
        raise HTTPException(500, "Database not available")
    rid = create_document("recipe", payload.recipe.model_dump())
    return {"id": rid}


# What can I cook? based on ingredients
class PantryRequest(BaseModel):
    ingredients: List[str]

@app.post("/api/suggest")
def suggest_recipes(body: PantryRequest, limit: int = 12):
    if db is None:
        raise HTTPException(500, "Database not available")
    have = [x.strip().lower() for x in body.ingredients if x.strip()]
    if not have:
        return {"items": []}
    # score recipes by overlap
    items = list(db["recipe"].find({"ingredients.name": {"$in": have}}))
    scored = []
    for it in items:
        names = [i.get("name", "").lower() for i in it.get("ingredients", [])]
        match = len(set(have) & set(names))
        missing = len([n for n in names if n not in have])
        score = match - 0.2 * missing + (it.get("rating", 0) * 0.05)
        it["id"] = str(it.pop("_id"))
        scored.append((score, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return {"items": [it for _, it in scored[:limit]]}


# Reviews
@app.post("/api/recipes/{recipe_id}/reviews")
def add_review(recipe_id: str, review: ReviewSchema):
    if db is None:
        raise HTTPException(500, "Database not available")
    if review.recipe_id != recipe_id:
        raise HTTPException(400, "Mismatched recipe id")
    create_document("review", review)
    return {"ok": True}


# User dashboard data: favorites, saved, cooked, shopping list
@app.get("/api/user/summary")
def user_summary(user: str):
    if db is None:
        raise HTTPException(500, "Database not available")
    fav = list(db["favorite"].find({"user_email": user}))
    saved = list(db["savedrecipe"].find({"user_email": user}))
    cooked = list(db["cooked"].find({"user_email": user}))
    sl = db["shoppinglist"].find_one({"user_email": user}) or {"items": []}
    for col in (fav, saved, cooked):
        for d in col:
            d["id"] = str(d.pop("_id"))
    return {"favorites": fav, "saved": saved, "cooked": cooked, "shopping_list": sl.get("items", [])}


@app.post("/api/user/favorites")
def set_favorite(fav: FavoriteSchema):
    if db is None:
        raise HTTPException(500, "Database not available")
    existing = db["favorite"].find_one({"user_email": fav.user_email, "recipe_id": fav.recipe_id})
    if existing:
        db["favorite"].delete_one({"_id": existing["_id"]})
        return {"favorited": False}
    create_document("favorite", fav)
    return {"favorited": True}


@app.post("/api/user/saved")
def toggle_saved(s: SavedRecipeSchema):
    if db is None:
        raise HTTPException(500, "Database not available")
    existing = db["savedrecipe"].find_one({"user_email": s.user_email, "recipe_id": s.recipe_id})
    if existing:
        db["savedrecipe"].delete_one({"_id": existing["_id"]})
        return {"saved": False}
    create_document("savedrecipe", s)
    return {"saved": True}


@app.post("/api/user/cooked")
def toggle_cooked(c: CookedSchema):
    if db is None:
        raise HTTPException(500, "Database not available")
    existing = db["cooked"].find_one({"user_email": c.user_email, "recipe_id": c.recipe_id})
    if existing:
        db["cooked"].delete_one({"_id": existing["_id"]})
        return {"cooked": False}
    create_document("cooked", c)
    return {"cooked": True}


@app.post("/api/user/shopping-list")
def update_shopping_list(sl: ShoppingListSchema):
    if db is None:
        raise HTTPException(500, "Database not available")
    db["shoppinglist"].update_one({"user_email": sl.user_email}, {"$set": {"items": sl.items}}, upsert=True)
    return {"ok": True}
