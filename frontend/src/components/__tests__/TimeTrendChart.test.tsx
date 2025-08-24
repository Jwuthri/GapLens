import { render, screen } from '@testing-library/react';
import TimeTrendChart from '../TimeTrendChart';
import { ComplaintCluster } from '@/types';

const mockClusters: ComplaintCluster[] = [
  {
    id: '1',
    analysis_id: 'analysis-1',
    name: 'App Crashes',
    description: 'Users experiencing frequent crashes',
    review_count: 150,
    percentage: 25.5,
    recency_score: 85.0,
    sample_reviews: ['App crashes constantly', 'Keeps crashing on startup'],
    keywords: ['crash', 'freeze', 'bug']
  },
  {
    id: '2',
    analysis_id: 'analysis-1',
    name: 'Battery Drain',
    description: 'High battery consumption issues',
    review_count: 100,
    percentage: 18.2,
    recency_score: 72.0,
    sample_reviews: ['Battery drains too fast', 'Phone dies quickly'],
    keywords: ['battery', 'drain', 'power']
  },
  {
    id: '3',
    analysis_id: 'analysis-1',
    name: 'Slow Performance',
    description: 'App runs slowly',
    review_count: 80,
    percentage: 15.1,
    recency_score: 60.0,
    sample_reviews: ['App is very slow', 'Takes forever to load'],
    keywords: ['slow', 'performance', 'lag']
  }
];

describe('TimeTrendChart', () => {
  it('renders chart with cluster data', () => {
    render(<TimeTrendChart clusters={mockClusters} />);
    
    const chart = screen.getByTestId('line-chart');
    expect(chart).toBeInTheDocument();
    
    // Check that chart data contains the expected structure
    const chartData = JSON.parse(chart.getAttribute('data-chart-data') || '{}');
    expect(chartData.datasets).toHaveLength(3);
  });

  it('shows empty state when no clusters provided', () => {
    render(<TimeTrendChart clusters={[]} />);
    
    expect(screen.getByText('No Trend Data Available')).toBeInTheDocument();
    expect(screen.getByText(/Time trend chart will appear here/)).toBeInTheDocument();
    expect(screen.queryByTestId('line-chart')).not.toBeInTheDocument();
  });

  it('filters clusters when selectedClusterIds provided', () => {
    render(<TimeTrendChart clusters={mockClusters} selectedClusterIds={['1', '2']} />);
    
    const chart = screen.getByTestId('line-chart');
    expect(chart).toBeInTheDocument();
    
    // Check that chart data contains filtered clusters
    const chartData = JSON.parse(chart.getAttribute('data-chart-data') || '{}');
    expect(chartData.datasets).toHaveLength(2);
    expect(chartData.datasets[0].label).toBe('App Crashes');
    expect(chartData.datasets[1].label).toBe('Battery Drain');
  });

  it('shows top 5 clusters when no selection provided', () => {
    const manyClusters = Array.from({ length: 10 }, (_, i) => ({
      ...mockClusters[0],
      id: `cluster-${i}`,
      name: `Cluster ${i}`,
      percentage: 20 - i * 2
    }));

    render(<TimeTrendChart clusters={manyClusters} />);
    
    const chart = screen.getByTestId('line-chart');
    const chartData = JSON.parse(chart.getAttribute('data-chart-data') || '{}');
    
    // Should show only top 5 clusters
    expect(chartData.datasets).toHaveLength(5);
  });

  it('displays correct description text', () => {
    render(<TimeTrendChart clusters={mockClusters} />);
    
    expect(screen.getByText(/Showing trends for 3 complaint categories/)).toBeInTheDocument();
    expect(screen.getByText(/Displaying top 5 clusters by frequency/)).toBeInTheDocument();
  });

  it('displays filtered description when clusters are selected', () => {
    render(<TimeTrendChart clusters={mockClusters} selectedClusterIds={['1']} />);
    
    expect(screen.getByText(/Showing trends for 1 complaint categories/)).toBeInTheDocument();
    expect(screen.getByText(/Filtered to selected clusters/)).toBeInTheDocument();
  });

  it('generates 12 months of data points', () => {
    render(<TimeTrendChart clusters={mockClusters} />);
    
    const chart = screen.getByTestId('line-chart');
    const chartData = JSON.parse(chart.getAttribute('data-chart-data') || '{}');
    
    // Should have 12 months of labels
    expect(chartData.labels).toHaveLength(12);
    
    // Each dataset should have 12 data points
    chartData.datasets.forEach((dataset: any) => {
      expect(dataset.data).toHaveLength(12);
    });
  });

  it('truncates long cluster names in legend', () => {
    const longNameCluster = {
      ...mockClusters[0],
      name: 'This is a very long cluster name that should be truncated for display purposes'
    };

    render(<TimeTrendChart clusters={[longNameCluster]} />);
    
    const chart = screen.getByTestId('line-chart');
    const chartData = JSON.parse(chart.getAttribute('data-chart-data') || '{}');
    
    expect(chartData.datasets[0].label).toBe('This is a very long cluster na...');
  });
});