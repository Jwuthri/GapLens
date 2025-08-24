"""Advanced clustering and insights generation engine using sentence transformers."""

import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np
from collections import Counter

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available, falling back to TF-IDF")

from sklearn.cluster import HDBSCAN, KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import hdbscan

from ..models.schemas import Review, ComplaintClusterBase


class ClusteringEngine:
    """Advanced clustering engine using sentence transformers and HDBSCAN."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the clustering engine.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        self.sentence_model = None
        self.tfidf_vectorizer = None
        
        # Initialize sentence transformer if available
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.sentence_model = SentenceTransformer(model_name)
                self.logger.info(f"Loaded sentence transformer model: {model_name}")
            except Exception as e:
                self.logger.warning(f"Failed to load sentence transformer: {e}")
                # Don't modify the global variable, just set local state
                self.sentence_model = None
        
        # Fallback to TF-IDF if sentence transformers not available
        if not SENTENCE_TRANSFORMERS_AVAILABLE or self.sentence_model is None:
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                min_df=1,  # Allow terms that appear in at least 1 document
                max_df=0.9,
                ngram_range=(1, 2)
            )
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            Numpy array of embeddings
        """
        if not texts:
            return np.array([])
        
        # Filter out empty texts
        valid_texts = [text for text in texts if text and text.strip()]
        if not valid_texts:
            return np.array([])
        
        try:
            if self.sentence_model is not None:
                # Use sentence transformers for better semantic embeddings
                embeddings = self.sentence_model.encode(valid_texts, show_progress_bar=False)
                self.logger.debug(f"Generated {len(embeddings)} sentence transformer embeddings")
                return embeddings
            else:
                # Fallback to TF-IDF with dynamic parameters for small datasets
                vectorizer = TfidfVectorizer(
                    max_features=min(1000, len(valid_texts) * 100),
                    stop_words='english',
                    min_df=1,  # Allow terms that appear in at least 1 document
                    max_df=0.9,
                    ngram_range=(1, 2)
                )
                embeddings = vectorizer.fit_transform(valid_texts).toarray()
                self.logger.debug(f"Generated {len(embeddings)} TF-IDF embeddings")
                return embeddings
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {e}")
            # Return empty array on error
            return np.array([])
    
    def find_optimal_clusters(self, embeddings: np.ndarray, min_cluster_size: int = 3, max_clusters: int = 10) -> Tuple[np.ndarray, str]:
        """
        Find optimal clustering using HDBSCAN with fallback to K-means.
        
        Args:
            embeddings: Embedding vectors
            min_cluster_size: Minimum size for a cluster
            max_clusters: Maximum number of clusters to consider
            
        Returns:
            Tuple of (cluster_labels, algorithm_used)
        """
        if len(embeddings) < min_cluster_size:
            return np.zeros(len(embeddings)), "insufficient_data"
        
        try:
            # Try HDBSCAN first (better for varying cluster sizes)
            hdbscan_clusterer = HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=max(1, min_cluster_size // 2),
                metric='euclidean',
                cluster_selection_method='eom'
            )
            
            hdbscan_labels = hdbscan_clusterer.fit_predict(embeddings)
            
            # Check if HDBSCAN found good clusters
            unique_labels = set(hdbscan_labels)
            n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
            
            if n_clusters >= 2 and n_clusters <= max_clusters:
                # Calculate silhouette score to validate clustering quality
                if n_clusters > 1 and len(set(hdbscan_labels)) > 1:
                    try:
                        silhouette_avg = silhouette_score(embeddings, hdbscan_labels)
                        if silhouette_avg > 0.1:  # Reasonable clustering quality
                            self.logger.info(f"HDBSCAN found {n_clusters} clusters with silhouette score: {silhouette_avg:.3f}")
                            return hdbscan_labels, "hdbscan"
                    except Exception:
                        pass
            
            # Fallback to K-means if HDBSCAN doesn't work well
            optimal_k = self._find_optimal_k_means(embeddings, min_clusters=2, max_clusters=max_clusters)
            
            kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
            kmeans_labels = kmeans.fit_predict(embeddings)
            
            self.logger.info(f"K-means found {optimal_k} clusters")
            return kmeans_labels, "kmeans"
            
        except Exception as e:
            self.logger.error(f"Error in clustering: {e}")
            # Return single cluster as fallback
            return np.zeros(len(embeddings)), "fallback"
    
    def _find_optimal_k_means(self, embeddings: np.ndarray, min_clusters: int = 2, max_clusters: int = 10) -> int:
        """
        Find optimal number of clusters for K-means using elbow method and silhouette analysis.
        
        Args:
            embeddings: Embedding vectors
            min_clusters: Minimum number of clusters
            max_clusters: Maximum number of clusters
            
        Returns:
            Optimal number of clusters
        """
        if len(embeddings) < min_clusters:
            return 1
        
        max_k = min(max_clusters, len(embeddings) - 1)
        if max_k < min_clusters:
            return min_clusters
        
        silhouette_scores = []
        inertias = []
        k_range = range(min_clusters, max_k + 1)
        
        for k in k_range:
            try:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(embeddings)
                
                # Calculate silhouette score
                if len(set(cluster_labels)) > 1:
                    silhouette_avg = silhouette_score(embeddings, cluster_labels)
                    silhouette_scores.append(silhouette_avg)
                else:
                    silhouette_scores.append(-1)
                
                inertias.append(kmeans.inertia_)
                
            except Exception:
                silhouette_scores.append(-1)
                inertias.append(float('inf'))
        
        # Find optimal k based on silhouette score
        if silhouette_scores and max(silhouette_scores) > 0:
            optimal_k = k_range[np.argmax(silhouette_scores)]
        else:
            # Fallback to elbow method or default
            optimal_k = min(5, max_k)
        
        return optimal_k
    
    def cluster_reviews(self, reviews: List[Review], min_cluster_size: int = 3) -> List[ComplaintClusterBase]:
        """
        Cluster reviews into complaint categories using advanced NLP techniques.
        
        Args:
            reviews: List of processed Review objects
            min_cluster_size: Minimum number of reviews required to form a cluster
            
        Returns:
            List of ComplaintClusterBase objects
        """
        if len(reviews) < min_cluster_size:
            self.logger.warning(f"Insufficient reviews for clustering: {len(reviews)} < {min_cluster_size}")
            return []
        
        # Extract and clean texts
        texts = []
        valid_reviews = []
        
        for review in reviews:
            cleaned_text = self._clean_text_for_clustering(review.text)
            if cleaned_text and len(cleaned_text.split()) >= 3:  # At least 3 words
                texts.append(cleaned_text)
                valid_reviews.append(review)
        
        if len(valid_reviews) < min_cluster_size:
            self.logger.warning(f"Insufficient valid reviews after cleaning: {len(valid_reviews)} < {min_cluster_size}")
            return []
        
        # Generate embeddings
        embeddings = self.generate_embeddings(texts)
        if len(embeddings) == 0:
            self.logger.error("Failed to generate embeddings")
            return []
        
        # Perform clustering
        cluster_labels, algorithm = self.find_optimal_clusters(embeddings, min_cluster_size)
        
        # Create complaint clusters
        clusters = self._create_complaint_clusters(valid_reviews, cluster_labels, algorithm)
        
        # Rank clusters by frequency and recency
        ranked_clusters = self._rank_clusters_by_importance(clusters)
        
        self.logger.info(f"Created {len(ranked_clusters)} clusters using {algorithm}")
        return ranked_clusters
    
    def _clean_text_for_clustering(self, text: str) -> str:
        """
        Clean text specifically for clustering (less aggressive than general cleaning).
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text suitable for clustering
        """
        if not text:
            return ""
        
        import re
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs and email addresses
        text = re.sub(r'http[s]?://\S+', '', text)
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove excessive punctuation but keep some for context
        text = re.sub(r'[^\w\s\.\!\?]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _create_complaint_clusters(self, reviews: List[Review], cluster_labels: np.ndarray, algorithm: str) -> List[ComplaintClusterBase]:
        """
        Create ComplaintClusterBase objects from clustering results.
        
        Args:
            reviews: List of Review objects
            cluster_labels: Array of cluster labels for each review
            algorithm: Algorithm used for clustering
            
        Returns:
            List of ComplaintClusterBase objects
        """
        clusters = []
        unique_labels = set(cluster_labels)
        
        # Remove noise label (-1) if present (from HDBSCAN)
        if -1 in unique_labels:
            unique_labels.remove(-1)
        
        total_reviews = len(reviews)
        
        for label in unique_labels:
            # Get reviews in this cluster
            cluster_indices = [i for i, l in enumerate(cluster_labels) if l == label]
            cluster_reviews = [reviews[i] for i in cluster_indices]
            
            if len(cluster_reviews) < 2:  # Skip very small clusters
                continue
            
            # Extract cluster information
            cluster_texts = [review.text for review in cluster_reviews]
            keywords = self._extract_cluster_keywords(cluster_texts)
            
            # Generate cluster name and description
            cluster_name, description = self._generate_cluster_name_and_description(keywords, cluster_texts)
            
            # Calculate metrics
            review_count = len(cluster_reviews)
            percentage = (review_count / total_reviews) * 100
            recency_score = self._calculate_recency_score(cluster_reviews)
            
            # Get sample reviews (up to 3 most representative)
            sample_reviews = self._select_representative_reviews(cluster_texts, max_samples=3)
            
            cluster = ComplaintClusterBase(
                name=cluster_name,
                description=description,
                review_count=review_count,
                percentage=round(percentage, 2),
                recency_score=round(recency_score, 2),
                sample_reviews=sample_reviews,
                keywords=keywords[:5]  # Top 5 keywords
            )
            
            clusters.append(cluster)
        
        return clusters
    
    def _extract_cluster_keywords(self, texts: List[str], max_keywords: int = 10) -> List[str]:
        """
        Extract important keywords from cluster texts using TF-IDF.
        
        Args:
            texts: List of text strings in the cluster
            max_keywords: Maximum number of keywords to return
            
        Returns:
            List of important keywords
        """
        if not texts:
            return []
        
        try:
            # Use TF-IDF to find cluster-specific keywords
            vectorizer = TfidfVectorizer(
                max_features=max_keywords * 2,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.9
            )
            
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get average TF-IDF scores
            mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
            
            # Sort by score and get top keywords
            top_indices = np.argsort(mean_scores)[::-1][:max_keywords]
            keywords = [feature_names[i] for i in top_indices if mean_scores[i] > 0]
            
            return keywords
        
        except Exception as e:
            self.logger.warning(f"Error extracting keywords: {e}")
            # Fallback to simple word frequency
            all_words = []
            for text in texts:
                words = text.lower().split()
                # Filter out common words and short words
                filtered_words = [w for w in words if len(w) > 3 and w.isalpha()]
                all_words.extend(filtered_words)
            
            word_freq = Counter(all_words)
            return [word for word, _ in word_freq.most_common(max_keywords)]
    
    def _generate_cluster_name_and_description(self, keywords: List[str], texts: List[str]) -> Tuple[str, str]:
        """
        Generate descriptive name and description for a cluster.
        
        Args:
            keywords: List of important keywords
            texts: List of review texts in the cluster
            
        Returns:
            Tuple of (cluster_name, description)
        """
        if not keywords:
            return "General Issues", "Miscellaneous user complaints and issues"
        
        # Enhanced category mapping with more specific patterns
        category_patterns = {
            'crash': ('App Crashes', 'Issues related to app crashes and instability'),
            'bug': ('Bug Reports', 'Various bugs and software defects reported by users'),
            'slow': ('Performance Issues', 'Complaints about slow performance and responsiveness'),
            'battery': ('Battery Drain', 'Issues with excessive battery consumption'),
            'login': ('Authentication Problems', 'Difficulties with login and account access'),
            'sync': ('Synchronization Issues', 'Problems with data syncing across devices'),
            'notification': ('Notification Problems', 'Issues with push notifications and alerts'),
            'interface': ('User Interface Issues', 'Problems with app design and usability'),
            'feature': ('Missing Features', 'Requests for missing or desired functionality'),
            'ads': ('Advertisement Issues', 'Complaints about ads and monetization'),
            'payment': ('Payment Problems', 'Issues with purchases and billing'),
            'update': ('Update Issues', 'Problems after app updates'),
            'loading': ('Loading Problems', 'Issues with content loading and connectivity'),
            'account': ('Account Issues', 'Problems with user accounts and profiles'),
            'data': ('Data Issues', 'Problems with data loss or corruption'),
            'connection': ('Connectivity Issues', 'Network and internet connection problems'),
            'storage': ('Storage Problems', 'Issues with storage space and memory'),
            'quality': ('Quality Issues', 'General quality and reliability concerns')
        }
        
        # Check keywords against patterns
        primary_keyword = keywords[0].lower()
        
        for pattern, (name, desc) in category_patterns.items():
            if pattern in primary_keyword or any(pattern in kw.lower() for kw in keywords[:3]):
                return name, desc
        
        # Generate name from top keywords if no pattern matches
        if len(keywords) >= 2:
            name = f"{keywords[0].title()} and {keywords[1].title()} Issues"
        else:
            name = f"{keywords[0].title()} Issues"
        
        description = f"User complaints primarily about {', '.join(keywords[:3]).lower()}"
        
        return name, description
    
    def _select_representative_reviews(self, texts: List[str], max_samples: int = 3) -> List[str]:
        """
        Select most representative reviews from a cluster.
        
        Args:
            texts: List of review texts
            max_samples: Maximum number of samples to return
            
        Returns:
            List of representative review texts
        """
        if len(texts) <= max_samples:
            return texts
        
        # Select reviews of different lengths to get variety
        sorted_texts = sorted(texts, key=len)
        
        if len(sorted_texts) >= 3:
            # Pick short, medium, and long reviews
            indices = [0, len(sorted_texts) // 2, len(sorted_texts) - 1]
            return [sorted_texts[i] for i in indices[:max_samples]]
        else:
            return sorted_texts[:max_samples]
    
    def _calculate_recency_score(self, reviews: List[Review]) -> float:
        """
        Calculate recency score for a cluster based on review dates.
        
        Args:
            reviews: List of Review objects
            
        Returns:
            Recency score (0-100, higher means more recent)
        """
        if not reviews:
            return 0.0
        
        now = datetime.now()
        three_months_ago = now - timedelta(days=90)
        one_month_ago = now - timedelta(days=30)
        
        recent_count = 0
        very_recent_count = 0
        total_count = len(reviews)
        
        for review in reviews:
            review_date = review.review_date
            if hasattr(review_date, 'replace'):  # Handle timezone-aware dates
                review_date = review_date.replace(tzinfo=None)
            
            if review_date >= three_months_ago:
                recent_count += 1
                if review_date >= one_month_ago:
                    very_recent_count += 1
        
        # Weight very recent reviews more heavily
        recency_score = ((recent_count * 0.7) + (very_recent_count * 0.3)) / total_count * 100
        
        return min(100.0, recency_score)
    
    def _rank_clusters_by_importance(self, clusters: List[ComplaintClusterBase]) -> List[ComplaintClusterBase]:
        """
        Rank clusters by combined importance score (frequency + recency).
        
        Args:
            clusters: List of ComplaintCluster objects
            
        Returns:
            Sorted list of clusters by importance
        """
        if not clusters:
            return clusters
        
        # Calculate combined importance score
        for cluster in clusters:
            frequency_weight = 0.7
            recency_weight = 0.3
            
            # Normalize scores
            frequency_score = cluster.percentage  # Already a percentage
            recency_score = cluster.recency_score  # Already 0-100
            
            # Calculate weighted importance score
            importance_score = (frequency_score * frequency_weight) + (recency_score * recency_weight)
            
            # Store original percentage for display
            cluster.percentage = round(cluster.percentage, 2)
            
            # Use a custom attribute for sorting (we'll sort by this)
            setattr(cluster, '_importance_score', importance_score)
        
        # Sort by importance score (highest first)
        clusters.sort(key=lambda x: getattr(x, '_importance_score', 0), reverse=True)
        
        # Remove the temporary attribute
        for cluster in clusters:
            if hasattr(cluster, '_importance_score'):
                delattr(cluster, '_importance_score')
        
        return clusters


class InsightsGenerator:
    """Generate insights and analytics from clustered review data."""
    
    def __init__(self):
        """Initialize the insights generator."""
        self.logger = logging.getLogger(__name__)
    
    def generate_summary_insights(self, reviews: List[Review], clusters: List[ComplaintClusterBase]) -> Dict:
        """
        Generate summary insights from reviews and clusters.
        
        Args:
            reviews: List of all reviews
            clusters: List of complaint clusters
            
        Returns:
            Dictionary containing summary insights
        """
        total_reviews = len(reviews)
        if total_reviews == 0:
            return {
                'total_reviews': 0,
                'clustered_reviews': 0,
                'coverage_percentage': 0,
                'top_issues': [],
                'trend_analysis': {},
                'recommendations': []
            }
        
        # Calculate coverage
        clustered_reviews = sum(cluster.review_count for cluster in clusters)
        coverage_percentage = min(100.0, (clustered_reviews / total_reviews) * 100) if total_reviews > 0 else 0
        
        # Get top issues
        top_issues = clusters[:5] if len(clusters) >= 5 else clusters
        
        # Analyze trends
        trend_analysis = self._analyze_trends(reviews, clusters)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(clusters)
        
        return {
            'total_reviews': total_reviews,
            'clustered_reviews': clustered_reviews,
            'coverage_percentage': round(coverage_percentage, 2),
            'top_issues': [
                {
                    'name': issue.name,
                    'percentage': issue.percentage,
                    'recency_score': issue.recency_score,
                    'review_count': issue.review_count
                }
                for issue in top_issues
            ],
            'trend_analysis': trend_analysis,
            'recommendations': recommendations
        }
    
    def _analyze_trends(self, reviews: List[Review], clusters: List[ComplaintClusterBase]) -> Dict:
        """
        Analyze trends in review data.
        
        Args:
            reviews: List of reviews
            clusters: List of clusters
            
        Returns:
            Dictionary containing trend analysis
        """
        if not reviews:
            return {}
        
        # Analyze recency trends
        now = datetime.now()
        one_month_ago = now - timedelta(days=30)
        three_months_ago = now - timedelta(days=90)
        
        recent_reviews = [r for r in reviews if r.review_date >= one_month_ago]
        older_reviews = [r for r in reviews if r.review_date < one_month_ago]
        
        # Calculate trend direction
        recent_percentage = len(recent_reviews) / len(reviews) * 100 if reviews else 0
        
        trend_direction = "stable"
        if recent_percentage > 40:
            trend_direction = "increasing"
        elif recent_percentage < 20:
            trend_direction = "decreasing"
        
        return {
            'recent_activity': recent_percentage,
            'trend_direction': trend_direction,
            'most_recent_issues': [c.name for c in clusters[:3] if c.recency_score > 50]
        }
    
    def _generate_recommendations(self, clusters: List[ComplaintClusterBase]) -> List[str]:
        """
        Generate actionable recommendations based on clusters.
        
        Args:
            clusters: List of complaint clusters
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if not clusters:
            return ["Insufficient data for recommendations. Collect more reviews for analysis."]
        
        # Priority recommendations based on top clusters
        top_cluster = clusters[0] if clusters else None
        if top_cluster:
            if top_cluster.percentage > 30:
                recommendations.append(f"High priority: Address '{top_cluster.name}' affecting {top_cluster.percentage:.1f}% of negative reviews")
            
            if top_cluster.recency_score > 70:
                recommendations.append(f"Urgent: '{top_cluster.name}' shows high recent activity - investigate immediately")
        
        # General recommendations
        if len(clusters) >= 3:
            top_three_percentage = sum(c.percentage for c in clusters[:3])
            if top_three_percentage > 60:
                recommendations.append(f"Focus on top 3 issues which cover {top_three_percentage:.1f}% of complaints")
        
        # Recency-based recommendations
        recent_clusters = [c for c in clusters if c.recency_score > 60]
        if recent_clusters:
            recommendations.append(f"Monitor recent trends: {len(recent_clusters)} issue categories show increasing activity")
        
        if not recommendations:
            recommendations.append("Continue monitoring user feedback and address issues as they emerge")
        
        return recommendations