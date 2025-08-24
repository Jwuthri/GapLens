"""Integration tests for background processing functionality."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from datetime import datetime, timedelta

from app.core.celery_app import celery_app
from app.tasks.analysis_tasks import process_app_analysis, process_website_analysis, update_task_progress
from app.tasks.maintenance_tasks import cleanup_old_results, cleanup_failed_analyses, system_health_check
from app.models import database as db_models


class TestBackgroundProcessingIntegration:
    """Integration tests for the complete background processing workflow."""
    
    @pytest.fixture
    def celery_eager_mode(self):
        """Configure Celery to run tasks synchronously for testing."""
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True
        yield
        celery_app.conf.task_always_eager = False
        celery_app.conf.task_eager_propagates = False
    
    @pytest.fixture
    def mock_database(self):
        """Mock database operations."""
        with patch('app.tasks.analysis_tasks.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            # Mock analysis object
            analysis = Mock()
            analysis.id = uuid4()
            analysis.status = db_models.AnalysisStatus.PENDING
            analysis.app_id = "com.example.app"
            analysis.platform = db_models.Platform.GOOGLE_PLAY
            
            mock_session.query.return_value.filter.return_value.first.return_value = analysis
            mock_session.query.return_value.filter.return_value.all.return_value = []
            
            yield mock_session, analysis
    
    def test_app_analysis_task_execution(self, celery_eager_mode, mock_database):
        """Test complete app analysis task execution."""
        mock_session, analysis = mock_database
        
        # Mock external services
        with patch('app.tasks.analysis_tasks.ReviewScraperService') as mock_scraper_service, \
             patch('app.tasks.analysis_tasks.NLPProcessor') as mock_nlp_processor, \
             patch('app.tasks.analysis_tasks.ClusteringEngine') as mock_clustering_engine:
            
            # Setup mocks
            mock_scraper = AsyncMock()
            mock_scraper.scrape_reviews.return_value = []
            mock_scraper_service.return_value.__aenter__.return_value = mock_scraper
            
            mock_nlp = Mock()
            mock_nlp.filter_negative_reviews.return_value = []
            mock_nlp.clean_text.return_value = []
            mock_nlp_processor.return_value = mock_nlp
            
            mock_clustering = Mock()
            mock_clustering.cluster_complaints.return_value = []
            mock_clustering_engine.return_value = mock_clustering
            
            # Execute task
            app_identifier_data = {
                "app_id": "com.example.app",
                "platform": "google_play",
                "app_name": "Test App",
                "developer": "Test Developer"
            }
            
            result = process_app_analysis.delay(str(analysis.id), app_identifier_data)
            
            # Verify task completed
            assert result.successful()
            task_result = result.get()
            assert task_result["status"] == "completed"
            
            # Verify analysis status was updated
            assert analysis.status == db_models.AnalysisStatus.COMPLETED
    
    def test_website_analysis_task_execution(self, celery_eager_mode, mock_database):
        """Test complete website analysis task execution."""
        mock_session, analysis = mock_database
        
        # Mock external services
        with patch('app.tasks.analysis_tasks.WebsiteReviewAggregator') as mock_aggregator, \
             patch('app.tasks.analysis_tasks.NLPProcessor') as mock_nlp_processor, \
             patch('app.tasks.analysis_tasks.ClusteringEngine') as mock_clustering_engine:
            
            # Setup mocks
            mock_agg = AsyncMock()
            mock_agg.aggregate_website_reviews.return_value = []
            mock_aggregator.return_value.__aenter__.return_value = mock_agg
            
            mock_nlp = Mock()
            mock_nlp.filter_negative_reviews.return_value = []
            mock_nlp.clean_text.return_value = []
            mock_nlp_processor.return_value = mock_nlp
            
            mock_clustering = Mock()
            mock_clustering.cluster_complaints.return_value = []
            mock_clustering_engine.return_value = mock_clustering
            
            # Execute task
            website_url = "https://example.com"
            
            result = process_website_analysis.delay(str(analysis.id), website_url)
            
            # Verify task completed
            assert result.successful()
            task_result = result.get()
            assert task_result["status"] == "completed"
            
            # Verify analysis status was updated
            assert analysis.status == db_models.AnalysisStatus.COMPLETED
    
    def test_task_retry_mechanism(self, celery_eager_mode, mock_database):
        """Test task retry mechanism with retryable errors."""
        mock_session, analysis = mock_database
        
        # Mock scraper to fail with retryable error
        with patch('app.tasks.analysis_tasks.ReviewScraperService') as mock_scraper_service:
            mock_scraper = AsyncMock()
            mock_scraper.scrape_reviews.side_effect = ConnectionError("Network error")
            mock_scraper_service.return_value.__aenter__.return_value = mock_scraper
            
            # Create a task that will fail and not retry in eager mode
            app_identifier_data = {
                "app_id": "com.example.app",
                "platform": "google_play"
            }
            
            # In eager mode, retries don't work the same way, so we expect failure
            result = process_app_analysis.delay(str(analysis.id), app_identifier_data)
            
            # Task should fail
            assert result.failed()
            
            # Analysis should be marked as failed
            assert analysis.status == db_models.AnalysisStatus.FAILED
            assert "ConnectionError" in analysis.status_message
    
    def test_progress_tracking(self, mock_database):
        """Test progress tracking functionality."""
        mock_session, analysis = mock_database
        
        # Test progress update
        analysis_id = analysis.id
        progress = 75.0
        message = "Processing reviews..."
        
        # Mock current_task
        with patch('app.tasks.analysis_tasks.current_task') as mock_current_task:
            mock_task = Mock()
            mock_current_task = mock_task
            
            # Call progress update
            update_task_progress(analysis_id, progress, message)
            
            # Verify database update
            assert analysis.progress == progress
            assert analysis.status_message == message
            mock_session.commit.assert_called()
    
    def test_maintenance_tasks(self, celery_eager_mode):
        """Test maintenance tasks execution."""
        # Mock database for maintenance tasks
        with patch('app.tasks.maintenance_tasks.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            # Mock old analyses
            old_analysis = Mock()
            old_analysis.id = uuid4()
            old_analysis.status = db_models.AnalysisStatus.COMPLETED
            old_analysis.completed_at = datetime.now() - timedelta(days=35)
            
            mock_session.query.return_value.filter.return_value.all.return_value = [old_analysis]
            
            # Test cleanup task
            result = cleanup_old_results.delay()
            
            assert result.successful()
            cleanup_stats = result.get()
            
            assert isinstance(cleanup_stats, dict)
            assert 'old_analyses_cleaned' in cleanup_stats
            assert 'orphaned_reviews_cleaned' in cleanup_stats
            assert 'errors' in cleanup_stats
    
    def test_failed_analysis_cleanup(self, celery_eager_mode):
        """Test cleanup of failed analyses."""
        with patch('app.tasks.maintenance_tasks.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            # Mock failed analysis
            failed_analysis = Mock()
            failed_analysis.id = uuid4()
            failed_analysis.status = db_models.AnalysisStatus.FAILED
            failed_analysis.created_at = datetime.now() - timedelta(days=10)
            
            # Mock stuck analysis
            stuck_analysis = Mock()
            stuck_analysis.id = uuid4()
            stuck_analysis.status = db_models.AnalysisStatus.PROCESSING
            stuck_analysis.created_at = datetime.now() - timedelta(hours=3)
            
            mock_session.query.return_value.filter.return_value.all.side_effect = [
                [failed_analysis],  # Failed analyses query
                [stuck_analysis]    # Stuck analyses query
            ]
            
            # Test cleanup task
            result = cleanup_failed_analyses.delay()
            
            assert result.successful()
            cleanup_stats = result.get()
            
            assert cleanup_stats['failed_analyses_cleaned'] == 1
            assert cleanup_stats['stuck_analyses_reset'] == 1
            
            # Verify stuck analysis was reset
            assert stuck_analysis.status == db_models.AnalysisStatus.FAILED
            assert "timed out" in stuck_analysis.status_message
    
    def test_system_health_check(self, celery_eager_mode):
        """Test system health check task."""
        # Mock database connection
        with patch('app.tasks.maintenance_tasks.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.execute.return_value = None  # Successful query
            
            # Mock Celery inspector
            with patch('app.core.celery_app.celery_app.control.inspect') as mock_inspect:
                mock_inspector = Mock()
                mock_inspector.stats.return_value = {'worker1': {'pool': {'max-concurrency': 4}}}
                mock_inspector.active_queues.return_value = {'worker1': []}
                mock_inspect.return_value = mock_inspector
                
                # Execute health check
                result = system_health_check.delay()
                
                assert result.successful()
                health_data = result.get()
                
                assert isinstance(health_data, dict)
                assert 'timestamp' in health_data
                assert 'overall_status' in health_data
                assert 'checks' in health_data
                assert health_data['checks']['database'] == 'healthy'
                assert health_data['checks']['redis'] == 'healthy'
    
    def test_task_error_categorization(self, celery_eager_mode, mock_database):
        """Test error categorization for retry logic."""
        mock_session, analysis = mock_database
        
        # Test non-retryable error
        with patch('app.tasks.analysis_tasks.ReviewScraperService') as mock_scraper_service:
            mock_scraper = AsyncMock()
            mock_scraper.scrape_reviews.side_effect = ValueError("Invalid input")
            mock_scraper_service.return_value.__aenter__.return_value = mock_scraper
            
            app_identifier_data = {
                "app_id": "com.example.app",
                "platform": "google_play"
            }
            
            result = process_app_analysis.delay(str(analysis.id), app_identifier_data)
            
            # Task should fail immediately for non-retryable error
            assert result.failed()
            assert analysis.status == db_models.AnalysisStatus.FAILED
            assert "non-retryable error" in analysis.status_message
            assert "ValueError" in analysis.status_message
    
    def test_task_timeout_handling(self, mock_database):
        """Test task timeout handling."""
        mock_session, analysis = mock_database
        
        # Test that long-running tasks would be handled by maintenance
        analysis.status = db_models.AnalysisStatus.PROCESSING
        analysis.created_at = datetime.now() - timedelta(hours=3)
        
        with patch('app.tasks.maintenance_tasks.SessionLocal') as mock_maintenance_session:
            mock_maintenance_session.return_value = mock_session
            mock_session.query.return_value.filter.return_value.all.return_value = [analysis]
            
            # Run cleanup task
            result = cleanup_failed_analyses.delay()
            cleanup_stats = result.get()
            
            # Verify stuck analysis was reset
            assert cleanup_stats['stuck_analyses_reset'] == 1
            assert analysis.status == db_models.AnalysisStatus.FAILED
            assert "timed out" in analysis.status_message


class TestTaskConfiguration:
    """Test Celery task configuration and routing."""
    
    def test_task_routing_configuration(self):
        """Test that tasks are routed to correct queues."""
        # Check task routes configuration
        task_routes = celery_app.conf.task_routes
        
        assert 'app.tasks.analysis_tasks.process_app_analysis' in task_routes
        assert 'app.tasks.analysis_tasks.process_website_analysis' in task_routes
        assert 'app.tasks.maintenance_tasks.*' in task_routes
        
        # Verify queue assignments
        assert task_routes['app.tasks.analysis_tasks.process_app_analysis']['queue'] == 'analysis'
        assert task_routes['app.tasks.analysis_tasks.process_website_analysis']['queue'] == 'analysis'
        assert task_routes['app.tasks.maintenance_tasks.*']['queue'] == 'maintenance'
    
    def test_task_retry_configuration(self):
        """Test task retry configuration."""
        # Check global retry settings
        assert celery_app.conf.task_default_retry_delay == 60
        assert celery_app.conf.task_max_retries == 3
        
        # Check task-specific settings
        assert celery_app.conf.task_soft_time_limit == 1800  # 30 minutes
        assert celery_app.conf.task_time_limit == 2400  # 40 minutes
    
    def test_beat_schedule_configuration(self):
        """Test periodic task schedule configuration."""
        beat_schedule = celery_app.conf.beat_schedule
        
        assert 'cleanup-old-results' in beat_schedule
        assert 'cleanup-failed-analyses' in beat_schedule
        
        # Check task intervals
        assert beat_schedule['cleanup-old-results']['schedule'] == 3600.0  # 1 hour
        assert beat_schedule['cleanup-failed-analyses']['schedule'] == 86400.0  # 1 day
    
    def test_worker_configuration(self):
        """Test worker configuration settings."""
        # Check worker settings
        assert celery_app.conf.worker_prefetch_multiplier == 1
        assert celery_app.conf.worker_max_tasks_per_child == 1000
        assert celery_app.conf.task_acks_late is True
        assert celery_app.conf.task_reject_on_worker_lost is True
    
    def test_result_backend_configuration(self):
        """Test result backend configuration."""
        assert celery_app.conf.result_expires == 3600  # 1 hour
        assert celery_app.conf.task_serializer == 'json'
        assert celery_app.conf.result_serializer == 'json'
        assert 'json' in celery_app.conf.accept_content


class TestTaskMonitoring:
    """Test task monitoring and health check functionality."""
    
    def test_health_check_task(self):
        """Test basic health check task."""
        from app.core.celery_app import health_check
        
        # Configure eager mode for testing
        celery_app.conf.task_always_eager = True
        
        try:
            result = health_check.delay()
            assert result.successful()
            
            health_data = result.get()
            assert isinstance(health_data, dict)
            assert health_data['status'] == 'healthy'
            assert 'timestamp' in health_data
            
        finally:
            celery_app.conf.task_always_eager = False
    
    def test_task_progress_monitoring(self):
        """Test task progress monitoring capabilities."""
        # This would typically involve checking Celery's monitoring capabilities
        # In a real environment, you'd test with Flower or similar monitoring tools
        
        # Test that progress tracking functions exist and are callable
        from app.tasks.analysis_tasks import update_task_progress
        
        assert callable(update_task_progress)
        
        # Test that monitoring endpoints are available
        from app.api.v1.analysis import get_system_health, get_worker_status
        
        assert callable(get_system_health)
        assert callable(get_worker_status)