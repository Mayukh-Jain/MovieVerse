from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from ..services import recommender, tmdb
from .. import models
from fastapi import Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from .auth import get_current_user # We need this to identify WHO is logged inuser # We need this to identify WHO is logged in

# Define the router with the prefix "/movies"
router = APIRouter(prefix="/movies", tags=["Movies"])

# --- 1. SPHERE ENDPOINT (This was missing) ---
@router.get("/sphere/year/{year}")
def get_movies_for_sphere(year: int):
    # Fetch data from TMDB
    data = tmdb.get_movies_by_year(year)
    results = data.get("results", [])
    
    # Format for the 3D Sphere
    sphere_data = [
        {
            "id": m["id"],
            "title": m["title"],
            "poster": f"https://image.tmdb.org/t/p/w500{m['poster_path']}",
            "rating": m["vote_average"],
            "genre": "Unknown" # You can map genre IDs here if you want
        }
        for m in results if m.get('poster_path')
    ]
    return sphere_data[:50] # Limit to 50 items

# --- 2. RECOMMENDATION ENDPOINT ---
@router.get("/recommend/{movie_name}")
def recommend_by_name(movie_name: str):
    data = recommender.get_content_recommendations(movie_name)
    if not data:
        raise HTTPException(status_code=404, detail="Movie not found")
    return data

# --- 3. FILTER ENDPOINT ---
@router.get("/filter")
def filter_movies(
    genre: Optional[str] = None, 
    year: Optional[int] = None, 
    rating: Optional[float] = Query(0, ge=0, le=10)
):
    return recommender.discover_movies(genre, year, rating)

@router.post("/history/add")
def add_to_history(
    movie_title: str, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """
    Saves a movie title to the logged-in user's history.
    """
    # Create the history record
    new_entry = models.SearchHistory(
        user_id=current_user.id, 
        movie_title=movie_title
    )
    db.add(new_entry)
    db.commit()
    return {"status": "success", "msg": f"Saved '{movie_title}' to history"}

@router.get("/history/view")
def view_history(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """
    Returns the user's saved history.
    """
    return db.query(models.SearchHistory).filter(
        models.SearchHistory.user_id == current_user.id
    ).order_by(models.SearchHistory.searched_at.desc()).all()

# ... (Keep existing imports) ...

# --- HELPER: GENRE MAPPING (ID -> Name) ---
# TMDB returns IDs (e.g., 28), but Frontend wants "Action".
GENRE_ID_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 53: "Thriller",
    10752: "War", 37: "Western"
}

# --- THE REQUESTED ENDPOINT ---
# Member A asked for "/api/movies", so we add a route that matches that structure.
@router.get("/api/movies") 
def get_frontend_movies():
    # 1. Fetch popular movies from TMDB
    data = tmdb.get_movies_by_year(2023) # Or use a generic 'popular' fetch
    results = data.get("results", [])

    # 2. TRANSFORM the data to match Member A's exact JSON requirements
    frontend_data = []
    for m in results:
        if not m.get("poster_path"): continue

        # Map Genre IDs to Names
        genres = [GENRE_ID_MAP.get(g_id, "General") for g_id in m.get("genre_ids", [])]

        frontend_data.append({
            "id": m["id"],
            "name": m["title"],  # They want 'name', TMDB has 'title'
            "premiered": m.get("release_date", "2023-01-01"), # They want 'premiered'
            "rating": {
                "average": m["vote_average"] # Nested object as requested
            },
            "genres": genres,
            "image": {
                "original": f"https://image.tmdb.org/t/p/w500{m['poster_path']}" # Nested image object
            },
            "summary": f"<p>{m['overview']}</p>" # They specifically asked for HTML tags
        })
    
    return frontend_data