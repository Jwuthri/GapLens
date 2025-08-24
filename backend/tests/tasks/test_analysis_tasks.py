"""Tests for analysis background tasks."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from datetime import datetime

from app.tasks.analysis_tasks import process_app_analysis, process_website_analysis
from app.models import database as db_models
from app.models.schemas import AppIdentifier, Platform


class TestAnalysisTasks:
    """Test cases for analysis background tasks."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        with patch('app.tasks.analysis_tasks.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            yield mock_session
    
    @pytest.fixture
    def sample_analysis(self):
        """Sample analysis object."""
        analysis = Mock()
        analysis.id = uuid4()
        analysis.status = db_models.AnalysisStatus.PENDING
        analysis.app_id = "com.example.app"
        analysis.platform = db_models.Platform.GOOGLE_PLAY
        return analysis
    
    @pytest.fixture
    def sample_app_identifier_data(self):
        """Sample app identifier data."""
        return {
            "app_id": "com.example.app",
            "platform": "google_play",
            "app_name": "Test App",
            "developer": "Test Developer"
        }
    
    @pytest.fixture
    def sample_reviews(self):
        """Sample review data."""
        return [
            Mock(
                id="review_1",
                app_id="com.example.app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="App crashes constantly",
                review_date=datetime.now(),
                locale="en",
                author="User1"
            ),
            Mock(
                id="review_2",
                app_id="com.example.app",
                platform=Platform.GOOGLE_PLAY,
                rating=2,
                text="Battery drain is terrible",
                review_date=datetime.now(),
                locale="en",
                author="User2"
            )
        ]
    
    @pytest.fixture
    def sample_clusters(self):
        """Sample cluster data."""
        return [
            Mock(
                name="Performance Issues",
                description="App performance and stability problems",
                review_count=10,
                percentage=50.0,
                recency_score=0.8,
                sample_reviews=["App crashes", "Very slow"],
                keywords=["crash", "slow", "performance"]
            ),
            Mock(
                name="Battery Drain",
                description="Battery consumption issues",
                review_count=8,
                percentage=40.0,
                recency_score=0.7,
                sample_reviews=["Battery dies quickly", "Drains battery"],
                keywords=["battery", "drain", "power"]
            )
        ]
    
    @patch('app.tasks.analysis_tasks.update_task_progress')
    @patch('app.tasks.analysis_tasks.ClusteringEngine')
    @patch('app.tasks.analysis_tasks.NLPProcessor')
    @patch('app.tasks.analysis_tasks.ReviewScraperService')
    def test_process_app_analysis_success(
        self, 
        mock_scraper_service,
        mock_nlp_processor,
        mock_clustering_engine,
        mock_update_progress,
        mock_db_session,
        sample_analysis,
        sample_app_identifier_data,
        sample_reviews,
        sample_clusters
    ):
        """Test successful app analysis processing."""
        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_analysis
        mock_db_session.query.return_value.filter.return_value.all.return_value = sample_reviews
        
        # Mock scraper
        mock_scraper = AsyncMock()
        mock_scraper.scrape_reviews.return_value = sample_reviews
        mock_scraper_service.return_value.__aenter__.return_value = mock_scraper
        
        # Mock NLP processor
        mock_nlp = Mock()
        mock_nlp.filter_negative_reviews.return_value = sample_reviews
        mock_nlp.clean_text.return_value = sample_reviews
        mock_nlp_processor.return_value = mock_nlp
        
        # Mock clustering engine
        mock_clustering = Mock()
        mock_clustering.cluster_complaints.return_value = sample_clusters
        mock_clustering_engine.return_value = mock_clustering
        
        # Create a mock task
        mock_task = Mock()
        mock_task.request.retries = 0
        mock_task.max_retries = 3
        
        # Execute task
        result = process_app_analysis(
            mock_task,
            str(sample_analysis.id),
            sample_app_identifier_data
        )
        
        # Verify results
        assert result["status"] == "completed"
        assert result["total_reviews"] == len(sample_reviews)
        assert result["negative_reviews"] == len(sample_reviews)
        assert result["clusters"] == len(sample_clusters)
        
        # Verify analysis status was updated
        assert sample_analysis.status == db_models.AnalysisStatus.COMPLETED
        assert sample_analysis.total_reviews == len(sample_reviews)
        assert sample_analysis.negative_reviews == len(sample_reviews)
        assert sample_analysis.completed_at is not None
        
        # Verify progress updates were called
        assert mock_update_progress.call_count >= 4  # Should have multiple progress updates
        
        # Verify database operations
        mock_db_session.commit.assert_called()
        mock_db_session.close.assert_called()
    
    @patch('app.tasks.analysis_tasks.update_task_progress')
    @patch('app.tasks.analysis_tasks.ReviewScraperService')
    def test_process_app_analysis_scraping_failure(
        self,
        mock_scraper_service,
        mock_update_progress,
        mock_db_session,
        sample_analysis,
        sample_app_identifier_data
    ):
        """Test app analysis with scraping failure."""
        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_analysis
        
        # Mock scraper to raise exception
        mock_scraper = AsyncMock()
        mock_scraper.scrape_reviews.side_effect = Exception("Scraping failed")
        mock_scraper_service.return_value.__aenter__.return_value = mock_scraper
        
        # Create a mock task that won't retry
        mock_task = Mock()
        mock_task.request.retries = 3
        mock_task.max_retries = 3
        
        # Execute task and expect exception
        with pytest.raises(Exception, match="Analysis failed after maximum retries"):
            process_app_analysis(
                mock_task,
                str(sample_analysis.id),
                sample_app_identifier_data
            )
        
        # Verify analysis was marked as failed
        assert sample_analysis.status == db_models.AnalysisStatus.FAILED
        assert "Analysis failed after 3 retries" in sample_analysis.status_message
    
    @patch('app.tasks.analysis_tasks.update_task_progress')
    @patch('app.tasks.analysis_tasks.NLPProcessor')
    @patch('app.tasks.analysis_tasks.ReviewScraperService')
    def test_process_app_analysis_insufficient_reviews(
        self,
        mock_scraper_service,
        mock_nlp_processor,
        mock_update_progress,
        mock_db_session,
        sample_analysis,
        sample_app_identifier_data
    ):
        """Test app analysis with insufficient negative reviews."""
        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_analysis
        mock_db_session.query.return_value.filter.return_value.all.return_value = []
        
        # Mock scraper
        mock_scraper = AsyncMock()
        mock_scraper.scrape_reviews.return_value = []
        mock_scraper_service.return_value.__aenter__.return_value = mock_scraper
        
        # Mock NLP processor to return insufficient reviews
        mock_nlp = Mock()
        mock_nlp.filter_negative_reviews.return_value = []  # No negative reviews
        mock_nlp.clean_text.return_value = []
        mock_nlp_processor.return_value = mock_nlp
        
        # Create a mock task
        mock_task = Mock()
        mock_task.request.retries = 0
        mock_task.max_retries = 3
        
        # Execute task
        result = process_app_analysis(
            mock_task,
            str(sample_analysis.id),
            sample_app_identifier_data
        )
        
        # Verify results
        assert result["status"] == "completed"
        assert result["message"] == "Insufficient negative reviews for clustering"
        
        # Verify analysis status
        assert sample_analysis.status == db_models.AnalysisStatus.COMPLETED
        assert "insufficient negative reviews" in sample_analysis.status_message
    
    @patch('app.tasks.analysis_tasks.update_task_progress')
    @patch('app.tasks.analysis_tasks.ClusteringEngine')
    @patch('app.tasks.analysis_tasks.NLPProcessor')
    @patch('app.tasks.analysis_tasks.WebsiteReviewAggregator')
    def test_process_website_analysis_success(
        self,
        mock_aggregator,
        mock_nlp_processor,
        mock_clustering_engine,
        mock_update_progress,
        mock_db_session,
        sample_clusters
    ):
        """Test successful website analysis processing."""
        # Setup analysis
        analysis = Mock()
        analysis.id = uuid4()
        analysis.status = db_models.AnalysisStatus.PENDING
        website_url = "https://example.com"
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = analysis
        
        # Mock website reviews
        website_reviews = [
            Mock(
                id="web_review_1",
                website_url=website_url,
                platform="GOOGLE_REVIEWS",
                source_platform="Google Reviews",
                rating=1,
                text="Terrible service",
                date=datetime.now(),
                author="Customer1"
            )
        ]
        
        mock_db_session.query.return_value.filter.return_value.all.return_value = website_reviews
        
        # Mock aggregator
        mock_agg = AsyncMock()
        mock_agg.aggregate_website_reviews.return_value = website_reviews
        mock_aggregator.return_value.__aenter__.return_value = mock_agg
        
        # Mock NLP processor
        mock_nlp = Mock()
        mock_nlp.filter_negative_reviews.return_value = website_reviews
        mock_nlp.clean_text.return_value = website_reviews
        mock_nlp_processor.return_value = mock_nlp
        
        # Mock clustering engine
        mock_clustering = Mock()
        mock_clustering.cluster_complaints.return_value = sample_clusters
        mock_clustering_engine.return_value = mock_clustering
        
        # Create a mock task
        mock_task = Mock()
        mock_task.request.retries = 0
        mock_task.max_retries = 3
        
        # Execute task
        result = process_website_analysis(
            mock_task,
            str(analysis.id),
            website_url
        )
        
        # Verify results
        assert result["status"] == "completed"
        assert result["total_reviews"] == len(website_reviews)
        assert result["negative_reviews"] == len(website_reviews)
        assert result["clusters"] == len(sample_clusters)
        
        # Verify analysis status was updated
        assert analysis.status == db_models.AnalysisStatus.COMPLETED
        assert analysis.completed_at is not None
    
    @patch('app.tasks.analysis_tasks.update_task_progress')
    def test_update_task_progress(self, mock_update_progress):
        """Test progress update functionality."""
        analysis_id = uuid4()
        progress = 50.0
        message = "Processing reviews..."
        
        # Mock current_task
        with patch('app.tasks.analysis_tasks.current_task') as mock_current_task:
            mock_task = Mock()
            mock_current_task = mock_task
            
            # Mock database session
            with patch('app.tasks.analysis_tasks.SessionLocal') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value = mock_session
                
                analysis = Mock()
                mock_session.query.return_value.filter.return_value.first.return_value = analysis
                
                # Call the actual function
                from app.tasks.analysis_tasks import update_task_progress
                update_task_progress(analysis_id, progress, message)
                
                # Verify database update
                assert analysis.progress == progress
                assert analysis.status_message == message
                mock_session.commit.assert_called_once()
                mock_session.close.assert_called_once()


class TestTaskRetryLogic:
    """Test retry logic and failure handling."""
    
    @patch('app.tasks.analysis_tasks.update_task_progress')
    @patch('app.tasks.analysis_tasks.ReviewScraperService')
    def test_task_retry_with_exponential_backoff(
        self,
        mock_scraper_service,
        mock_update_progress
    ):
        """Test task retry with exponential backoff."""
        analysis_id = str(uuid4())
        app_identifier_data = {
            "app_id": "com.example.app",
            "platform": "google_play",
            "app_name": "Test App",
            "developer": "Test Developer"
        }
        
        # Mock database session
        with patch('app.tasks.analysis_tasks.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            analysis = Mock()
            analysis.id = analysis_id
            analysis.status = db_models.AnalysisStatus.PENDING
            mock_session.query.return_value.filter.return_value.first.return_value = analysis
            
            # Mock scraper to fail
            mock_scraper = AsyncMock()
            mock_scraper.scrape_reviews.side_effect = Exception("Network error")
            mock_scraper_service.return_value.__aenter__.return_value = mock_scraper
            
            # Create a mock task that will retry
            mock_task = Mock()
            mock_task.request.retries = 1  # Second attempt
            mock_task.max_retries = 3
            mock_task.retry = Mock(side_effect=Exception("Retry called"))
            
            # Execute task and expect retry
            with pytest.raises(Exception, match="Retry called"):
                process_app_analysis(mock_task, analysis_id, app_identifier_data)
            
            # Verify retry was called with exponential backoff
            mock_task.retry.assert_called_once_with(countdown=120)  # 60 * (2 ** 1)
    
    def test_task_failure_after_max_retries(self):
        """Test task failure after maximum retries exceeded."""
        analysis_id = str(uuid4())
        app_identifier_data = {
            "app_id": "com.example.app",
            "platform": "google_play"
        }
        
        # Mock database session
        with patch('app.tasks.analysis_tasks.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            analysis = Mock()
            analysis.id = analysis_id
            mock_session.query.return_value.filter.return_value.first.return_value = analysis
            
            # Create a mock task that has exceeded max retries
            mock_task = Mock()
            mock_task.request.retries = 3  # At max retries
            mock_task.max_retries = 3
            
            # Mock scraper to fail
            with patch('app.tasks.analysis_tasks.ReviewScraperService') as mock_scraper_service:
                mock_scraper = AsyncMock()
                mock_scraper.scrape_reviews.side_effect = Exception("Persistent error")
                mock_scraper_service.return_value.__aenter__.return_value = mock_scraper
                
                # Execute task and expect permanent failure
                with pytest.raises(Exception, match="Analysis failed after maximum retries"):
                    process_app_analysis(mock_task, analysis_id, app_identifier_data)
                
                # Verify analysis was marked as permanently failed
                assert analysis.status == db_models.AnalysisStatus.FAILED
                assert "Analysis failed after 3 retries" in analysis.status_message