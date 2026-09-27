"""FastAPI application entry point for FlowerAI."""

from fastapi import FastAPI

app = FastAPI(
    title="FlowerAI API",
    description="AI-powered bouquet recommendation platform.",
    version="0.1.0",
)


@app.get("/")
def root():
    """Return a basic status message for the FlowerAI API."""
    return {"message": "FlowerAI API is running"}
