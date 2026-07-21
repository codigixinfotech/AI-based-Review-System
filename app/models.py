from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import relationship
from .database import Base
import datetime
import uuid

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ReviewRequest(Base):
    __tablename__ = "review_requests"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    client_name = Column(String, nullable=True)
    client_industry = Column(String, nullable=True)
    google_place_id = Column(String, nullable=True)
    allowed_services = Column(String, nullable=True) # Comma separated IDs
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    scanned_at = Column(DateTime, nullable=True)
    
    # Relationships
    reviews = relationship("Review", back_populates="request")

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("review_requests.id"))
    service_id = Column(Integer, ForeignKey("services.id"))
    rating = Column(String) # Poor, Good, Excellent
    score = Column(Integer) # 1, 3, 5
    email = Column(String, index=True)
    comment = Column(Text)
    ai_generated_text = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    request = relationship("ReviewRequest", back_populates="reviews")
    service = relationship("Service")

class Analytic(Base):
    __tablename__ = "analytics"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String) # "scan", "submission"
    request_id = Column(Integer, ForeignKey("review_requests.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String)
