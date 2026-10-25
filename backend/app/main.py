from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import auth, users, athletes, sessions, ws_pose

app = FastAPI(
    title="AthletiQ API",
    description="Backend for AthletiQ: Real-Time Athlete Performance Analysis System",
    version="1.0.0",
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(athletes.router, prefix="/api/athletes", tags=["Athletes"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(ws_pose.router, prefix="/ws", tags=["WebSocket"])

@app.get("/")
def read_root():
    return {"message": "Welcome to AthletiQ API"}

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Backend is running"}
