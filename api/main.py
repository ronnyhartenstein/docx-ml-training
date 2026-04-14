from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import chat, health

app = FastAPI(title="PPS neo Fachkonzept-Assistent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(health.router, prefix="/api")

# Statische UI-Dateien
ui_dir = Path(__file__).parent.parent / "ui"
if ui_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(ui_dir)), name="assets")


@app.get("/")
async def serve_ui():
    index = ui_dir / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "PPS neo API läuft. UI nicht gefunden."}
