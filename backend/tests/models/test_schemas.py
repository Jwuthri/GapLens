"""Tests for Pydantic schema models."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AnalysisCreate,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
    AnalysisUpdate,
    ComplaintClusterCreate,
    ComplaintClusterUpdate,
    ExportFormat,
    ExportRequest,
    Platform,
    ReviewCreate,
    ReviewUpdate,
    SummaryStats,
)


class TestPlatformEnum:
    """Tests for Platform enum."""
    
    def test_platform_values(self):
        """Test platform enum values."""
        assert Platform.GOOGLE_PLAY == "google_play"
        assert Platform.APP_STORE == "app_store"


class TestAnalysisStatusEnum:
    """Tests for AnalysisStatus enum."""
    
    def test_analysis_status_values(self):
        """Test analysis status enum values."""
        assert AnalysisStatus.PENDING == "pending"
        assert AnalysisStatus.PROCESSING == "processing"
        assert AnalysisStatus.COMPLETED == "completed"
        assert AnalysisStatus.FAILED == "failed"


class TestReviewSchemas:
    """Tests for Review-related schemas."""
    
    def test_review_create_valid(self):
        """Test creating a valid ReviewCreate schema."""
        review_data = {
            "id": "test_review_1",
            "app_id": "com.example.app",
            "platform": Platform.GOOGLE_PLAY,
            "rating": 1,
            "text": "App crashes constantly",
            "review_date": datetime.now(),
            "locale": "en_US"
        }
        
        review = ReviewCreate(**review_data)
        assert review.id == "test_review_1"
        assert review.app_id == "com.example.app"
        assert review.platform == Platform.GOOGLE_PLAY
        assert review.rating == 1
        assert review.text == "App crashes constantly"
        assert review.locale == "en_US"
    
    def test_review_create_missing_required_fields(self):
        """Test ReviewCreate with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ReviewCreate()
        
        errors = exc_info.value.errors()
        required_fields = {"id", "platform", "text", "review_date"}
        error_fields = {error["loc"][0] for error in errors}
        assert required_fields.issubset(error_fields)
    
    def test_review_create_invalid_rating(self):
        """Test ReviewCreate with invalid rating values."""
        base_data = {
            "id": "test_review",
            "app_id": "com.example.app",
            "platform": Platform.GOOGLE_PLAY,
            "text": "Test review",
            "review_date": datetime.now()
        }
        
        # Test rating too low
        with pytest.raises(ValidationError):
            ReviewCreate(**{**base_data, "rating": 0})
        
        # Test rating too high
        with pytest.raises(ValidationError):
            ReviewCreate(**{**base_data, "rating": 6})
    
    def test_review_create_empty_strings(self):
        """Test ReviewCreate with empty string validation."""
        base_data = {
            "id": "test_review",
            "app_id": "com.example.app",
            "platform": Platform.GOOGLE_PLAY,
            "rating": 1,
            "review_date": datetime.now()
        }
        
        # Empty text should fail
        with pytest.raises(ValidationError):
            ReviewCreate(**{**base_data, "text": ""})
        
        # Empty app_id should fail
        with pytest.raises(ValidationError):
            ReviewCreate(**{**base_data, "app_id": "", "text": "Valid text"})
    
    def test_review_update_optional_fields(self):
        """Test ReviewUpdate with optional fields."""
        # Empty update should be valid
        update = ReviewUpdate()
        assert update.processed is None
        
        # Update with processed field
        update = ReviewUpdate(processed=True)
        assert update.processed is True


class TestAnalysisSchemas:
    """Tests for Analysis-related schemas."""
    
    def test_analysis_create_valid(self):
        """Test creating a valid AnalysisCreate schema."""
        analysis_data = {
            "app_id": "com.example.app",
            "analysis_type": "APP",
            "platform": Platform.GOOGLE_PLAY
        }
        
        analysis = AnalysisCreate(**analysis_data)
        assert analysis.app_id == "com.example.app"
        assert analysis.platform == Platform.GOOGLE_PLAY
    
    def test_analysis_request_valid(self):
        """Test creating a valid AnalysisRequest schema."""
        # Test with URL
        request = AnalysisRequest(app_url_or_id="https://play.google.com/store/apps/details?id=com.example.app")
        assert request.app_url_or_id == "https://play.google.com/store/apps/details?id=com.example.app"
        
        # Test with app ID
        request = AnalysisRequest(app_url_or_id="com.example.app")
        assert request.app_url_or_id == "com.example.app"
    
    def test_analysis_request_validation(self):
        """Test AnalysisRequest validation."""
        # Empty string should fail
        with pytest.raises(ValidationError):
            AnalysisRequest(app_url_or_id="")
        
        # Whitespace-only string should fail
        with pytest.raises(ValidationError):
            AnalysisRequest(app_url_or_id="   ")
    
    def test_analysis_update_optional_fields(self):
        """Test AnalysisUpdate with optional fields."""
        # Empty update should be valid
        update = AnalysisUpdate()
        assert update.status is None
        assert update.total_reviews is None
        assert update.negative_reviews is None
        assert update.completed_at is None
        
        # Update with all fields
        now = datetime.now()
        update = AnalysisUpdate(
            status=AnalysisStatus.COMPLETED,
            total_reviews=100,
            negative_reviews=25,
            completed_at=now
        )
        assert update.status == AnalysisStatus.COMPLETED
        assert update.total_reviews == 100
        assert update.negative_reviews == 25
        assert update.completed_at == now
    
    def test_analysis_update_negative_values(self):
        """Test AnalysisUpdate with negative values."""
        # Negative total_reviews should fail
        with pytest.raises(ValidationError):
            AnalysisUpdate(total_reviews=-1)
        
        # Negative negative_reviews should fail
        with pytest.raises(ValidationError):
            AnalysisUpdate(negative_reviews=-1)


class TestComplaintClusterSchemas:
    """Tests for ComplaintCluster-related schemas."""
    
    def test_complaint_cluster_create_valid(self):
        """Test creating a valid ComplaintClusterCreate schema."""
        analysis_id = uuid4()
        cluster_data = {
            "analysis_id": analysis_id,
            "name": "Crash Issues",
            "description": "App crashes and stability problems",
            "review_count": 25,
            "percentage": 15.5,
            "recency_score": 85.2,
            "sample_reviews": ["App crashes on startup", "Constant crashes"],
            "keywords": ["crash", "stability", "bug"]
        }
        
        cluster = ComplaintClusterCreate(**cluster_data)
        assert cluster.analysis_id == analysis_id
        assert cluster.name == "Crash Issues"
        assert cluster.description == "App crashes and stability problems"
        assert cluster.review_count == 25
        assert cluster.percentage == 15.5
        assert cluster.recency_score == 85.2
        assert cluster.sample_reviews == ["App crashes on startup", "Constant crashes"]
        assert cluster.keywords == ["crash", "stability", "bug"]
    
    def test_complaint_cluster_create_required_fields(self):
        """Test ComplaintClusterCreate with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ComplaintClusterCreate()
        
        errors = exc_info.value.errors()
        required_fields = {"analysis_id", "name", "review_count", "percentage", "recency_score"}
        error_fields = {error["loc"][0] for error in errors}
        assert required_fields.issubset(error_fields)
    
    def test_complaint_cluster_percentage_validation(self):
        """Test percentage field validation."""
        base_data = {
            "analysis_id": uuid4(),
            "name": "Test Cluster",
            "review_count": 10,
            "recency_score": 50.0
        }
        
        # Valid percentages
        for percentage in [0.0, 50.0, 100.0]:
            cluster = ComplaintClusterCreate(**{**base_data, "percentage": percentage})
            assert cluster.percentage == percentage
        
        # Invalid percentages
        with pytest.raises(ValidationError):
            ComplaintClusterCreate(**{**base_data, "percentage": -1.0})
        
        with pytest.raises(ValidationError):
            ComplaintClusterCreate(**{**base_data, "percentage": 101.0})
    
    def test_complaint_cluster_update_optional_fields(self):
        """Test ComplaintClusterUpdate with optional fields."""
        # Empty update should be valid
        update = ComplaintClusterUpdate()
        assert update.name is None
        assert update.description is None
        assert update.review_count is None
        
        # Partial update
        update = ComplaintClusterUpdate(name="Updated Name", review_count=30)
        assert update.name == "Updated Name"
        assert update.review_count == 30
        assert update.description is None


class TestSummaryStats:
    """Tests for SummaryStats schema."""
    
    def test_summary_stats_valid(self):
        """Test creating valid SummaryStats."""
        stats_data = {
            "total_reviews": 100,
            "negative_reviews": 25,
            "negative_percentage": 25.0,
            "analysis_date": datetime.now(),
            "app_id": "com.example.app",
            "analysis_type": "APP",
            "platform": Platform.GOOGLE_PLAY
        }
        
        stats = SummaryStats(**stats_data)
        assert stats.total_reviews == 100
        assert stats.negative_reviews == 25
        assert stats.negative_percentage == 25.0
        assert stats.app_id == "com.example.app"
        assert stats.platform == Platform.GOOGLE_PLAY
    
    def test_summary_stats_validation(self):
        """Test SummaryStats validation."""
        base_data = {
            "negative_reviews": 25,
            "negative_percentage": 25.0,
            "analysis_date": datetime.now(),
            "app_id": "com.example.app",
            "platform": Platform.GOOGLE_PLAY
        }
        
        # Negative total_reviews should fail
        with pytest.raises(ValidationError):
            SummaryStats(**{**base_data, "total_reviews": -1})
        
        # Negative negative_reviews should fail
        with pytest.raises(ValidationError):
            SummaryStats(**{**base_data, "total_reviews": 100, "negative_reviews": -1})


class TestExportSchemas:
    """Tests for Export-related schemas."""
    
    def test_export_format_enum(self):
        """Test ExportFormat enum values."""
        assert ExportFormat.CSV == "csv"
        assert ExportFormat.JSON == "json"
    
    def test_export_request_default(self):
        """Test ExportRequest with default format."""
        request = ExportRequest()
        assert request.format == ExportFormat.JSON
    
    def test_export_request_custom_format(self):
        """Test ExportRequest with custom format."""
        request = ExportRequest(format=ExportFormat.CSV)
        assert request.format == ExportFormat.CSV