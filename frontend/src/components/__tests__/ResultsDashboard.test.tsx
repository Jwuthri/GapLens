import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ResultsDashboard from '../ResultsDashboard';
import { AnalysisResult } from '@/types';

const mockAnalysisResult: AnalysisResult = {
  analysis: {
    id: 'test-analysis-id',
    app_id: 'com.test.app',
    analysis_type: 'APP',
    platform: 'GOOGLE_PLAY',
    status: 'completed',
    created_at: '2024-01-15T10:00:00Z',
    completed_at: '2024-01-15T10:05:00Z'
  },
  summary: {
    total_reviews: 1000,
    negative_reviews: 250,
    negative_percentage: 25.0,
    analysis_date: '2024-01-15T10:05:00Z'
  },
  clusters: [
    {
      id: 'cluster-1',
      name: 'Crash Issues',
      description: 'App crashes and stability problems',
      review_count: 100,
      percentage: 40.0,
      recency_score: 85.0,
      sample_reviews: [
        'App crashes on startup',
        'Constant crashes when opening',
        'Crashes every time I try to use it'
      ],
      keywords: ['crash', 'stability', 'bug']
    },
    {
      id: 'cluster-2',
      name: 'Battery Drain',
      description: 'Excessive battery consumption',
      review_count: 75,
      percentage: 30.0,
      recency_score: 70.0,
      sample_reviews: [
        'Battery drains too fast',
        'Phone dies quickly with this app',
        'Terrible battery optimization'
      ],
      keywords: ['battery', 'drain', 'power']
    },
    {
      id: 'cluster-3',
      name: 'UI Problems',
      description: 'User interface and usability issues',
      review_count: 50,
      percentage: 20.0,
      recency_score: 60.0,
      sample_reviews: [
        'Interface is confusing',
        'Hard to navigate',
        'Poor design choices'
      ],
      keywords: ['ui', 'interface', 'design']
    }
  ],
  trends: [
    {
      month: '2024-01',
      crash_issues: 45,
      battery_drain: 30,
      ui_problems: 25
    },
    {
      month: '2024-02',
      crash_issues: 55,
      battery_drain: 35,
      ui_problems: 20
    }
  ]
};

// Mock the export service
jest.mock('@/services/exportService', () => ({
  exportToCSV: jest.fn().mockResolvedValue(undefined),
  exportToJSON: jest.fn().mockResolvedValue(undefined),
}));

describe('ResultsDashboard', () => {
  const mockOnExport = jest.fn();

  beforeEach(() => {
    mockOnExport.mockClear();
  });

  it('renders dashboard with analysis results', () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    // Check summary stats
    expect(screen.getByText('1,000')).toBeInTheDocument(); // Total reviews
    expect(screen.getByText('250')).toBeInTheDocument(); // Negative reviews
    expect(screen.getByText('25.0%')).toBeInTheDocument(); // Negative percentage
    
    // Check clusters are displayed
    expect(screen.getByText('Crash Issues')).toBeInTheDocument();
    expect(screen.getByText('Battery Drain')).toBeInTheDocument();
    expect(screen.getByText('UI Problems')).toBeInTheDocument();
  });

  it('displays cluster percentages correctly', () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    expect(screen.getByText('40.0%')).toBeInTheDocument(); // Crash Issues
    expect(screen.getByText('30.0%')).toBeInTheDocument(); // Battery Drain
    expect(screen.getByText('20.0%')).toBeInTheDocument(); // UI Problems
  });

  it('shows cluster review counts', () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    expect(screen.getByText('100 reviews')).toBeInTheDocument(); // Crash Issues
    expect(screen.getByText('75 reviews')).toBeInTheDocument(); // Battery Drain
    expect(screen.getByText('50 reviews')).toBeInTheDocument(); // UI Problems
  });

  it('opens cluster detail modal when cluster is clicked', async () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    const crashIssuesCluster = screen.getByText('Crash Issues');
    fireEvent.click(crashIssuesCluster);
    
    await waitFor(() => {
      expect(screen.getByText('App crashes on startup')).toBeInTheDocument();
      expect(screen.getByText('Constant crashes when opening')).toBeInTheDocument();
    });
  });

  it('displays export buttons', () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    expect(screen.getByText('Export CSV')).toBeInTheDocument();
    expect(screen.getByText('Export JSON')).toBeInTheDocument();
  });

  it('calls onExport when export buttons are clicked', () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    const csvButton = screen.getByText('Export CSV');
    const jsonButton = screen.getByText('Export JSON');
    
    fireEvent.click(csvButton);
    expect(mockOnExport).toHaveBeenCalledWith('csv');
    
    fireEvent.click(jsonButton);
    expect(mockOnExport).toHaveBeenCalledWith('json');
  });

  it('renders time trend chart when trends data is available', () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });

  it('renders clusters chart', () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('handles empty clusters gracefully', () => {
    const emptyResult = {
      ...mockAnalysisResult,
      clusters: []
    };
    
    render(<ResultsDashboard result={emptyResult} onExport={mockOnExport} />);
    
    expect(screen.getByText('No complaint clusters found')).toBeInTheDocument();
  });

  it('displays app information correctly', () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    expect(screen.getByText('com.test.app')).toBeInTheDocument();
    expect(screen.getByText('Google Play Store')).toBeInTheDocument();
  });

  it('displays website information for website analysis', () => {
    const websiteResult = {
      ...mockAnalysisResult,
      analysis: {
        ...mockAnalysisResult.analysis,
        app_id: undefined,
        website_url: 'https://example.com',
        analysis_type: 'WEBSITE' as const,
        platform: undefined
      }
    };
    
    render(<ResultsDashboard result={websiteResult} onExport={mockOnExport} />);
    
    expect(screen.getByText('https://example.com')).toBeInTheDocument();
    expect(screen.getByText('Website Analysis')).toBeInTheDocument();
  });

  it('shows recency scores for clusters', () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    // Recency scores should be displayed somewhere in the cluster information
    expect(screen.getByText(/85\.0/)).toBeInTheDocument(); // Crash Issues recency
    expect(screen.getByText(/70\.0/)).toBeInTheDocument(); // Battery Drain recency
    expect(screen.getByText(/60\.0/)).toBeInTheDocument(); // UI Problems recency
  });

  it('displays keywords for clusters', async () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    // Click on a cluster to see details
    const crashIssuesCluster = screen.getByText('Crash Issues');
    fireEvent.click(crashIssuesCluster);
    
    await waitFor(() => {
      expect(screen.getByText('crash')).toBeInTheDocument();
      expect(screen.getByText('stability')).toBeInTheDocument();
      expect(screen.getByText('bug')).toBeInTheDocument();
    });
  });

  it('handles loading state', () => {
    render(<ResultsDashboard result={null} onExport={mockOnExport} />);
    
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('sorts clusters by percentage in descending order', () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    const clusterElements = screen.getAllByTestId(/cluster-item/);
    
    // First cluster should be Crash Issues (40%)
    expect(clusterElements[0]).toHaveTextContent('Crash Issues');
    expect(clusterElements[0]).toHaveTextContent('40.0%');
    
    // Second cluster should be Battery Drain (30%)
    expect(clusterElements[1]).toHaveTextContent('Battery Drain');
    expect(clusterElements[1]).toHaveTextContent('30.0%');
    
    // Third cluster should be UI Problems (20%)
    expect(clusterElements[2]).toHaveTextContent('UI Problems');
    expect(clusterElements[2]).toHaveTextContent('20.0%');
  });

  it('displays analysis completion time', () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    // Should display formatted completion time
    expect(screen.getByText(/January 15, 2024/)).toBeInTheDocument();
  });

  it('shows processing time duration', () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    // Should calculate and display processing duration (5 minutes in this case)
    expect(screen.getByText(/5 minutes/)).toBeInTheDocument();
  });

  it('handles clusters with no sample reviews', () => {
    const resultWithEmptyReviews = {
      ...mockAnalysisResult,
      clusters: [
        {
          ...mockAnalysisResult.clusters[0],
          sample_reviews: []
        }
      ]
    };
    
    render(<ResultsDashboard result={resultWithEmptyReviews} onExport={mockOnExport} />);
    
    const clusterElement = screen.getByText('Crash Issues');
    fireEvent.click(clusterElement);
    
    expect(screen.getByText('No sample reviews available')).toBeInTheDocument();
  });

  it('handles very long cluster names gracefully', () => {
    const resultWithLongName = {
      ...mockAnalysisResult,
      clusters: [
        {
          ...mockAnalysisResult.clusters[0],
          name: 'This is a very long cluster name that should be handled gracefully by the UI component'
        }
      ]
    };
    
    render(<ResultsDashboard result={resultWithLongName} onExport={mockOnExport} />);
    
    expect(screen.getByText(/This is a very long cluster name/)).toBeInTheDocument();
  });

  it('displays cluster descriptions in detail view', async () => {
    render(<ResultsDashboard result={mockAnalysisResult} onExport={mockOnExport} />);
    
    const crashIssuesCluster = screen.getByText('Crash Issues');
    fireEvent.click(crashIssuesCluster);
    
    await waitFor(() => {
      expect(screen.getByText('App crashes and stability problems')).toBeInTheDocument();
    });
  });
});