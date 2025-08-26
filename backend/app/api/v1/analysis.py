"""Analysis API endpoints for the Review Gap Analyzer."""

import csv
import logging
import io
import json
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models import database as db_models
from app.models.schemas import (
    AnalysisRequest, AnalysisResponse, AnalysisResultsResponse, 
    AnalysisStatusResponse, ExportFormat, SummaryStats,
    Analysis, ComplaintCluster, Platform
)
from app.services.url_parser import URLParser, URLParsingError
from app.services.review_scraper import ReviewScraperService, AppNotFoundError, RateLimitError
from app.services.website_review_aggregator import WebsiteReviewAggregator
from app.services.cache_service import cache_service

router = APIRouter(prefix="/analysis", tags=["analysis"])
logger = logging.getLogger(__name__)
# Initialize services
url_parser = URLParser()


@router.post("/", response_model=AnalysisResponse)
async def submit_analysis(
    request: AnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Submit an app or website for analysis.
    
    This endpoint accepts either an app URL/ID or website URL and starts
    the analysis process in the background.
    """
    logger.info(f"Received analysis request: {request}")
    try:
        # Determine analysis type and validate input
        if request.app_url_or_id:
            # App analysis
            logger.info(f"Processing app analysis for: {request.app_url_or_id}")
            try:
                app_identifier = url_parser.extract_app_id(request.app_url_or_id)
                analysis_type = "APP"
                app_id = app_identifier.app_id
                # Convert schema Platform to database Platform
                platform = db_models.Platform(app_identifier.platform)
                website_url = None
                logger.info(f"App analysis setup complete: app_id={app_id}, platform={platform}")
                # raise HTTPException(status_code=500, detail=f"App analysis setup complete: app_id={app_id}, platform={platform}")
            except URLParsingError as e:
                logger.error(f"URL parsing error: {str(e)}")
                error_message = str(e)
                
                # Provide more helpful error messages
                if "appears to be a website URL" in error_message:
                    raise HTTPException(
                        status_code=400,
                        detail=error_message
                    )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid app URL or ID: {error_message}"
                    )
        else:
            # Website analysis
            logger.info(f"Processing website analysis for: {request.website_url}")
            analysis_type = "WEBSITE"
            app_id = None
            platform = None
            website_url = request.website_url
            
            # Basic URL validation for website
            if not website_url.startswith(('http://', 'https://')):
                website_url = f'https://{website_url}'
            logger.info(f"Website analysis setup complete: website_url={website_url}")
        # Note: Existing analysis check removed for simplicity
        # In production, you might want to check for recent analyses to avoid duplicates
        
        # Create new analysis record
        logger.info(f"Creating analysis record: type={analysis_type}, app_id={app_id}, website_url={website_url}, platform={platform}")
        analysis = db_models.Analysis(
            app_id=app_id,
            website_url=website_url,
            analysis_type=analysis_type,
            platform=platform,
            status=db_models.AnalysisStatus.PENDING
        )
        
        logger.info("Adding analysis to database...")
        db.add(analysis)
        logger.info("Committing analysis to database...")
        db.commit()
        logger.info("Refreshing analysis from database...")
        db.refresh(analysis)
        logger.info(f"Analysis created successfully with ID: {analysis.id}")
        
        # Start background processing with Celery
        logger.info(f"Starting background processing for analysis type: {analysis_type}")
        if analysis_type == "APP":
            logger.info("Importing app analysis task...")
            from app.tasks.analysis_tasks import process_app_analysis
            
            # Convert app_identifier to serializable dict
            app_identifier_data = {
                "app_id": app_identifier.app_id,
                "platform": app_identifier.platform,
                "app_name": app_identifier.app_name,
                "developer": app_identifier.developer
            }
            
            logger.info(f"Starting app analysis task with data: {app_identifier_data}")
            task = process_app_analysis.delay(str(analysis.id), app_identifier_data)
            analysis.task_id = task.id
            logger.info(f"App analysis task started with ID: {task.id}")
        else:
            logger.info("Importing website analysis task...")
            from app.tasks.analysis_tasks import process_website_analysis
            
            logger.info(f"Starting website analysis task for URL: {website_url}")
            task = process_website_analysis.delay(str(analysis.id), website_url)
            analysis.task_id = task.id
            logger.info(f"Website analysis task started with ID: {task.id}")
        
        logger.info("Updating analysis with task ID...")
        db.commit()
        logger.info("Analysis submission completed successfully")
        
        return AnalysisResponse(
            analysis_id=analysis.id,
            status=analysis.status,
            message="Analysis started successfully. Check status for progress updates."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis submission failed with exception: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit analysis: {str(e)}"
        )


@router.get("/{analysis_id}", response_model=AnalysisResultsResponse)
async def get_analysis_results(
    analysis_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get complete analysis results including clusters and summary statistics with caching.
    """
    try:
        # Check cache first
        cached_results = cache_service.get_analysis_results(analysis_id)
        if cached_results:
            logger.info(f"Returning cached results for analysis {analysis_id}")
            return AnalysisResultsResponse(**cached_results)
        
        # Get analysis with clusters from database
        analysis = db.query(db_models.Analysis).filter(
            db_models.Analysis.id == analysis_id
        ).first()
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail="Analysis not found"
            )
        
        if analysis.status != db_models.AnalysisStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Analysis is not completed. Current status: {analysis.status}"
            )
        
        # Convert to response models
        analysis_response = Analysis(
            id=analysis.id,
            app_id=analysis.app_id,
            website_url=analysis.website_url,
            analysis_type=analysis.analysis_type,
            platform=analysis.platform,
            status=analysis.status,
            total_reviews=analysis.total_reviews,
            negative_reviews=analysis.negative_reviews,
            created_at=analysis.created_at,
            completed_at=analysis.completed_at,
            clusters=[
                ComplaintCluster(
                    id=cluster.id,
                    analysis_id=cluster.analysis_id,
                    name=cluster.name,
                    description=cluster.description,
                    review_count=cluster.review_count,
                    percentage=float(cluster.percentage),
                    recency_score=float(cluster.recency_score),
                    sample_reviews=cluster.sample_reviews or [],
                    keywords=cluster.keywords or []
                )
                for cluster in analysis.clusters
            ]
        )
        
        # Generate summary statistics
        summary = SummaryStats(
            total_reviews=analysis.total_reviews or 0,
            negative_reviews=analysis.negative_reviews or 0,
            negative_percentage=round(
                (analysis.negative_reviews / analysis.total_reviews * 100) 
                if analysis.total_reviews and analysis.total_reviews > 0 else 0.0, 
                2
            ),
            analysis_date=analysis.completed_at or analysis.created_at,
            app_id=analysis.app_id,
            website_url=analysis.website_url,
            analysis_type=analysis.analysis_type,
            platform=analysis.platform
        )
        
        response = AnalysisResultsResponse(
            analysis=analysis_response,
            summary=summary,
            clusters=analysis_response.clusters
        )
        
        # Cache the results
        cache_service.cache_analysis_results(analysis_id, response.dict(), ttl=7200)  # 2 hours
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analysis results: {str(e)}"
        )


@router.get("/{analysis_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    analysis_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get the current status and progress of an analysis with caching.
    """
    try:
        # Check cache for status (short TTL for real-time updates)
        cached_status = cache_service.get_analysis_status(analysis_id)
        if cached_status and cached_status.get("status") == "COMPLETED":
            # Only use cached status for completed analyses
            return AnalysisStatusResponse(**cached_status)
        
        analysis = db.query(db_models.Analysis).filter(
            db_models.Analysis.id == analysis_id
        ).first()
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail="Analysis not found"
            )
        
        # Get progress and message from database or Celery task
        progress = float(analysis.progress) if analysis.progress else 0.0
        message = analysis.status_message
        
        # If no detailed progress available, use status-based defaults
        if not message:
            if analysis.status == db_models.AnalysisStatus.PENDING:
                message = "Analysis is queued for processing"
            elif analysis.status == db_models.AnalysisStatus.PROCESSING:
                message = "Analysis is in progress"
            elif analysis.status == db_models.AnalysisStatus.COMPLETED:
                message = "Analysis completed successfully"
            elif analysis.status == db_models.AnalysisStatus.FAILED:
                message = "Analysis failed. Please try again."
        
        # Try to get real-time progress from Celery if task is running
        if analysis.task_id and analysis.status == db_models.AnalysisStatus.PROCESSING:
            try:
                from app.core.celery_app import celery_app
                task_result = celery_app.AsyncResult(analysis.task_id)
                
                if task_result.state == "PROGRESS" and task_result.info:
                    progress = task_result.info.get("progress", progress)
                    message = task_result.info.get("message", message)
            except Exception:
                # If Celery is not available, use database values
                pass
        
        response = AnalysisStatusResponse(
            analysis_id=analysis.id,
            status=analysis.status,
            progress=progress,
            message=message
        )
        
        # Cache status with short TTL for active analyses, longer for completed
        ttl = 3600 if analysis.status == db_models.AnalysisStatus.COMPLETED else 60
        cache_service.cache_analysis_status(analysis_id, response.dict(), ttl=ttl)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analysis status: {str(e)}"
        )


@router.get("/{analysis_id}/export")
async def export_analysis_results(
    analysis_id: UUID,
    format: ExportFormat = Query(ExportFormat.JSON, description="Export format"),
    db: Session = Depends(get_db)
):
    """
    Export analysis results in CSV or JSON format.
    """
    try:
        # Get analysis with clusters
        analysis = db.query(db_models.Analysis).filter(
            db_models.Analysis.id == analysis_id
        ).first()
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail="Analysis not found"
            )
        
        if analysis.status != db_models.AnalysisStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Analysis is not completed. Current status: {analysis.status}"
            )
        
        # Prepare export data
        export_data = {
            "analysis_id": str(analysis.id),
            "analysis_type": analysis.analysis_type,
            "app_id": analysis.app_id,
            "website_url": analysis.website_url,
            "platform": analysis.platform.value if analysis.platform else None,
            "total_reviews": analysis.total_reviews,
            "negative_reviews": analysis.negative_reviews,
            "negative_percentage": round(
                (analysis.negative_reviews / analysis.total_reviews * 100) 
                if analysis.total_reviews and analysis.total_reviews > 0 else 0.0, 
                2
            ),
            "analysis_date": analysis.completed_at.isoformat() if analysis.completed_at else analysis.created_at.isoformat(),
            "clusters": [
                {
                    "name": cluster.name,
                    "description": cluster.description,
                    "review_count": cluster.review_count,
                    "percentage": float(cluster.percentage),
                    "recency_score": float(cluster.recency_score),
                    "sample_reviews": cluster.sample_reviews or [],
                    "keywords": cluster.keywords or []
                }
                for cluster in analysis.clusters
            ]
        }
        
        if format == ExportFormat.JSON:
            # JSON export
            json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
            
            filename = f"analysis_{analysis_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            return Response(
                content=json_str,
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
        
        elif format == ExportFormat.CSV:
            # CSV export
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "Analysis ID", "Analysis Type", "App ID", "Website URL", "Platform",
                "Total Reviews", "Negative Reviews", "Negative Percentage", "Analysis Date",
                "Cluster Name", "Cluster Description", "Review Count", "Percentage", 
                "Recency Score", "Sample Reviews", "Keywords"
            ])
            
            # Write data rows
            for cluster in analysis.clusters:
                sample_reviews_str = "; ".join(cluster.sample_reviews or [])
                keywords_str = ", ".join(cluster.keywords or [])
                
                writer.writerow([
                    str(analysis.id),
                    analysis.analysis_type,
                    analysis.app_id or "",
                    analysis.website_url or "",
                    analysis.platform.value if analysis.platform else "",
                    analysis.total_reviews or 0,
                    analysis.negative_reviews or 0,
                    export_data["negative_percentage"],
                    export_data["analysis_date"],
                    cluster.name,
                    cluster.description or "",
                    cluster.review_count,
                    float(cluster.percentage),
                    float(cluster.recency_score),
                    sample_reviews_str,
                    keywords_str
                ])
            
            filename = f"analysis_{analysis_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported export format: {format}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export analysis results: {str(e)}"
        )


@router.get("/system/health")
async def get_system_health():
    """
    Get system health status including background processing status.
    """
    try:
        from app.core.celery_app import celery_app
        from app.tasks.maintenance_tasks import system_health_check
        from app.services.performance_monitor import monitor
        
        # Get performance summary
        performance_summary = monitor.get_performance_summary()
        
        # Run health check task
        health_result = system_health_check.delay()
        
        # Wait for result with timeout
        try:
            health_data = health_result.get(timeout=10)
            
            # Combine health data with performance metrics
            health_data['performance_metrics'] = performance_summary
            return health_data
            
        except Exception as e:
            # If health check task fails, return basic status with performance data
            return {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'degraded',
                'checks': {
                    'health_check_task': 'failed'
                },
                'errors': [f"Health check task failed: {str(e)}"],
                'performance_metrics': performance_summary
            }
            
    except Exception as e:
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'unhealthy',
            'checks': {},
            'errors': [f"System health check failed: {str(e)}"]
        }


@router.get("/system/workers")
async def get_worker_status():
    """
    Get detailed worker status and queue information.
    """
    try:
        from app.core.celery_app import celery_app
        
        inspector = celery_app.control.inspect()
        
        # Get worker stats
        stats = inspector.stats()
        active = inspector.active()
        scheduled = inspector.scheduled()
        reserved = inspector.reserved()
        
        worker_info = {
            'timestamp': datetime.now().isoformat(),
            'workers': {},
            'summary': {
                'total_workers': len(stats) if stats else 0,
                'total_active_tasks': 0,
                'total_scheduled_tasks': 0,
                'total_reserved_tasks': 0
            }
        }
        
        if stats:
            for worker_name, worker_stats in stats.items():
                worker_info['workers'][worker_name] = {
                    'status': 'online',
                    'pool': worker_stats.get('pool', {}),
                    'active_tasks': len(active.get(worker_name, [])) if active else 0,
                    'scheduled_tasks': len(scheduled.get(worker_name, [])) if scheduled else 0,
                    'reserved_tasks': len(reserved.get(worker_name, [])) if reserved else 0,
                }
                
                # Update summary
                worker_info['summary']['total_active_tasks'] += worker_info['workers'][worker_name]['active_tasks']
                worker_info['summary']['total_scheduled_tasks'] += worker_info['workers'][worker_name]['scheduled_tasks']
                worker_info['summary']['total_reserved_tasks'] += worker_info['workers'][worker_name]['reserved_tasks']
        
        return worker_info
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get worker status: {str(e)}"
        )


@router.get("/system/performance")
async def get_performance_metrics():
    """
    Get detailed performance metrics and statistics.
    """
    try:
        from app.services.performance_monitor import monitor
        
        # Get comprehensive performance data
        performance_data = {
            'summary': monitor.get_performance_summary(),
            'operations': monitor.get_all_operations_stats(hours=24),
            'system_metrics': monitor.get_system_metrics(hours=1)
        }
        
        return performance_data
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/system/cache")
async def get_cache_status():
    """
    Get cache status and statistics.
    """
    try:
        cache_stats = cache_service.get_cache_stats()
        
        # Add cache key information
        cache_info = {
            'stats': cache_stats,
            'timestamp': datetime.now().isoformat()
        }
        
        return cache_info
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache status: {str(e)}"
        )


@router.post("/system/cache/clear")
async def clear_cache(pattern: str = Query("*", description="Pattern to match for cache clearing")):
    """
    Clear cache entries matching the specified pattern.
    """
    try:
        cleared_count = cache_service.clear_pattern(pattern)
        
        return {
            'message': f'Cleared {cleared_count} cache entries matching pattern: {pattern}',
            'cleared_count': cleared_count,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )


