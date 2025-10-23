from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Family Meal Planner", version="0.0.1")

@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})
