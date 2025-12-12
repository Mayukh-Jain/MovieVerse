import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

def get_movies_by_year(year: int):
    url = f"{BASE_URL}/discover/movie"
    params = {
        "api_key": API_KEY,
        "primary_release_year": year,
        "sort_by": "vote_count.desc"
    }
    
    try:
        # We add a timeout so it doesn't hang forever
        # verify=False helps if you have strict Windows Firewall/Antivirus (Use with caution in prod)
        response = requests.get(url, params=params, timeout=10) 
        response.raise_for_status() # Raises error if status is 4xx or 5xx
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"\n[TMDB ERROR] Could not fetch movies: {e}")
        # Return an empty list so the server stays alive
        return {"results": []}

def get_movie_details(movie_name: str):
    search_url = f"{BASE_URL}/search/movie"
    params = {"api_key": API_KEY, "query": movie_name}
    
    try:
        search_res = requests.get(search_url, params=params, timeout=10)
        search_data = search_res.json()
        
        if not search_data.get('results'):
            return None
            
        movie_id = search_data['results'][0]['id']
        
        details_url = f"{BASE_URL}/movie/{movie_id}"
        details_params = {"api_key": API_KEY, "append_to_response": "recommendations,credits"}
        
        return requests.get(details_url, params=details_params, timeout=10).json()
        
    except requests.exceptions.RequestException:
        print(f"[TMDB ERROR] Failed to get details for {movie_name}")
        return None