"""Pydantic models for API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class AppIdentifier(BaseModel):
    """Schema for standardized app information across platforms."""
    app_id: str = Field(..., min_length=1, max_length=255, description="Platform-specific app identifier")
    platform: Platform = Field(..., description="App store platform")
    app_name: Optional[str] = Field(None, max_length=255, description="App name if available")
    developer: Optional[str] = Field(None, max_length=255, description="Developer name if available")
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class AnalysisStatus(str, Enum):
    """Analysis processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Base schemas
class ReviewBase(BaseModel):
    """Base review schema."""
    app_id: Optional[str] = Field(None, min_length=1, max_length=255, description="App ID for app reviews")
    website_url: Optional[str] = Field(None, min_length=1, max_length=500, description="Website URL for website reviews")
    platform: Platform
    source_platform: Optional[str] = Field(None, max_length=100, description="Original platform name for website reviews")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating (some platforms may not have ratings)")
    text: str = Field(..., min_length=1)
    review_date: datetime
    locale: Optional[str] = Field(None, max_length=10)
    author: Optional[str] = Field(None, max_length=255, description="Review author name")
    metadata: Optional[dict] = Field(None, description="Platform-specific metadata as JSON")


class ReviewCreate(ReviewBase):
    """Schema for creating a review."""
    id: str = Field(..., min_length=1, max_length=255)


class ReviewUpdate(BaseModel):
    """Schema for updating a review."""
    processed: Optional[bool] = None


class Review(ReviewBase):
    """Schema for review response."""
    id: str
    processed: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# Analysis schemas
class AnalysisBase(BaseModel):
    """Base analysis schema."""
    app_id: Optional[str] = Field(None, min_length=1, max_length=255, description="App ID for app analysis")
    website_url: Optional[str] = Field(None, min_length=1, max_length=500, description="Website URL for website analysis")
    analysis_type: str = Field(..., description="Type of analysis: APP or WEBSITE")
    platform: Optional[Platform] = Field(None, description="Platform for app analysis")


class AnalysisCreate(AnalysisBase):
    """Schema for creating an analysis."""
    pass


class AnalysisUpdate(BaseModel):
    """Schema for updating an analysis."""
    status: Optional[AnalysisStatus] = None
    total_reviews: Optional[int] = Field(None, ge=0)
    negative_reviews: Optional[int] = Field(None, ge=0)
    completed_at: Optional[datetime] = None


# Complaint cluster schemas
class ComplaintClusterBase(BaseModel):
    """Base complaint cluster schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    review_count: int = Field(..., ge=0)
    percentage: float = Field(..., ge=0.0, le=100.0)
    recency_score: float = Field(..., ge=0.0, le=100.0)
    sample_reviews: Optional[List[str]] = None
    keywords: Optional[List[str]] = None


class ComplaintClusterCreate(ComplaintClusterBase):
    """Schema for creating a complaint cluster."""
    analysis_id: UUID


class ComplaintClusterUpdate(BaseModel):
    """Schema for updating a complaint cluster."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    review_count: Optional[int] = Field(None, ge=0)
    percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    recency_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    sample_reviews: Optional[List[str]] = None
    keywords: Optional[List[str]] = None


class ComplaintCluster(ComplaintClusterBase):
    """Schema for complaint cluster response."""
    id: UUID
    analysis_id: UUID
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# Analysis with clusters
class Analysis(AnalysisBase):
    """Schema for analysis response with clusters."""
    id: UUID
    status: AnalysisStatus
    total_reviews: Optional[int] = None
    negative_reviews: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    clusters: List[ComplaintCluster] = []
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# Request/Response schemas for API endpoints
class AnalysisRequest(BaseModel):
    """Schema for analysis request."""
    app_url_or_id: Optional[str] = Field(None, min_length=1, description="App Store URL or app ID")
    website_url: Optional[str] = Field(None, min_length=1, description="Website URL for website analysis")
    
    @field_validator('app_url_or_id')
    @classmethod
    def validate_app_url_or_id(cls, v):
        """Validate app URL or ID format."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("App URL or ID cannot be empty")
        return v
    
    @field_validator('website_url')
    @classmethod
    def validate_website_url(cls, v):
        """Validate website URL format."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Website URL cannot be empty")
        return v
    
    def model_post_init(self, __context):
        """Validate that either app_url_or_id or website_url is provided."""
        if not self.app_url_or_id and not self.website_url:
            raise ValueError("Either app_url_or_id or website_url must be provided")
        if self.app_url_or_id and self.website_url:
            raise ValueError("Only one of app_url_or_id or website_url should be provided")


class AnalysisResponse(BaseModel):
    """Schema for analysis response."""
    analysis_id: UUID
    status: AnalysisStatus
    message: str


class AnalysisStatusResponse(BaseModel):
    """Schema for analysis status response."""
    analysis_id: UUID
    status: AnalysisStatus
    progress: Optional[float] = Field(None, ge=0.0, le=100.0, description="Progress percentage")
    message: Optional[str] = None


class SummaryStats(BaseModel):
    """Schema for summary statistics."""
    total_reviews: int = Field(..., ge=0)
    negative_reviews: int = Field(..., ge=0)
    negative_percentage: float = Field(..., ge=0.0, le=100.0)
    analysis_date: datetime
    app_id: Optional[str] = None
    website_url: Optional[str] = None
    analysis_type: str = Field(..., description="Type of analysis: APP or WEBSITE")
    platform: Optional[Platform] = None


class AnalysisResultsResponse(BaseModel):
    """Schema for complete analysis results."""
    analysis: Analysis
    summary: SummaryStats
    clusters: List[ComplaintCluster]


# Export schemas
class ExportFormat(str, Enum):
    """Supported export formats."""
    CSV = "csv"
    JSON = "json"


class ExportRequest(BaseModel):
    """Schema for export request."""
    format: ExportFormat = ExportFormat.JSON