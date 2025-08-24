export interface Review {
  id: string;
  app_id?: string;
  website_url?: string;
  platform: Platform;
  source_platform: string;
  rating?: number;
  text: string;
  date: string;
  locale: string;
  processed: boolean;
}

export interface ComplaintCluster {
  id: string;
  analysis_id: string;
  name: string;
  description: string;
  review_count: number;
  percentage: number;
  recency_score: number;
  sample_reviews: string[];
  keywords: string[];
}

export interface Analysis {
  id: string;
  app_id?: string;
  website_url?: string;
  analysis_type: 'APP' | 'WEBSITE';
  platform?: Platform;
  status: AnalysisStatus;
  total_reviews: number;
  negative_reviews: number;
  clusters: ComplaintCluster[];
  created_at: string;
  completed_at?: string;
}

export type Platform = 'GOOGLE_PLAY' | 'APP_STORE' | 'GOOGLE_REVIEWS' | 'YELP' | 'FACEBOOK' | 'TWITTER';

export type AnalysisStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface AnalysisRequest {
  input: string; // URL or app ID
  analysis_type: 'APP' | 'WEBSITE';
}

export interface SummaryStats {
  total_reviews: number;
  negative_reviews: number;
  negative_percentage: number;
  top_complaints: string[];
}