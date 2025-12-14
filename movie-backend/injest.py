import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

# --- CONFIGURATION ---
load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# --- 1. SETUP ROBUST CONNECTION (The Fix) ---
# This creates a "Session" that automatically retries 5 times if the connection drops
session = requests.Session()
retry_strategy = Retry(
    total=5,              # Try 5 times before failing
    backoff_factor=1,     # Wait 1s, 2s, 4s between retries
    status_forcelist=[429, 500, 502, 503, 504], # Retry on these server errors
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

# --- 2. SETUP QDRANT & AI ---
if QDRANT_URL and QDRANT_API_KEY:
    print(f"🌐 Connecting to Qdrant Cloud...")
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
else:
    print("📁 Using Local Qdrant (./qdrant_data)")
    qdrant = QdrantClient(path="./qdrant_data")

print("🧠 Loading AI Model...")
model = SentenceTransformer('all-MiniLM-L6-v2')

COLLECTION_NAME = "movies"
START_PAGE = 1
END_PAGE = 500 

# Create collection if needed
if not qdrant.collection_exists(COLLECTION_NAME):
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

def fetch_and_vectorize():
    total_added = 0
    batch_points = []
    
    print(f"🚀 Starting ingestion: Pages {START_PAGE} to {END_PAGE}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Portfolio Project)",
        "Accept": "application/json"
    }

    for page in range(START_PAGE, END_PAGE + 1):
        url = f"https://api.themoviedb.org/3/movie/top_rated?api_key={TMDB_API_KEY}&language=en-US&page={page}"
        
        try:
            # USE SESSION INSTEAD OF REQUESTS
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status() # Trigger retry logic on error
                
            data = response.json()
            movies = data.get('results', [])

            for movie in movies:
                if not movie.get('overview'): continue

                # Create Vector
                text_content = f"{movie['title']}: {movie['overview']}"
                vector = model.encode(text_content).tolist()
                
                payload = {
                    "title": movie['title'],
                    "overview": movie['overview'],
                    "poster_path": movie.get('poster_path', ""),
                    "release_date": movie.get('release_date', "Unknown"),
                    "vote_average": movie.get('vote_average', 0)
                }
                
                # Use Real ID
                batch_points.append(PointStruct(id=movie['id'], vector=vector, payload=payload))
                total_added += 1

            # Upload Batch
            if len(batch_points) >= 100:
                qdrant.upsert(collection_name=COLLECTION_NAME, points=batch_points)
                print(f"✅ Uploaded batch from page {page}. Total: {total_added}")
                batch_points = []
            
            # Sleep slightly longer to be safer
            time.sleep(0.5)

        except Exception as e:
            # If it still fails after 5 retries, just log it and keep going
            print(f"❌ FAILED page {page} after retries. Error: {e}")

    # Final Batch
    if batch_points:
        qdrant.upsert(collection_name=COLLECTION_NAME, points=batch_points)
        print(f"✅ Uploaded final batch.")

    print(f"🎉 DONE! Total movies: {total_added}")

if __name__ == "__main__":
    fetch_and_vectorize()