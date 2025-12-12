from fastapi import FastAPI
from .database import engine, Base
from fastapi.middleware.cors import CORSMiddleware # <--- 1. IMPORT THIS
from .routers import auth, movies  # <--- IMPORT YOUR ROUTERS

# Create Tables (Simple way for dev)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Movie Sphere Backend",
    description="API for Movie Recommendation & 3D Sphere",
    version="1.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (good for dev)
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, etc.
    allow_headers=["*"],
)

# --- PLUG IN THE ROUTERS HERE ---
app.include_router(auth.router)
app.include_router(movies.router) 

@app.get("/")
def root():
    return {"message": "Movie API is running", "status": "active"}

@app.on_event("startup")
def list_routes():
    print("\n--- ACTIVE ROUTES ---")
    for route in app.routes:
        print(f"Path: {route.path}  |  Name: {route.name}")
    print("---------------------\n")