from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from .. import models, schemas, services, database
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
import io

router = APIRouter(tags=["client"])

@router.get("/r/{token}")
def handle_qr_scan(token: str, db: Session = Depends(database.get_db)):
    req = services.DBService.get_request_by_token(db, token)
    if not req or not req.is_active:
        raise HTTPException(status_code=404, detail="Invalid or expired review request")
    
    # Log scan analytic
    services.DBService.log_scan(db, req.id)
    return RedirectResponse(url=f"/review/{token}")

@router.get("/services")
def get_services(token: Optional[str] = None, db: Session = Depends(database.get_db)):
    if token:
        req = services.DBService.get_request_by_token(db, token)
        if req and req.allowed_services:
            ids = [int(i) for i in req.allowed_services.split(",") if i.strip()]
            return db.query(models.Service).filter(models.Service.id.in_(ids)).all()
    
    return db.query(models.Service).all()

@router.post("/submit", response_model=schemas.ReviewResponse)
def submit_review(data: schemas.ReviewSubmit, db: Session = Depends(database.get_db)):
    req = services.DBService.get_request_by_token(db, data.token)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Validate email (30 day rule)
    if not services.DBService.validate_email_submission(db, data.email):
        raise HTTPException(status_code=400, detail="You can only submit one review every 30 days.")
    
    services_list = db.query(models.Service).filter(models.Service.id.in_(data.service_ids)).all()
    if not services_list:
        raise HTTPException(status_code=404, detail="Services not found")
    
    # Combined service names for AI
    service_names = ", ".join([s.name for s in services_list])
    
    # Generate AI review text
    ai_text = services.AIService.generate_review_text(service_names, data.rating)
    
    # Store review (linking to the first service for DB simplicity, or you could extend models)
    review = services.DBService.submit_review(
        db, req.id, services_list[0].id, data.rating, data.email, ai_text
    )
    
    # Return response
    return {
        "id": review.id,
        "ai_generated_text": review.ai_generated_text,
        "service_name": service_names,
        "rating": review.rating
    }

@router.get("/config/request/{token}")
def get_request_config(token: str, db: Session = Depends(database.get_db)):
    req = services.DBService.get_request_by_token(db, token)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Get global place_id if not set on request
    place_id = req.google_place_id
    if not place_id:
        setting = db.query(models.Setting).filter(models.Setting.key == "google_place_id").first()
        place_id = setting.value if setting else ""
        
    return {
        "client_name": req.client_name or "Codigix Infotech",
        "client_industry": req.client_industry or "Marketing Agency",
        "place_id": place_id
    }
