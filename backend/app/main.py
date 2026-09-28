"""FastAPI application entry point for FlowerAI."""

from fastapi import FastAPI

from app.routers.flowers import router as flowers_router
from app.routers.recommendations import router as recommendations_router

app = FastAPI(
    title="FlowerAI API",
    description="AI-powered bouquet recommendation platform.",
    version="0.1.0",
)

app.include_router(recommendations_router)
app.include_router(flowers_router)


@app.get("/")
def root():
    """Return a basic status message for the FlowerAI API."""
    return {"message": "FlowerAI API is running"}
