import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI(title="Kanban App API")

@app.get("/api/hello")
def hello_world():
    return {"message": "Hello World"}

# Mount the static directory to serve the frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    @app.get("/", response_class=HTMLResponse)
    def default_home():
        return "<h1>Static folder not found. API is running.</h1>"
