"""SQLAlchemy database models for the Review Gap Analyzer."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

import json

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, 
    Integer, JSON, Numeric, String, Text, TypeDecorator
)
from sqlalchemy.types import TypeDecorator, VARCHAR
from sqlalchemy.dialects.postgresql import JSONB as PostgresJSONB, UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base


class EnumAsString(TypeDecorator):
    """Custom type to ensure enum values are stored as strings."""
    impl = VARCHAR
    cache_ok = True
    
    def __init__(self, enum_class, *args, **kwargs):
        self.enum_class = enum_class
        super().__init__(*args, **kwargs)
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, self.enum_class):
            return value.value
        return str(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return self.enum_class(value)


class UUID(TypeDecorator):
    """Platform-independent UUID type.
    
    Uses PostgreSQL UUID when available, otherwise falls back to String.
    """
    impl = String
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresUUID())
        else:
            return dialect.type_descriptor(String(36))
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            return str(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return str(value)


class JSONB(TypeDecorator):
    """Platform-independent JSONB type.
    
    Uses PostgreSQL JSONB when available, otherwise falls back to Text with JSON serialization.
    """
    impl = Text
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresJSONB())
        else:
            return dialect.type_descriptor(Text())
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            return json.loads(value) if value else None


class Platform(str, Enum):
    """Supported platforms for reviews."""
    # App Store Platforms
    GOOGLE_PLAY = "google_play"
    APP_STORE = "app_store"
    
    # Software Review Platforms
    G2 = "g2"
    CAPTERRA = "capterra"
    TRUSTRADIUS = "trustradius"
    SOFTWARE_ADVICE = "software_advice"
    PRODUCT_HUNT = "product_hunt"
    
    # Travel & Hospitality Platforms
    TRIPADVISOR = "tripadvisor"
    BOOKING_COM = "booking_com"
    EXPEDIA = "expedia"
    HOTELS_COM = "hotels_com"
    AIRBNB = "airbnb"
    TRIVAGO = "trivago"
    HOLIDAYCHECK = "holidaycheck"
    
    # Restaurant Platforms
    ZOMATO = "zomato"
    OPENTABLE = "opentable"
    
    # General Review Platforms
    GOOGLE_REVIEWS = "google_reviews"
    YELP = "yelp"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    TRUSTPILOT = "trustpilot"


class AnalysisStatus(str, Enum):
    """Analysis processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Review(Base):
    """Review model for storing reviews from apps and websites."""
    
    __tablename__ = "reviews"
    
    id = Column(String, primary_key=True, index=True)
    app_id = Column(String, nullable=True, index=True)  # For app reviews
    website_url = Column(String, nullable=True, index=True)  # For website reviews
    platform = Column(EnumAsString(Platform), nullable=False)
    source_platform = Column(String, nullable=True)  # Original platform name for website reviews
    rating = Column(Integer, nullable=True)  # Some platforms may not have ratings
    text = Column(Text, nullable=False)
    review_date = Column(DateTime, nullable=False)
    locale = Column(String, nullable=True)
    author = Column(String, nullable=True)  # Review author name
    metadata = Column(JSON, nullable=True)  # Platform-specific metadata as JSON
    processed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Indexes for common queries
    __table_args__ = (
        {"extend_existing": True}
    )


class Analysis(Base):
    """Analysis model for storing analysis metadata and results."""
    
    __tablename__ = "analyses"
    
    id = Column(UUID, primary_key=True, default=uuid4, index=True)
    app_id = Column(String, nullable=True, index=True)  # For app analysis
    website_url = Column(String, nullable=True, index=True)  # For website analysis
    analysis_type = Column(String, nullable=False)  # APP or WEBSITE
    platform = Column(EnumAsString(Platform), nullable=True)  # For app analysis
    status = Column(EnumAsString(AnalysisStatus), nullable=False, default=AnalysisStatus.PENDING)
    total_reviews = Column(Integer, nullable=True)
    negative_reviews = Column(Integer, nullable=True)
    progress = Column(Numeric(5, 2), nullable=True, default=0.0)  # Progress percentage (0-100)
    status_message = Column(Text, nullable=True)  # Detailed status message
    task_id = Column(String, nullable=True)  # Celery task ID for tracking
    created_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship to complaint clusters
    clusters = relationship("ComplaintCluster", back_populates="analysis", cascade="all, delete-orphan")


class ComplaintCluster(Base):
    """Complaint cluster model for storing grouped complaints."""
    
    __tablename__ = "complaint_clusters"
    
    id = Column(UUID, primary_key=True, default=uuid4, index=True)
    analysis_id = Column(UUID, ForeignKey("analyses.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    review_count = Column(Integer, nullable=False)
    percentage = Column(Numeric(5, 2), nullable=False)
    recency_score = Column(Numeric(5, 2), nullable=False)
    sample_reviews = Column(JSONB, nullable=True)
    keywords = Column(JSONB, nullable=True)
    
    # Relationship back to analysis
    analysis = relationship("Analysis", back_populates="clusters")