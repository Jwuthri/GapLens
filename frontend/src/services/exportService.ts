import { Analysis, ComplaintCluster } from '@/types';

export interface ExportProgress {
  stage: string;
  progress: number;
  message: string;
}

export class ExportService {
  private onProgress?: (progress: ExportProgress) => void;

  constructor(onProgress?: (progress: ExportProgress) => void) {
    this.onProgress = onProgress;
  }

  private updateProgress(stage: string, progress: number, message: string) {
    if (this.onProgress) {
      this.onProgress({ stage, progress, message });
    }
  }

  async exportToCSV(analysis: Analysis): Promise<Blob> {
    this.updateProgress('preparing', 10, 'Preparing CSV data...');

    // CSV Headers
    const headers = [
      'Cluster Name',
      'Description',
      'Review Count',
      'Percentage',
      'Recency Score',
      'Keywords',
      'Sample Review 1',
      'Sample Review 2',
      'Sample Review 3'
    ];

    this.updateProgress('formatting', 30, 'Formatting cluster data...');

    // Format cluster data
    const rows = analysis.clusters.map(cluster => [
      `"${cluster.name.replace(/"/g, '""')}"`, // Escape quotes
      `"${cluster.description.replace(/"/g, '""')}"`,
      cluster.review_count.toString(),
      cluster.percentage.toFixed(2),
      cluster.recency_score.toFixed(1),
      `"${cluster.keywords.join(', ')}"`,
      `"${(cluster.sample_reviews[0] || '').replace(/"/g, '""')}"`,
      `"${(cluster.sample_reviews[1] || '').replace(/"/g, '""')}"`,
      `"${(cluster.sample_reviews[2] || '').replace(/"/g, '""')}"`,
    ]);

    this.updateProgress('generating', 60, 'Generating CSV file...');

    // Create metadata section
    const metadata = [
      ['Analysis Metadata'],
      ['Analysis ID', analysis.id],
      ['Analysis Type', analysis.analysis_type],
      ['App ID', analysis.app_id || 'N/A'],
      ['Website URL', analysis.website_url || 'N/A'],
      ['Platform', analysis.platform || 'N/A'],
      ['Total Reviews', analysis.total_reviews.toString()],
      ['Negative Reviews', analysis.negative_reviews.toString()],
      ['Negative Percentage', `${((analysis.negative_reviews / analysis.total_reviews) * 100).toFixed(1)}%`],
      ['Created At', new Date(analysis.created_at).toLocaleString()],
      ['Completed At', analysis.completed_at ? new Date(analysis.completed_at).toLocaleString() : 'N/A'],
      [''], // Empty row separator
      ['Complaint Clusters'],
      headers
    ];

    this.updateProgress('finalizing', 80, 'Finalizing CSV...');

    // Combine metadata and data
    const csvContent = [...metadata, ...rows]
      .map(row => row.join(','))
      .join('\n');

    this.updateProgress('complete', 100, 'CSV export complete!');

    return new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  }

  async exportToJSON(analysis: Analysis): Promise<Blob> {
    this.updateProgress('preparing', 10, 'Preparing JSON data...');

    // Create comprehensive JSON structure
    const exportData = {
      metadata: {
        analysis_id: analysis.id,
        analysis_type: analysis.analysis_type,
        app_id: analysis.app_id,
        website_url: analysis.website_url,
        platform: analysis.platform,
        status: analysis.status,
        created_at: analysis.created_at,
        completed_at: analysis.completed_at,
        export_timestamp: new Date().toISOString(),
        export_version: '1.0'
      },
      summary: {
        total_reviews: analysis.total_reviews,
        negative_reviews: analysis.negative_reviews,
        negative_percentage: (analysis.negative_reviews / analysis.total_reviews) * 100,
        clusters_count: analysis.clusters.length,
        top_complaint: analysis.clusters[0]?.name || null,
        recent_clusters: analysis.clusters.filter(c => c.recency_score > 70).length
      },
      clusters: analysis.clusters.map((cluster, index) => ({
        rank: index + 1,
        id: cluster.id,
        name: cluster.name,
        description: cluster.description,
        metrics: {
          review_count: cluster.review_count,
          percentage: cluster.percentage,
          recency_score: cluster.recency_score,
          severity_rank: index + 1
        },
        keywords: cluster.keywords,
        sample_reviews: cluster.sample_reviews.map((review, reviewIndex) => ({
          index: reviewIndex + 1,
          text: review,
          length: review.length
        })),
        insights: {
          is_top_complaint: index === 0,
          is_recent: cluster.recency_score > 70,
          is_significant: cluster.percentage > 5,
          priority_level: this.calculatePriorityLevel(cluster, index)
        }
      })),
      recommendations: this.generateRecommendations(analysis)
    };

    this.updateProgress('formatting', 50, 'Formatting JSON structure...');

    // Add pretty formatting with proper indentation
    const jsonString = JSON.stringify(exportData, null, 2);

    this.updateProgress('complete', 100, 'JSON export complete!');

    return new Blob([jsonString], { type: 'application/json;charset=utf-8;' });
  }

  private calculatePriorityLevel(cluster: ComplaintCluster, rank: number): 'high' | 'medium' | 'low' {
    if (rank === 0 || (cluster.percentage > 10 && cluster.recency_score > 80)) {
      return 'high';
    } else if (cluster.percentage > 5 || cluster.recency_score > 60) {
      return 'medium';
    } else {
      return 'low';
    }
  }

  private generateRecommendations(analysis: Analysis): string[] {
    const recommendations: string[] = [];
    const topClusters = analysis.clusters.slice(0, 3);

    if (topClusters.length > 0) {
      recommendations.push(
        `Focus on addressing "${topClusters[0].name}" as it affects ${topClusters[0].percentage.toFixed(1)}% of negative reviews`
      );
    }

    const recentClusters = analysis.clusters.filter(c => c.recency_score > 70);
    if (recentClusters.length > 0) {
      recommendations.push(
        `${recentClusters.length} complaint categories show recent activity - prioritize these for immediate attention`
      );
    }

    const highImpactClusters = analysis.clusters.filter(c => c.percentage > 10);
    if (highImpactClusters.length > 1) {
      recommendations.push(
        `Address the top ${Math.min(3, highImpactClusters.length)} clusters to resolve ${
          highImpactClusters.slice(0, 3).reduce((sum, c) => sum + c.percentage, 0).toFixed(1)
        }% of user complaints`
      );
    }

    if (recommendations.length === 0) {
      recommendations.push('Continue monitoring user feedback for emerging complaint patterns');
    }

    return recommendations;
  }

  static async downloadFile(blob: Blob, filename: string): Promise<void> {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  static generateFilename(analysis: Analysis, format: 'csv' | 'json'): string {
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
    const identifier = analysis.app_id || analysis.website_url?.replace(/[^a-zA-Z0-9]/g, '-') || 'analysis';
    return `review-analysis-${identifier}-${timestamp}.${format}`;
  }
}