"""API v1 router configuration."""

from fastapi import APIRouter

from .analysis import router as analysis_router

# Create main v1 router
router = APIRouter(prefix="/v1")

# Include sub-routers
router.include_router(analysis_router)