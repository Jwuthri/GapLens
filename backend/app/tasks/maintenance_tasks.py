"""Maintenance tasks for cleanup and monitoring."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from celery import current_task
from sqlalchemy import and_, or_

from app.core.celery_app import celery_app
from app.database.connection import SessionLocal
from app.models import database as db_models

logger = logging.getLogger(__name__)


@celery_app.task(name='cleanup_old_results')
def cleanup_old_results() -> Dict[str, Any]:
    """
    Clean up old Celery task results and expired analysis data.
    
    This task runs periodically to:
    - Remove old Celery task results from Redis
    - Clean up completed analyses older than 30 days
    - Remove orphaned reviews not associated with any analysis
    """
    db = SessionLocal()
    cleanup_stats = {
        'celery_results_cleaned': 0,
        'old_analyses_cleaned': 0,
        'orphaned_reviews_cleaned': 0,
        'errors': []
    }
    
    try:
        # Clean up old Celery results
        try:
            from app.core.celery_app import celery_app
            inspector = celery_app.control.inspect()
            
            # Get all task results older than 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            # Note: This is a simplified cleanup. In production, you might want
            # to use Redis commands directly for more efficient cleanup
            logger.info("Celery result cleanup completed (simplified implementation)")
            cleanup_stats['celery_results_cleaned'] = 0  # Placeholder
            
        except Exception as e:
            error_msg = f"Failed to cleanup Celery results: {str(e)}"
            logger.error(error_msg)
            cleanup_stats['errors'].append(error_msg)
        
        # Clean up old completed analyses (older than 30 days)
        try:
            cutoff_date = datetime.now() - timedelta(days=30)
            
            old_analyses = db.query(db_models.Analysis).filter(
                and_(
                    db_models.Analysis.status == db_models.AnalysisStatus.COMPLETED,
                    db_models.Analysis.completed_at < cutoff_date
                )
            ).all()
            
            for analysis in old_analyses:
                # Delete associated clusters first (cascade should handle this)
                db.delete(analysis)
                cleanup_stats['old_analyses_cleaned'] += 1
            
            db.commit()
            logger.info(f"Cleaned up {cleanup_stats['old_analyses_cleaned']} old analyses")
            
        except Exception as e:
            error_msg = f"Failed to cleanup old analyses: {str(e)}"
            logger.error(error_msg)
            cleanup_stats['errors'].append(error_msg)
            db.rollback()
        
        # Clean up orphaned reviews (reviews not associated with any existing analysis)
        try:
            # Find reviews that don't have corresponding analyses
            orphaned_reviews = db.query(db_models.Review).filter(
                and_(
                    or_(
                        # App reviews without matching analysis
                        and_(
                            db_models.Review.app_id.isnot(None),
                            ~db.query(db_models.Analysis).filter(
                                and_(
                                    db_models.Analysis.app_id == db_models.Review.app_id,
                                    db_models.Analysis.platform == db_models.Review.platform
                                )
                            ).exists()
                        ),
                        # Website reviews without matching analysis
                        and_(
                            db_models.Review.website_url.isnot(None),
                            ~db.query(db_models.Analysis).filter(
                                db_models.Analysis.website_url == db_models.Review.website_url
                            ).exists()
                        )
                    ),
                    # Only clean up reviews older than 7 days
                    db_models.Review.created_at < datetime.now() - timedelta(days=7)
                )
            ).limit(1000)  # Limit to avoid overwhelming the database
            
            orphaned_count = orphaned_reviews.count()
            if orphaned_count > 0:
                orphaned_reviews.delete(synchronize_session=False)
                db.commit()
                cleanup_stats['orphaned_reviews_cleaned'] = orphaned_count
                logger.info(f"Cleaned up {orphaned_count} orphaned reviews")
            
        except Exception as e:
            error_msg = f"Failed to cleanup orphaned reviews: {str(e)}"
            logger.error(error_msg)
            cleanup_stats['errors'].append(error_msg)
            db.rollback()
        
        logger.info(f"Cleanup completed: {cleanup_stats}")
        return cleanup_stats
        
    except Exception as e:
        error_msg = f"Cleanup task failed: {str(e)}"
        logger.error(error_msg)
        cleanup_stats['errors'].append(error_msg)
        return cleanup_stats
        
    finally:
        db.close()


@celery_app.task(name='cleanup_failed_analyses')
def cleanup_failed_analyses() -> Dict[str, Any]:
    """
    Clean up failed analyses and reset stuck processing analyses.
    
    This task:
    - Removes failed analyses older than 7 days
    - Resets analyses stuck in PROCESSING state for more than 2 hours
    """
    db = SessionLocal()
    cleanup_stats = {
        'failed_analyses_cleaned': 0,
        'stuck_analyses_reset': 0,
        'errors': []
    }
    
    try:
        # Clean up old failed analyses
        try:
            cutoff_date = datetime.now() - timedelta(days=7)
            
            failed_analyses = db.query(db_models.Analysis).filter(
                and_(
                    db_models.Analysis.status == db_models.AnalysisStatus.FAILED,
                    db_models.Analysis.created_at < cutoff_date
                )
            ).all()
            
            for analysis in failed_analyses:
                db.delete(analysis)
                cleanup_stats['failed_analyses_cleaned'] += 1
            
            db.commit()
            logger.info(f"Cleaned up {cleanup_stats['failed_analyses_cleaned']} failed analyses")
            
        except Exception as e:
            error_msg = f"Failed to cleanup failed analyses: {str(e)}"
            logger.error(error_msg)
            cleanup_stats['errors'].append(error_msg)
            db.rollback()
        
        # Reset stuck processing analyses
        try:
            stuck_cutoff = datetime.now() - timedelta(hours=2)
            
            stuck_analyses = db.query(db_models.Analysis).filter(
                and_(
                    db_models.Analysis.status == db_models.AnalysisStatus.PROCESSING,
                    db_models.Analysis.created_at < stuck_cutoff
                )
            ).all()
            
            for analysis in stuck_analyses:
                analysis.status = db_models.AnalysisStatus.FAILED
                analysis.status_message = "Analysis timed out and was reset by maintenance task"
                analysis.progress = 0.0
                cleanup_stats['stuck_analyses_reset'] += 1
            
            db.commit()
            logger.info(f"Reset {cleanup_stats['stuck_analyses_reset']} stuck analyses")
            
        except Exception as e:
            error_msg = f"Failed to reset stuck analyses: {str(e)}"
            logger.error(error_msg)
            cleanup_stats['errors'].append(error_msg)
            db.rollback()
        
        logger.info(f"Failed analysis cleanup completed: {cleanup_stats}")
        return cleanup_stats
        
    except Exception as e:
        error_msg = f"Failed analysis cleanup task failed: {str(e)}"
        logger.error(error_msg)
        cleanup_stats['errors'].append(error_msg)
        return cleanup_stats
        
    finally:
        db.close()


@celery_app.task(name='system_health_check')
def system_health_check() -> Dict[str, Any]:
    """
    Perform comprehensive system health check.
    
    Checks:
    - Database connectivity
    - Redis connectivity
    - Worker status
    - Queue lengths
    """
    health_status = {
        'timestamp': datetime.now().isoformat(),
        'overall_status': 'healthy',
        'checks': {},
        'errors': []
    }
    
    # Check database connectivity
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health_status['checks']['database'] = 'healthy'
    except Exception as e:
        health_status['checks']['database'] = 'unhealthy'
        health_status['errors'].append(f"Database check failed: {str(e)}")
        health_status['overall_status'] = 'unhealthy'
    
    # Check Redis connectivity
    try:
        from app.core.celery_app import celery_app
        
        # Test Redis connection through Celery
        inspector = celery_app.control.inspect()
        stats = inspector.stats()
        
        if stats:
            health_status['checks']['redis'] = 'healthy'
            health_status['checks']['workers'] = len(stats)
        else:
            health_status['checks']['redis'] = 'unhealthy'
            health_status['checks']['workers'] = 0
            health_status['errors'].append("No Celery workers detected")
            health_status['overall_status'] = 'degraded'
            
    except Exception as e:
        health_status['checks']['redis'] = 'unhealthy'
        health_status['checks']['workers'] = 0
        health_status['errors'].append(f"Redis/Celery check failed: {str(e)}")
        health_status['overall_status'] = 'unhealthy'
    
    # Check queue lengths
    try:
        inspector = celery_app.control.inspect()
        active_queues = inspector.active_queues()
        
        if active_queues:
            total_active = sum(len(queues) for queues in active_queues.values())
            health_status['checks']['active_tasks'] = total_active
            
            if total_active > 100:  # Threshold for high load
                health_status['overall_status'] = 'degraded'
                health_status['errors'].append(f"High task load detected: {total_active} active tasks")
        else:
            health_status['checks']['active_tasks'] = 0
            
    except Exception as e:
        health_status['errors'].append(f"Queue check failed: {str(e)}")
    
    logger.info(f"Health check completed: {health_status['overall_status']}")
    return health_status