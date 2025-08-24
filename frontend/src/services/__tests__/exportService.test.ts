import { ExportService } from '../exportService';
import { Analysis } from '@/types';

// Mock Blob with text method for Node.js environment
global.Blob = class MockBlob {
  private content: string;
  
  constructor(content: string[]) {
    this.content = content.join('');
  }
  
  async text(): Promise<string> {
    return this.content;
  }
} as any;

const mockAnalysis: Analysis = {
  id: 'analysis-123',
  app_id: 'com.example.app',
  analysis_type: 'APP',
  platform: 'GOOGLE_PLAY',
  status: 'COMPLETED',
  total_reviews: 1000,
  negative_reviews: 300,
  created_at: '2024-01-15T10:00:00Z',
  completed_at: '2024-01-15T10:05:00Z',
  clusters: [
    {
      id: 'cluster-1',
      analysis_id: 'analysis-123',
      name: 'App Crashes',
      description: 'Users experiencing frequent crashes',
      review_count: 150,
      percentage: 50.0,
      recency_score: 85.0,
      sample_reviews: [
        'App crashes constantly on Android 14',
        'Keeps crashing when I try to login',
        'Crashes every time I open it'
      ],
      keywords: ['crash', 'freeze', 'bug']
    },
    {
      id: 'cluster-2',
      analysis_id: 'analysis-123',
      name: 'Battery Drain',
      description: 'High battery consumption issues',
      review_count: 100,
      percentage: 33.3,
      recency_score: 72.0,
      sample_reviews: [
        'Battery drains too fast',
        'Phone dies in 2 hours'
      ],
      keywords: ['battery', 'drain', 'power']
    }
  ]
};

describe('ExportService', () => {
  let progressCallback: jest.Mock;
  let exportService: ExportService;

  beforeEach(() => {
    progressCallback = jest.fn();
    exportService = new ExportService(progressCallback);
  });

  describe('CSV Export', () => {
    it('generates CSV with proper headers and data', async () => {
      const blob = await exportService.exportToCSV(mockAnalysis);
      const text = await blob.text();

      // Check metadata section
      expect(text).toContain('Analysis Metadata');
      expect(text).toContain('analysis-123');
      expect(text).toContain('APP');
      expect(text).toContain('com.example.app');
      expect(text).toContain('GOOGLE_PLAY');

      // Check cluster data headers
      expect(text).toContain('Cluster Name');
      expect(text).toContain('Description');
      expect(text).toContain('Review Count');
      expect(text).toContain('Percentage');

      // Check cluster data
      expect(text).toContain('App Crashes');
      expect(text).toContain('Battery Drain');
      expect(text).toContain('50.00');
      expect(text).toContain('33.30');
    });

    it('escapes quotes in CSV data', async () => {
      const analysisWithQuotes = {
        ...mockAnalysis,
        clusters: [{
          ...mockAnalysis.clusters[0],
          name: 'App "Crashes" Frequently',
          sample_reviews: ['App says "Error occurred"']
        }]
      };

      const blob = await exportService.exportToCSV(analysisWithQuotes);
      const text = await blob.text();

      expect(text).toContain('"App ""Crashes"" Frequently"');
      expect(text).toContain('"App says ""Error occurred"""');
    });

    it('calls progress callback during export', async () => {
      await exportService.exportToCSV(mockAnalysis);

      expect(progressCallback).toHaveBeenCalledWith({
        stage: 'preparing',
        progress: 10,
        message: 'Preparing CSV data...'
      });

      expect(progressCallback).toHaveBeenCalledWith({
        stage: 'complete',
        progress: 100,
        message: 'CSV export complete!'
      });
    });
  });

  describe('JSON Export', () => {
    it('generates structured JSON with metadata and insights', async () => {
      const blob = await exportService.exportToJSON(mockAnalysis);
      const text = await blob.text();
      const data = JSON.parse(text);

      // Check metadata
      expect(data.metadata.analysis_id).toBe('analysis-123');
      expect(data.metadata.analysis_type).toBe('APP');
      expect(data.metadata.export_version).toBe('1.0');

      // Check summary
      expect(data.summary.total_reviews).toBe(1000);
      expect(data.summary.negative_reviews).toBe(300);
      expect(data.summary.clusters_count).toBe(2);

      // Check clusters with insights
      expect(data.clusters).toHaveLength(2);
      expect(data.clusters[0].rank).toBe(1);
      expect(data.clusters[0].insights.is_top_complaint).toBe(true);
      expect(data.clusters[0].insights.priority_level).toBe('high');

      // Check recommendations
      expect(data.recommendations).toBeInstanceOf(Array);
      expect(data.recommendations.length).toBeGreaterThan(0);
    });

    it('calculates priority levels correctly', async () => {
      const blob = await exportService.exportToJSON(mockAnalysis);
      const text = await blob.text();
      const data = JSON.parse(text);

      // First cluster should be high priority (rank 0, high percentage)
      expect(data.clusters[0].insights.priority_level).toBe('high');
      
      // Second cluster should be medium priority
      expect(data.clusters[1].insights.priority_level).toBe('medium');
    });

    it('includes sample reviews with metadata', async () => {
      const blob = await exportService.exportToJSON(mockAnalysis);
      const text = await blob.text();
      const data = JSON.parse(text);

      const firstCluster = data.clusters[0];
      expect(firstCluster.sample_reviews).toHaveLength(3);
      expect(firstCluster.sample_reviews[0]).toEqual({
        index: 1,
        text: 'App crashes constantly on Android 14',
        length: 36
      });
    });

    it('generates appropriate recommendations', async () => {
      const blob = await exportService.exportToJSON(mockAnalysis);
      const text = await blob.text();
      const data = JSON.parse(text);

      expect(data.recommendations).toContain(
        'Focus on addressing "App Crashes" as it affects 50.0% of negative reviews'
      );
    });
  });

  describe('Static Methods', () => {
    it('generates appropriate filename for app analysis', () => {
      const filename = ExportService.generateFilename(mockAnalysis, 'csv');
      expect(filename).toMatch(/^review-analysis-com\.example\.app-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.csv$/);
    });

    it('generates appropriate filename for website analysis', () => {
      const websiteAnalysis = {
        ...mockAnalysis,
        analysis_type: 'WEBSITE' as const,
        app_id: undefined,
        website_url: 'https://example.com'
      };

      const filename = ExportService.generateFilename(websiteAnalysis, 'json');
      expect(filename).toMatch(/^review-analysis-https---example-com-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.json$/);
    });

    it('downloads file correctly', async () => {
      const mockBlob = new Blob(['test content'], { type: 'text/plain' });
      const mockLink = {
        href: '',
        download: '',
        click: jest.fn()
      };

      // Mock DOM methods
      const createElementSpy = jest.spyOn(document, 'createElement').mockReturnValue(mockLink as any);
      const appendChildSpy = jest.spyOn(document.body, 'appendChild').mockImplementation();
      const removeChildSpy = jest.spyOn(document.body, 'removeChild').mockImplementation();

      await ExportService.downloadFile(mockBlob, 'test.txt');

      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(mockLink.download).toBe('test.txt');
      expect(mockLink.click).toHaveBeenCalled();
      expect(appendChildSpy).toHaveBeenCalledWith(mockLink);
      expect(removeChildSpy).toHaveBeenCalledWith(mockLink);

      createElementSpy.mockRestore();
      appendChildSpy.mockRestore();
      removeChildSpy.mockRestore();
    });
  });

  describe('Edge Cases', () => {
    it('handles analysis with no clusters', async () => {
      const emptyAnalysis = {
        ...mockAnalysis,
        clusters: []
      };

      const csvBlob = await exportService.exportToCSV(emptyAnalysis);
      const csvText = await csvBlob.text();
      expect(csvText).toContain('Analysis Metadata');

      const jsonBlob = await exportService.exportToJSON(emptyAnalysis);
      const jsonText = await jsonBlob.text();
      const jsonData = JSON.parse(jsonText);
      expect(jsonData.clusters).toHaveLength(0);
      expect(jsonData.recommendations).toContain('Continue monitoring user feedback for emerging complaint patterns');
    });

    it('handles clusters with missing sample reviews', async () => {
      const analysisWithEmptyReviews = {
        ...mockAnalysis,
        clusters: [{
          ...mockAnalysis.clusters[0],
          sample_reviews: []
        }]
      };

      const blob = await exportService.exportToCSV(analysisWithEmptyReviews);
      const text = await blob.text();
      
      // Should handle empty sample reviews gracefully
      expect(text).toContain('App Crashes');
    });
  });
});