from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

@app.get("/")
def read_root():
    return {"message": "Welcome to AthletiQ API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
