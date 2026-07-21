from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None

class ServiceCreate(ServiceBase):
    pass

class Service(ServiceBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class ReviewRequestBase(BaseModel):
    client_name: Optional[str] = None
    client_industry: Optional[str] = None
    google_place_id: Optional[str] = None
    allowed_services: Optional[str] = None

class ReviewRequestCreate(ReviewRequestBase):
    pass

class ReviewRequest(ReviewRequestBase):
    id: int
    token: str
    is_active: bool
    created_at: datetime
    scanned_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class ReviewSubmit(BaseModel):
    token: str
    service_ids: List[int]
    rating: str # "Poor", "Good", "Excellent"
    email: Optional[EmailStr] = None

class ReviewResponse(BaseModel):
    id: int
    ai_generated_text: str
    service_name: str
    rating: str
    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_requests: int
    total_scans: int
    total_submissions: int
    conversion_rate: float
    recent_reviews: List[ReviewResponse]
    class Config:
        from_attributes = True

class SettingUpdate(BaseModel):
    value: str

class SettingResponse(BaseModel):
    key: str
    value: str
    class Config:
        from_attributes = True
