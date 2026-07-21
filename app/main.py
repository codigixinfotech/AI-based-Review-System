from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .database import engine, Base, get_db
from .routes import admin, client
from . import models
import os

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Review QR Automation")

@app.on_event("startup")
def startup_populate_services():
    from .database import SessionLocal
    db = SessionLocal()
    try:
        if db.query(models.Service).count() == 0:
            default_services = [
                "SEO Optimization", "Social Media Marketing", "Pay-Per-Click (PPC)",
                "Content Marketing", "Email Marketing", "Web Development",
                "Graphic Designing", "Video Editing"
            ]
            for s_name in default_services:
                db.add(models.Service(name=s_name))
            db.commit()
    finally:
        db.close()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routes
app.include_router(admin.router)
app.include_router(client.router)

@app.get("/", tags=["UI"])
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/review/{token}", tags=["UI"])
def review_page(request: Request, token: str):
    return templates.TemplateResponse(request, "review.html", {"token": token})

@app.get("/admin/panel", tags=["UI"])
def admin_panel(request: Request):
    return templates.TemplateResponse(request, "admin.html")
