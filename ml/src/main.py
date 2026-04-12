from fastapi import FastAPI

app = FastAPI(title="Veridion Fraud Service", version="1.0.0")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "fraud-detection",
        "note": "Placeholder — real model built in Phase 4",
    }
