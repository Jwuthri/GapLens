"""NLP text processing pipeline for review analysis."""

import re
import string
from typing import List, Set, Tuple
from collections import Counter
from datetime import datetime, timedelta

import nltk
import numpy as np
import pandas as pd
from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.metrics.pairwise import cosine_similarity

from ..models.schemas import Review, ComplaintClusterBase
from .clustering_engine import ClusteringEngine, InsightsGenerator


class NLPProcessor:
    """NLP processing engine for review text analysis and clustering."""
    
    def __init__(self):
        """Initialize the NLP processor with required NLTK data."""
        self._ensure_nltk_data()
        self.stopwords = self._get_stopwords()
        self.emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
        
        # Initialize advanced clustering engine
        self.clustering_engine = ClusteringEngine()
        self.insights_generator = InsightsGenerator()
    
    def _ensure_nltk_data(self) -> None:
        """Download required NLTK data if not present."""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', quiet=True)
    
    def _get_stopwords(self) -> Set[str]:
        """Get English stopwords set."""
        from nltk.corpus import stopwords
        return set(stopwords.words('english'))
    
    def clean_text(self, text: str) -> str:
        """
        Clean individual text by removing emojis, special characters, and normalizing.
        
        Args:
            text: Raw review text
            
        Returns:
            Cleaned text string
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove emojis
        text = self.emoji_pattern.sub('', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        
        # Remove punctuation (keep only alphanumeric and spaces)
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove extra spaces
        text = ' '.join(text.split())
        
        return text.strip()
    
    def remove_stopwords(self, text: str) -> str:
        """
        Remove stopwords from text while preserving sentence structure.
        
        Args:
            text: Cleaned text
            
        Returns:
            Text with stopwords removed
        """
        if not text:
            return ""
        
        words = text.split()
        filtered_words = [word for word in words if word not in self.stopwords and len(word) > 2]
        return ' '.join(filtered_words)
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text by applying all cleaning steps.
        
        Args:
            text: Raw text
            
        Returns:
            Fully normalized text
        """
        text = self.clean_text(text)
        text = self.remove_stopwords(text)
        return text
    
    def filter_negative_reviews(self, reviews: List[Review]) -> List[Review]:
        """
        Filter reviews to include only negative ones (1-2 star ratings or negative sentiment).
        
        Args:
            reviews: List of Review objects
            
        Returns:
            List of negative reviews
        """
        negative_reviews = []
        
        for review in reviews:
            is_negative = False
            
            # Check rating if available
            if review.rating is not None and review.rating <= 2:
                is_negative = True
            # If no rating, use sentiment analysis
            elif review.rating is None:
                sentiment = self.analyze_sentiment(review.text)
                if sentiment < -0.1:  # Negative sentiment threshold
                    is_negative = True
            
            if is_negative:
                negative_reviews.append(review)
        
        return negative_reviews
    
    def analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment of text using TextBlob.
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment polarity score (-1 to 1, negative to positive)
        """
        if not text:
            return 0.0
        
        try:
            blob = TextBlob(text)
            return blob.sentiment.polarity
        except Exception:
            return 0.0
    
    def remove_duplicates(self, reviews: List[Review], similarity_threshold: float = 0.85) -> List[Review]:
        """
        Remove duplicate reviews based on text similarity.
        
        Args:
            reviews: List of Review objects
            similarity_threshold: Cosine similarity threshold for considering reviews as duplicates
            
        Returns:
            List of unique reviews
        """
        if len(reviews) <= 1:
            return reviews
        
        # Extract and normalize texts
        texts = [self.normalize_text(review.text) for review in reviews]
        
        # Create TF-IDF vectors
        vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
        except ValueError:
            # If all texts are empty after normalization, return original reviews
            return reviews
        
        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(tfidf_matrix)
        
        # Find duplicates
        unique_indices = []
        processed = set()
        
        for i in range(len(reviews)):
            if i in processed:
                continue
            
            unique_indices.append(i)
            
            # Mark similar reviews as processed
            for j in range(i + 1, len(reviews)):
                if j not in processed and similarity_matrix[i][j] >= similarity_threshold:
                    processed.add(j)
        
        return [reviews[i] for i in unique_indices]
    
    def process_reviews(self, reviews: List[Review]) -> List[Review]:
        """
        Complete processing pipeline for reviews.
        
        Args:
            reviews: List of Review objects
            
        Returns:
            List of processed negative reviews with duplicates removed
        """
        # Filter for negative reviews
        negative_reviews = self.filter_negative_reviews(reviews)
        
        # Remove duplicates
        unique_reviews = self.remove_duplicates(negative_reviews)
        
        return unique_reviews
    
    def extract_keywords(self, texts: List[str], max_keywords: int = 10) -> List[str]:
        """
        Extract important keywords from a collection of texts using TF-IDF.
        
        Args:
            texts: List of text strings
            max_keywords: Maximum number of keywords to return
            
        Returns:
            List of important keywords
        """
        if not texts:
            return []
        
        # Normalize texts
        normalized_texts = [self.normalize_text(text) for text in texts if text]
        
        if not normalized_texts:
            return []
        
        try:
            # Use TF-IDF to find important terms
            vectorizer = TfidfVectorizer(
                max_features=max_keywords * 3,
                stop_words='english',
                ngram_range=(1, 2),  # Include bigrams
                min_df=2  # Term must appear in at least 2 documents
            )
            
            tfidf_matrix = vectorizer.fit_transform(normalized_texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get average TF-IDF scores
            mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
            
            # Sort by score and get top keywords
            top_indices = np.argsort(mean_scores)[::-1][:max_keywords]
            keywords = [feature_names[i] for i in top_indices if mean_scores[i] > 0]
            
            return keywords
        
        except (ValueError, AttributeError):
            # Fallback to simple word frequency if TF-IDF fails
            all_words = []
            for text in normalized_texts:
                all_words.extend(text.split())
            
            word_freq = Counter(all_words)
            return [word for word, _ in word_freq.most_common(max_keywords)]
    
    def cluster_complaints(self, reviews: List[Review], min_cluster_size: int = 3) -> List[ComplaintClusterBase]:
        """
        Cluster reviews into complaint categories using advanced NLP techniques.
        
        Args:
            reviews: List of processed Review objects
            min_cluster_size: Minimum number of reviews required to form a cluster
            
        Returns:
            List of ComplaintClusterBase objects
        """
        # Use the advanced clustering engine
        return self.clustering_engine.cluster_reviews(reviews, min_cluster_size)
    
    def _create_complaint_clusters(self, reviews: List[Review], cluster_labels: np.ndarray) -> List[ComplaintClusterBase]:
        """
        Create ComplaintClusterBase objects from clustering results.
        
        Args:
            reviews: List of Review objects
            cluster_labels: Array of cluster labels for each review
            
        Returns:
            List of ComplaintClusterBase objects
        """
        clusters = []
        unique_labels = set(cluster_labels)
        
        # Remove noise label (-1) if present
        if -1 in unique_labels:
            unique_labels.remove(-1)
        
        total_reviews = len(reviews)
        
        for label in unique_labels:
            # Get reviews in this cluster
            cluster_reviews = [reviews[i] for i, l in enumerate(cluster_labels) if l == label]
            
            if len(cluster_reviews) < 2:  # Skip very small clusters
                continue
            
            # Extract cluster information
            cluster_texts = [review.text for review in cluster_reviews]
            keywords = self.extract_keywords(cluster_texts, max_keywords=5)
            
            # Generate cluster name from keywords
            cluster_name = self._generate_cluster_name(keywords, cluster_texts)
            
            # Calculate metrics
            review_count = len(cluster_reviews)
            percentage = (review_count / total_reviews) * 100
            recency_score = self._calculate_recency_score(cluster_reviews)
            
            # Get sample reviews (up to 3)
            sample_reviews = [review.text for review in cluster_reviews[:3]]
            
            cluster = ComplaintClusterBase(
                name=cluster_name,
                description=f"Cluster of {review_count} reviews about {cluster_name.lower()}",
                review_count=review_count,
                percentage=round(percentage, 2),
                recency_score=round(recency_score, 2),
                sample_reviews=sample_reviews,
                keywords=keywords
            )
            
            clusters.append(cluster)
        
        # Sort clusters by percentage (most common first)
        clusters.sort(key=lambda x: x.percentage, reverse=True)
        
        return clusters
    
    def generate_insights(self, reviews: List[Review], clusters: List[ComplaintClusterBase]) -> dict:
        """
        Generate comprehensive insights from reviews and clusters.
        
        Args:
            reviews: List of all reviews
            clusters: List of complaint clusters
            
        Returns:
            Dictionary containing insights and analytics
        """
        return self.insights_generator.generate_summary_insights(reviews, clusters)
    
    def _create_simple_clusters(self, reviews: List[Review], min_cluster_size: int) -> List[ComplaintClusterBase]:
        """
        Create simple clusters based on keyword frequency as fallback.
        
        Args:
            reviews: List of Review objects
            min_cluster_size: Minimum cluster size
            
        Returns:
            List of ComplaintClusterBase objects
        """
        # Extract all keywords
        all_texts = [review.text for review in reviews]
        keywords = self.extract_keywords(all_texts, max_keywords=20)
        
        if not keywords:
            return []
        
        clusters = []
        used_reviews = set()
        
        for keyword in keywords[:5]:  # Create up to 5 clusters
            # Find reviews containing this keyword
            keyword_reviews = []
            for i, review in enumerate(reviews):
                if i not in used_reviews and keyword.lower() in review.text.lower():
                    keyword_reviews.append(review)
                    used_reviews.add(i)
            
            if len(keyword_reviews) >= min_cluster_size:
                review_count = len(keyword_reviews)
                percentage = (review_count / len(reviews)) * 100
                recency_score = self._calculate_recency_score(keyword_reviews)
                
                cluster = ComplaintClusterBase(
                    name=f"{keyword.title()} Issues",
                    description=f"Reviews mentioning {keyword}",
                    review_count=review_count,
                    percentage=round(percentage, 2),
                    recency_score=round(recency_score, 2),
                    sample_reviews=[review.text for review in keyword_reviews[:3]],
                    keywords=[keyword]
                )
                
                clusters.append(cluster)
        
        return clusters
    
    def _generate_cluster_name(self, keywords: List[str], texts: List[str]) -> str:
        """
        Generate a descriptive name for a cluster based on keywords and texts.
        
        Args:
            keywords: List of important keywords
            texts: List of review texts in the cluster
            
        Returns:
            Generated cluster name
        """
        if not keywords:
            return "General Issues"
        
        # Use the most important keyword as base
        primary_keyword = keywords[0]
        
        # Common complaint categories mapping
        category_mapping = {
            'crash': 'App Crashes',
            'bug': 'Bug Reports',
            'slow': 'Performance Issues',
            'battery': 'Battery Drain',
            'login': 'Login Problems',
            'sync': 'Sync Issues',
            'notification': 'Notification Problems',
            'ui': 'Interface Issues',
            'feature': 'Missing Features',
            'ads': 'Advertisement Issues',
            'payment': 'Payment Problems',
            'update': 'Update Issues'
        }
        
        # Check if primary keyword matches known categories
        for key, category in category_mapping.items():
            if key in primary_keyword.lower():
                return category
        
        # Generate name from keywords
        if len(keywords) >= 2:
            return f"{keywords[0].title()} and {keywords[1].title()} Issues"
        else:
            return f"{primary_keyword.title()} Issues"
    
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
        
        recent_count = 0
        total_count = len(reviews)
        
        for review in reviews:
            if review.review_date >= three_months_ago:
                recent_count += 1
        
        # Calculate percentage of recent reviews
        recency_percentage = (recent_count / total_count) * 100
        
        return recency_percentage
    
    def rank_clusters(self, clusters: List[ComplaintClusterBase]) -> List[ComplaintClusterBase]:
        """
        Rank clusters by combined frequency and recency score.
        
        Args:
            clusters: List of ComplaintCluster objects
            
        Returns:
            Sorted list of clusters by ranking score
        """
        if not clusters:
            return clusters
        
        # Calculate combined score (70% frequency, 30% recency)
        for cluster in clusters:
            frequency_score = cluster.percentage
            recency_score = cluster.recency_score
            combined_score = (frequency_score * 0.7) + (recency_score * 0.3)
            
            # Store the combined score (we'll use percentage field for sorting)
            cluster.percentage = round(combined_score, 2)
        
        # Sort by combined score
        clusters.sort(key=lambda x: x.percentage, reverse=True)
        
        return clusters