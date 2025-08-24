"""Background tasks for analysis processing."""

import asyncio
from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from celery import current_task
from celery.exceptions import Retry

from app.core.celery_app import celery_app
from app.database.connection import SessionLocal
from app.models import database as db_models
from app.services.url_parser import URLParser, URLParsingError
from app.services.review_scraper import ReviewScraperService, AppNotFoundError, RateLimitError
from app.models.schemas import ReviewCreate, Platform
from app.services.website_review_aggregator import WebsiteReviewAggregator
from app.services.nlp_processor import NLPProcessor
from app.services.clustering_engine import ClusteringEngine


def update_task_progress(analysis_id: UUID, progress: float, message: str = None):
    """Update task progress in the database and Celery state."""
    if current_task:
        current_task.update_state(
            state="PROGRESS",
            meta={
                "analysis_id": str(analysis_id),
                "progress": progress,
                "message": message or f"Progress: {progress:.1f}%"
            }
        )
    
    # Also update database
    db = SessionLocal()
    try:
        analysis = db.query(db_models.Analysis).filter(
            db_models.Analysis.id == analysis_id
        ).first()
        
        if analysis:
            analysis.progress = progress
            if message:
                analysis.status_message = message
            db.commit()
    except Exception as e:
        print(f"Failed to update progress in database: {e}")
    finally:
        db.close()


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def process_app_analysis(self, analysis_id: str, app_identifier_data: Dict[str, Any]):
    """
    Background task to process app analysis.
    
    Args:
        analysis_id: Analysis ID to update
        app_identifier_data: Dictionary containing app identifier information
    """
    analysis_uuid = UUID(analysis_id)
    db = SessionLocal()
    
    try:
        # Update status to processing
        analysis = db.query(db_models.Analysis).filter(
            db_models.Analysis.id == analysis_uuid
        ).first()
        
        if not analysis:
            raise Exception(f"Analysis {analysis_id} not found")
        
        analysis.status = db_models.AnalysisStatus.PROCESSING
        db.commit()
        
        update_task_progress(analysis_uuid, 10.0, "Starting review scraping...")
        
        # Reconstruct app identifier from data
        from app.models.schemas import AppIdentifier, Platform
        app_identifier = AppIdentifier(
            app_id=app_identifier_data["app_id"],
            platform=Platform(app_identifier_data["platform"]),
            app_name=app_identifier_data.get("app_name"),
            developer=app_identifier_data.get("developer")
        )
        
        # Scrape reviews
        try:
            # Run async scraping in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def scrape_reviews():
                async with ReviewScraperService() as scraper:
                    return await scraper.scrape_reviews(
                        app_identifier, 
                        max_reviews=1000, 
                        prioritize_recent=True
                    )
            
            reviews = loop.run_until_complete(scrape_reviews())
            loop.close()
            
            if not reviews:
                # Create a sample review to allow analysis to continue
                sample_review = ReviewCreate(
                    id=f"sample_{analysis_uuid}",
                    app_id=app_identifier["app_id"],
                    platform=Platform(app_identifier["platform"]),
                    rating=3,
                    text="No reviews were found for this app. This is a placeholder review to allow the analysis to complete. The app may be new or have limited reviews available.",
                    review_date=datetime.now(),
                    locale="en",
                    author="System"
                )
                reviews = [sample_review]
                update_task_progress(analysis_uuid, 25.0, "No reviews found, using sample data for analysis...")
            
            update_task_progress(analysis_uuid, 30.0, f"Found {len(reviews)} reviews, storing in database...")
            
            # Store reviews in database
            stored_count = 0
            for review_data in reviews:
                existing_review = db.query(db_models.Review).filter(
                    db_models.Review.id == review_data.id
                ).first()
                
                if not existing_review:
                    review = db_models.Review(
                        id=review_data.id,
                        app_id=review_data.app_id,
                        platform=db_models.Platform(review_data.platform),
                        rating=review_data.rating,
                        text=review_data.text,
                        review_date=review_data.review_date,
                        locale=review_data.locale,
                        author=review_data.author
                    )
                    db.add(review)
                    stored_count += 1
            
            db.commit()
            update_task_progress(analysis_uuid, 50.0, f"Stored {stored_count} new reviews, starting NLP processing...")
            
        except (AppNotFoundError, RateLimitError) as e:
            analysis.status = db_models.AnalysisStatus.FAILED
            analysis.status_message = str(e)
            db.commit()
            raise Exception(f"Review scraping failed: {e}")
        
        # Process reviews with NLP
        nlp_processor = NLPProcessor()
        
        # Get reviews for processing
        app_reviews = db.query(db_models.Review).filter(
            db_models.Review.app_id == app_identifier.app_id,
            db_models.Review.platform == db_models.Platform(app_identifier.platform)
        ).all()
        
        update_task_progress(analysis_uuid, 60.0, "Filtering and cleaning negative reviews...")
        
        # Filter negative reviews and clean text
        negative_reviews = nlp_processor.filter_negative_reviews(app_reviews)
        cleaned_reviews = nlp_processor.clean_text(negative_reviews)
        
        if len(cleaned_reviews) < 5:
            # Not enough negative reviews for meaningful analysis
            analysis.status = db_models.AnalysisStatus.COMPLETED
            analysis.total_reviews = len(app_reviews)
            analysis.negative_reviews = len(negative_reviews)
            analysis.completed_at = datetime.now()
            analysis.status_message = "Analysis completed with insufficient negative reviews for clustering"
            db.commit()
            update_task_progress(analysis_uuid, 100.0, "Analysis completed - insufficient negative reviews")
            return {"status": "completed", "message": "Insufficient negative reviews for clustering"}
        
        update_task_progress(analysis_uuid, 80.0, f"Clustering {len(cleaned_reviews)} negative reviews...")
        
        # Cluster complaints
        clustering_engine = ClusteringEngine()
        clusters = clustering_engine.cluster_complaints(cleaned_reviews)
        
        update_task_progress(analysis_uuid, 90.0, f"Storing {len(clusters)} complaint clusters...")
        
        # Store clusters
        for cluster_data in clusters:
            cluster = db_models.ComplaintCluster(
                analysis_id=analysis.id,
                name=cluster_data.name,
                description=cluster_data.description,
                review_count=cluster_data.review_count,
                percentage=cluster_data.percentage,
                recency_score=cluster_data.recency_score,
                sample_reviews=cluster_data.sample_reviews,
                keywords=cluster_data.keywords
            )
            db.add(cluster)
        
        # Update analysis as completed
        analysis.status = db_models.AnalysisStatus.COMPLETED
        analysis.total_reviews = len(app_reviews)
        analysis.negative_reviews = len(negative_reviews)
        analysis.completed_at = datetime.now()
        analysis.status_message = f"Analysis completed successfully with {len(clusters)} complaint clusters"
        
        db.commit()
        
        update_task_progress(analysis_uuid, 100.0, "Analysis completed successfully!")
        
        return {
            "status": "completed",
            "total_reviews": len(app_reviews),
            "negative_reviews": len(negative_reviews),
            "clusters": len(clusters)
        }
        
    except Exception as e:
        # Categorize the error for better retry logic
        error_type = type(e).__name__
        error_message = str(e)
        
        # Determine if error is retryable
        retryable_errors = [
            'ConnectionError', 'TimeoutError', 'HTTPError', 'RateLimitError',
            'TemporaryFailure', 'NetworkError', 'ServiceUnavailable'
        ]
        
        is_retryable = any(err in error_type for err in retryable_errors)
        
        # Handle retries for retryable errors
        if is_retryable and self.request.retries < self.max_retries:
            retry_delay = min(60 * (2 ** self.request.retries), 300)  # Cap at 5 minutes
            update_task_progress(
                analysis_uuid, 
                0.0, 
                f"Analysis failed ({error_type}), retrying in {retry_delay}s... (attempt {self.request.retries + 1}/{self.max_retries})"
            )
            
            # Log the retry attempt
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Retrying app analysis {analysis_id} due to {error_type}: {error_message}")
            
            raise self.retry(countdown=retry_delay, exc=e)
        
        # Mark analysis as failed after max retries or non-retryable error
        try:
            analysis = db.query(db_models.Analysis).filter(
                db_models.Analysis.id == analysis_uuid
            ).first()
            
            if analysis:
                if is_retryable:
                    failure_reason = f"Analysis failed after {self.max_retries} retries due to {error_type}: {error_message}"
                else:
                    failure_reason = f"Analysis failed due to non-retryable error ({error_type}): {error_message}"
                
                analysis.status = db_models.AnalysisStatus.FAILED
                analysis.status_message = failure_reason
                analysis.progress = 0.0
                db.commit()
                
                # Log the permanent failure
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"App analysis {analysis_id} permanently failed: {failure_reason}")
                
        except Exception as db_error:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to update analysis status for {analysis_id}: {db_error}")
        
        # Re-raise the original exception
        raise Exception(f"Analysis failed: {error_message}")
        
    finally:
        db.close()


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def process_website_analysis(self, analysis_id: str, website_url: str):
    """
    Background task to process website analysis.
    
    Args:
        analysis_id: Analysis ID to update
        website_url: Website URL to analyze
    """
    analysis_uuid = UUID(analysis_id)
    db = SessionLocal()
    
    try:
        # Update status to processing
        analysis = db.query(db_models.Analysis).filter(
            db_models.Analysis.id == analysis_uuid
        ).first()
        
        if not analysis:
            raise Exception(f"Analysis {analysis_id} not found")
        
        analysis.status = db_models.AnalysisStatus.PROCESSING
        db.commit()
        
        update_task_progress(analysis_uuid, 10.0, "Starting website review aggregation...")
        
        # Aggregate website reviews
        try:
            # Run async aggregation in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def aggregate_reviews():
                async with WebsiteReviewAggregator() as aggregator:
                    return await aggregator.aggregate_website_reviews(website_url)
            
            reviews = loop.run_until_complete(aggregate_reviews())
            loop.close()
            
            if not reviews:
                # Create a sample review to allow analysis to continue
                from app.services.website_review_aggregator import WebsiteReview
                
                sample_review = WebsiteReview(
                    id=f"sample_{analysis_uuid}",
                    platform="GOOGLE_REVIEWS",  # Use a valid platform enum value
                    source_platform="Sample Data",
                    rating=3,
                    text="No reviews were found for this website. This is a placeholder review to allow the analysis to complete. Consider checking the website manually for customer feedback or testimonials.",
                    date=datetime.now(),
                    author="System",
                    website_url=website_url
                )
                reviews = [sample_review]
                update_task_progress(analysis_uuid, 25.0, "No reviews found, using sample data for analysis...")
            
            update_task_progress(analysis_uuid, 30.0, f"Found {len(reviews)} reviews, storing in database...")
            
            # Store reviews in database
            stored_count = 0
            for review_data in reviews:
                existing_review = db.query(db_models.Review).filter(
                    db_models.Review.id == review_data.id
                ).first()
                
                if not existing_review:
                    # Convert platform string to enum
                    platform_mapping = {
                        "GOOGLE_REVIEWS": db_models.Platform.GOOGLE_REVIEWS,
                        "YELP": db_models.Platform.YELP,
                        "FACEBOOK": db_models.Platform.FACEBOOK,
                        "TWITTER": db_models.Platform.TWITTER,
                        "GOOGLE": db_models.Platform.GOOGLE_REVIEWS,
                        "WEBSITE": db_models.Platform.GOOGLE_REVIEWS,  # Map website to google_reviews as fallback
                        "G2": db_models.Platform.G2,
                        "CAPTERRA": db_models.Platform.CAPTERRA,
                        "TRUSTRADIUS": db_models.Platform.TRUSTRADIUS,
                        "SOFTWARE_ADVICE": db_models.Platform.SOFTWARE_ADVICE,
                        "PRODUCT_HUNT": db_models.Platform.PRODUCT_HUNT,
                        "TRIPADVISOR": db_models.Platform.TRIPADVISOR,
                        "BOOKING_COM": db_models.Platform.BOOKING_COM,
                        "EXPEDIA": db_models.Platform.EXPEDIA,
                        "HOTELS_COM": db_models.Platform.HOTELS_COM,
                        "AIRBNB": db_models.Platform.AIRBNB,
                        "TRIVAGO": db_models.Platform.TRIVAGO,
                        "HOLIDAYCHECK": db_models.Platform.HOLIDAYCHECK,
                        "ZOMATO": db_models.Platform.ZOMATO,
                        "OPENTABLE": db_models.Platform.OPENTABLE,
                    }
                    
                    platform_enum = platform_mapping.get(
                        review_data.platform.upper(), 
                        db_models.Platform.GOOGLE_REVIEWS  # Default fallback
                    )
                    
                    review = db_models.Review(
                        id=review_data.id,
                        website_url=review_data.website_url,
                        platform=platform_enum,
                        source_platform=review_data.source_platform,
                        rating=review_data.rating,
                        text=review_data.text,
                        review_date=review_data.date,  # WebsiteReview uses 'date', not 'review_date'
                        locale="en",  # Default locale for website reviews
                        author=review_data.author
                    )
                    db.add(review)
                    stored_count += 1
            
            db.commit()
            update_task_progress(analysis_uuid, 50.0, f"Stored {stored_count} new reviews, starting NLP processing...")
            
        except Exception as e:
            analysis.status = db_models.AnalysisStatus.FAILED
            analysis.status_message = str(e)
            db.commit()
            raise Exception(f"Website review aggregation failed: {e}")
        
        # Process reviews with NLP
        nlp_processor = NLPProcessor()
        
        # Get reviews for processing
        website_reviews = db.query(db_models.Review).filter(
            db_models.Review.website_url == website_url
        ).all()
        
        update_task_progress(analysis_uuid, 60.0, "Filtering and cleaning negative reviews...")
        
        # Filter negative reviews and clean text
        negative_reviews = nlp_processor.filter_negative_reviews(website_reviews)
        cleaned_reviews = nlp_processor.clean_text(negative_reviews)
        
        if len(cleaned_reviews) < 5:
            # Not enough negative reviews for meaningful analysis
            analysis.status = db_models.AnalysisStatus.COMPLETED
            analysis.total_reviews = len(website_reviews)
            analysis.negative_reviews = len(negative_reviews)
            analysis.completed_at = datetime.now()
            analysis.status_message = "Analysis completed with insufficient negative reviews for clustering"
            db.commit()
            update_task_progress(analysis_uuid, 100.0, "Analysis completed - insufficient negative reviews")
            return {"status": "completed", "message": "Insufficient negative reviews for clustering"}
        
        update_task_progress(analysis_uuid, 80.0, f"Clustering {len(cleaned_reviews)} negative reviews...")
        
        # Cluster complaints
        clustering_engine = ClusteringEngine()
        clusters = clustering_engine.cluster_complaints(cleaned_reviews)
        
        update_task_progress(analysis_uuid, 90.0, f"Storing {len(clusters)} complaint clusters...")
        
        # Store clusters
        for cluster_data in clusters:
            cluster = db_models.ComplaintCluster(
                analysis_id=analysis.id,
                name=cluster_data.name,
                description=cluster_data.description,
                review_count=cluster_data.review_count,
                percentage=cluster_data.percentage,
                recency_score=cluster_data.recency_score,
                sample_reviews=cluster_data.sample_reviews,
                keywords=cluster_data.keywords
            )
            db.add(cluster)
        
        # Update analysis as completed
        analysis.status = db_models.AnalysisStatus.COMPLETED
        analysis.total_reviews = len(website_reviews)
        analysis.negative_reviews = len(negative_reviews)
        analysis.completed_at = datetime.now()
        analysis.status_message = f"Analysis completed successfully with {len(clusters)} complaint clusters"
        
        db.commit()
        
        update_task_progress(analysis_uuid, 100.0, "Analysis completed successfully!")
        
        return {
            "status": "completed",
            "total_reviews": len(website_reviews),
            "negative_reviews": len(negative_reviews),
            "clusters": len(clusters)
        }
        
    except Exception as e:
        # Categorize the error for better retry logic
        error_type = type(e).__name__
        error_message = str(e)
        
        # Determine if error is retryable
        retryable_errors = [
            'ConnectionError', 'TimeoutError', 'HTTPError', 'RateLimitError',
            'TemporaryFailure', 'NetworkError', 'ServiceUnavailable'
        ]
        
        is_retryable = any(err in error_type for err in retryable_errors)
        
        # Handle retries for retryable errors
        if is_retryable and self.request.retries < self.max_retries:
            retry_delay = min(60 * (2 ** self.request.retries), 300)  # Cap at 5 minutes
            update_task_progress(
                analysis_uuid, 
                0.0, 
                f"Analysis failed ({error_type}), retrying in {retry_delay}s... (attempt {self.request.retries + 1}/{self.max_retries})"
            )
            
            # Log the retry attempt
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Retrying website analysis {analysis_id} due to {error_type}: {error_message}")
            
            raise self.retry(countdown=retry_delay, exc=e)
        
        # Mark analysis as failed after max retries or non-retryable error
        try:
            analysis = db.query(db_models.Analysis).filter(
                db_models.Analysis.id == analysis_uuid
            ).first()
            
            if analysis:
                if is_retryable:
                    failure_reason = f"Analysis failed after {self.max_retries} retries due to {error_type}: {error_message}"
                else:
                    failure_reason = f"Analysis failed due to non-retryable error ({error_type}): {error_message}"
                
                analysis.status = db_models.AnalysisStatus.FAILED
                analysis.status_message = failure_reason
                analysis.progress = 0.0
                db.commit()
                
                # Log the permanent failure
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Website analysis {analysis_id} permanently failed: {failure_reason}")
                
        except Exception as db_error:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to update analysis status for {analysis_id}: {db_error}")
        
        # Re-raise the original exception
        raise Exception(f"Analysis failed: {error_message}")
        
    finally:
        db.close()