from fastapi import FastAPI

app = FastAPI(
    title="FlowerAI API",
    description="AI-powered bouquet recommendation platform.",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"message": "FlowerAI API is running"}