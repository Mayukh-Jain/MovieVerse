import requests
import os
from dotenv import load_dotenv
from typing import List, Optional, Dict

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

# Map common genres to TMDB IDs for easier lookup
GENRE_MAP = {
    "action": 28, "adventure": 12, "animation": 16, "comedy": 35,
    "crime": 80, "documentary": 99, "drama": 18, "family": 10751,
    "fantasy": 14, "history": 36, "horror": 27, "music": 10402,
    "mystery": 9648, "romance": 10749, "sci-fi": 878, "thriller": 53,
    "war": 10752, "western": 37
}

def get_headers():
    return {
        "accept": "application/json",
        "Authorization": f"Bearer {os.getenv('TMDB_READ_ACCESS_TOKEN')}" # Optional if using Key
    }

def search_movie_id(movie_name: str) -> Optional[int]:
    """
    Helper: Finds the TMDB ID for a given movie name.
    """
    url = f"{BASE_URL}/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": movie_name,
        "language": "en-US",
        "page": 1,
        "include_adult": "false"
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    if data.get("results"):
        # Return the ID of the first (most relevant) result
        return data["results"][0]["id"]
    return None

def get_content_recommendations(movie_name: str) -> List[Dict]:
    """
    SECTION 1: Basic Movie Recommendation
    User puts a movie name -> We find similar movies.
    """
    movie_id = search_movie_id(movie_name)
    if not movie_id:
        return []

    # Endpoint: Get Recommendations based on movie ID
    url = f"{BASE_URL}/movie/{movie_id}/recommendations"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "page": 1
    }
    
    response = requests.get(url, params=params)
    results = response.json().get("results", [])

    # Clean the data for the Frontend
    cleaned_results = []
    for m in results[:12]: # Return top 12
        if m.get("poster_path"): # Only include if it has an image
            cleaned_results.append({
                "id": m["id"],
                "title": m["title"],
                "overview": m["overview"],
                "year": m.get("release_date", "")[:4],
                "rating": m["vote_average"],
                "poster": f"https://image.tmdb.org/t/p/w500{m['poster_path']}"
            })
            
    return cleaned_results

def discover_movies(
    genre: str = None, 
    year: int = None, 
    min_rating: float = 0
) -> List[Dict]:
    """
    SECTION 2: Complex Filtering & Scoring
    User filters by Genre, Year, and Rating.
    """
    url = f"{BASE_URL}/discover/movie"
    
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "page": 1,
        "vote_count.gte": 100 # Only reasonable movies
    }

    # Apply Filters
    if genre and genre.lower() in GENRE_MAP:
        params["with_genres"] = GENRE_MAP[genre.lower()]
    
    if year:
        params["primary_release_year"] = year
        
    if min_rating:
        params["vote_average.gte"] = min_rating

    response = requests.get(url, params=params)
    results = response.json().get("results", [])

    # --- DATA SPECIALIST LOGIC ---
    # Custom Re-Ranking: 
    # The API sorts by 'popularity', but we want a mix of Rating & Popularity.
    # Formula: Score = (Rating * 0.7) + (Popularity_Normalized * 0.3)
    
    processed_movies = []
    for m in results:
        if not m.get("poster_path"): continue

        # Simple normalization for popularity (capping at 100 for math)
        pop_score = min(m["popularity"], 100) / 10
        
        # Weighted Score Calculation
        custom_score = (m["vote_average"] * 0.7) + (pop_score * 0.3)
        
        processed_movies.append({
            "id": m["id"],
            "title": m["title"],
            "poster": f"https://image.tmdb.org/t/p/w500{m['poster_path']}",
            "rating": m["vote_average"],
            "year": m.get("release_date", "N/A")[:4],
            "custom_score": round(custom_score, 2)
        })

    # Sort by our new Custom Score instead of default API order
    processed_movies.sort(key=lambda x: x["custom_score"], reverse=True)

    return processed_movies