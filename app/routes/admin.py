from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from .. import models, schemas, services, database
from fastapi.responses import HTMLResponse, StreamingResponse
import io

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/requests", response_model=schemas.ReviewRequest)
def create_review_request(request: schemas.ReviewRequestCreate, db: Session = Depends(database.get_db)):
    return services.DBService.create_review_request(
        db, 
        request.client_name, 
        request.client_industry,
        request.google_place_id,
        request.allowed_services
    )

@router.get("/qr/{token}")
def get_qr_code(token: str, request: Request, db: Session = Depends(database.get_db)):
    req = services.DBService.get_request_by_token(db, token)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    qr_bytes = services.QRService.generate_qr_bytes(token, base_url)
    return Response(
        content=qr_bytes, 
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename=review-qr-{token[:8]}.png"}
    )

@router.get("/card/{token}")
def get_qr_card(token: str, request: Request, db: Session = Depends(database.get_db)):
    req = services.DBService.get_request_by_token(db, token)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    client_name = req.client_name if req.client_name else "Codigix Infotech"
    client_industry = req.client_industry if req.client_industry else "Marketing Agency"
    card_bytes = services.CardService.generate_card(token, base_url, company_name=client_name, industry=client_industry)
    return Response(
        content=card_bytes, 
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename=feedback-card-{token[:8]}.png"}
    )

@router.get("/dashboard", response_model=schemas.DashboardStats)
def get_dashboard_stats(db: Session = Depends(database.get_db)):
    total_requests = db.query(models.ReviewRequest).count()
    total_scans = db.query(models.Analytic).filter(models.Analytic.event_type == "scan").count()
    total_submissions = db.query(models.Review).count()
    
    conversion_rate = (total_submissions / total_scans * 100) if total_scans > 0 else 0
    
    recent_reviews_db = db.query(models.Review).order_by(models.Review.created_at.desc()).limit(10).all()
    
    recent_reviews = []
    for r in recent_reviews_db:
        recent_reviews.append({
            "id": r.id,
            "ai_generated_text": r.ai_generated_text,
            "service_name": r.service.name if r.service else "Unknown",
            "rating": r.rating
        })
    
    return {
        "total_requests": total_requests,
        "total_scans": total_scans,
        "total_submissions": total_submissions,
        "conversion_rate": conversion_rate,
        "recent_reviews": recent_reviews
    }

@router.post("/services", response_model=schemas.Service)
def create_service(service: schemas.ServiceCreate, db: Session = Depends(database.get_db)):
    db_service = models.Service(name=service.name, description=service.description)
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

@router.get("/services", response_model=list[schemas.Service])
def list_services(db: Session = Depends(database.get_db)):
    return db.query(models.Service).all()

@router.get("/settings/{key}", response_model=schemas.SettingResponse)
def get_setting(key: str, db: Session = Depends(database.get_db)):
    setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    if not setting:
        return {"key": key, "value": ""}
    return setting

@router.post("/settings/{key}", response_model=schemas.SettingResponse)
def update_setting(key: str, data: schemas.SettingUpdate, db: Session = Depends(database.get_db)):
    setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    if not setting:
        setting = models.Setting(key=key, value=data.value)
        db.add(setting)
    else:
        setting.value = data.value
    db.commit()
    db.refresh(setting)
    return setting
