from fastapi import FastAPI

app = FastAPI(title="Estetika-Elora")


@app.get("/health")
def health():
    return {"status": "ok"}
