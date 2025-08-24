import { render, screen, fireEvent } from '@testing-library/react';
import ClustersList from '../ClustersList';
import { ComplaintCluster } from '@/types';

const mockClusters: ComplaintCluster[] = [
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
      'Phone dies quickly with this app'
    ],
    keywords: ['battery', 'drain', 'power']
  },
  {
    id: 'cluster-3',
    name: 'UI Problems',
    description: 'User interface and usability issues',
    review_count: 25,
    percentage: 10.0,
    recency_score: 60.0,
    sample_reviews: [
      'Interface is confusing',
      'Hard to navigate'
    ],
    keywords: ['ui', 'interface', 'design']
  }
];

describe('ClustersList', () => {
  const mockOnClusterClick = jest.fn();

  beforeEach(() => {
    mockOnClusterClick.mockClear();
  });

  it('renders all clusters', () => {
    render(<ClustersList clusters={mockClusters} onClusterClick={mockOnClusterClick} />);
    
    expect(screen.getByText('Crash Issues')).toBeInTheDocument();
    expect(screen.getByText('Battery Drain')).toBeInTheDocument();
    expect(screen.getByText('UI Problems')).toBeInTheDocument();
  });

  it('displays cluster percentages', () => {
    render(<ClustersList clusters={mockClusters} onClusterClick={mockOnClusterClick} />);
    
    expect(screen.getByText('40.0%')).toBeInTheDocument();
    expect(screen.getByText('30.0%')).toBeInTheDocument();
    expect(screen.getByText('10.0%')).toBeInTheDocument();
  });

  it('displays cluster review counts', () => {
    render(<ClustersList clusters={mockClusters} onClusterClick={mockOnClusterClick} />);
    
    expect(screen.getByText('100 reviews')).toBeInTheDocument();
    expect(screen.getByText('75 reviews')).toBeInTheDocument();
    expect(screen.getByText('25 reviews')).toBeInTheDocument();
  });

  it('displays cluster descriptions', () => {
    render(<ClustersList clusters={mockClusters} onClusterClick={mockOnClusterClick} />);
    
    expect(screen.getByText('App crashes and stability problems')).toBeInTheDocument();
    expect(screen.getByText('Excessive battery consumption')).toBeInTheDocument();
    expect(screen.getByText('User interface and usability issues')).toBeInTheDocument();
  });

  it('calls onClusterClick when cluster is clicked', () => {
    render(<ClustersList clusters={mockClusters} onClusterClick={mockOnClusterClick} />);
    
    const crashIssuesCluster = screen.getByText('Crash Issues');
    fireEvent.click(crashIssuesCluster);
    
    expect(mockOnClusterClick).toHaveBeenCalledWith(mockClusters[0]);
  });

  it('displays recency scores', () => {
    render(<ClustersList clusters={mockClusters} onClusterClick={mockOnClusterClick} />);
    
    expect(screen.getByText(/85\.0/)).toBeInTheDocument(); // Crash Issues
    expect(screen.getByText(/70\.0/)).toBeInTheDocument(); // Battery Drain
    expect(screen.getByText(/60\.0/)).toBeInTheDocument(); // UI Problems
  });

  it('shows sample reviews preview', () => {
    render(<ClustersList clusters={mockClusters} onClusterClick={mockOnClusterClick} />);
    
    // Should show first sample review as preview
    expect(screen.getByText('App crashes on startup')).toBeInTheDocument();
    expect(screen.getByText('Battery drains too fast')).toBeInTheDocument();
    expect(screen.getByText('Interface is confusing')).toBeInTheDocument();
  });

  it('handles empty clusters array', () => {
    render(<ClustersList clusters={[]} onClusterClick={mockOnClusterClick} />);
    
    expect(screen.getByText('No complaint clusters found')).toBeInTheDocument();
  });

  it('sorts clusters by percentage in descending order', () => {
    const unsortedClusters = [...mockClusters].reverse(); // Reverse the order
    
    render(<ClustersList clusters={unsortedClusters} onClusterClick={mockOnClusterClick} />);
    
    const clusterElements = screen.getAllByTestId(/cluster-item/);
    
    // Should still be sorted by percentage (highest first)
    expect(clusterElements[0]).toHaveTextContent('Crash Issues');
    expect(clusterElements[0]).toHaveTextContent('40.0%');
    
    expect(clusterElements[1]).toHaveTextContent('Battery Drain');
    expect(clusterElements[1]).toHaveTextContent('30.0%');
    
    expect(clusterElements[2]).toHaveTextContent('UI Problems');
    expect(clusterElements[2]).toHaveTextContent('10.0%');
  });

  it('displays keywords for each cluster', () => {
    render(<ClustersList clusters={mockClusters} onClusterClick={mockOnClusterClick} />);
    
    // Keywords should be displayed as tags
    expect(screen.getByText('crash')).toBeInTheDocument();
    expect(screen.getByText('stability')).toBeInTheDocument();
    expect(screen.getByText('bug')).toBeInTheDocument();
    
    expect(screen.getByText('battery')).toBeInTheDocument();
    expect(screen.getByText('drain')).toBeInTheDocument();
    expect(screen.getByText('power')).toBeInTheDocument();
    
    expect(screen.getByText('ui')).toBeInTheDocument();
    expect(screen.getByText('interface')).toBeInTheDocument();
    expect(screen.getByText('design')).toBeInTheDocument();
  });

  it('handles clusters with no keywords', () => {
    const clustersWithoutKeywords = [
      {
        ...mockClusters[0],
        keywords: []
      }
    ];
    
    render(<ClustersList clusters={clustersWithoutKeywords} onClusterClick={mockOnClusterClick} />);
    
    expect(screen.getByText('Crash Issues')).toBeInTheDocument();
    // Should not crash and should handle empty keywords gracefully
  });

  it('handles clusters with no sample reviews', () => {
    const clustersWithoutSamples = [
      {
        ...mockClusters[0],
        sample_reviews: []
      }
    ];
    
    render(<ClustersList clusters={clustersWithoutSamples} onClusterClick={mockOnClusterClick} />);
    
    expect(screen.getByText('Crash Issues')).toBeInTheDocument();
    expect(screen.getByText('No sample reviews available')).toBeInTheDocument();
  });

  it('truncates long cluster names', () => {
    const clustersWithLongNames = [
      {
        ...mockClusters[0],
        name: 'This is an extremely long cluster name that should be truncated to prevent layout issues in the user interface'
      }
    ];
    
    render(<ClustersList clusters={clustersWithLongNames} onClusterClick={mockOnClusterClick} />);
    
    // Should display the name but potentially truncated
    expect(screen.getByText(/This is an extremely long cluster name/)).toBeInTheDocument();
  });

  it('shows hover effects on cluster items', () => {
    render(<ClustersList clusters={mockClusters} onClusterClick={mockOnClusterClick} />);
    
    const clusterItem = screen.getByTestId('cluster-item-cluster-1');
    
    // Should have cursor pointer style
    expect(clusterItem).toHaveClass('cursor-pointer');
  });

  it('displays cluster items with proper accessibility attributes', () => {
    render(<ClustersList clusters={mockClusters} onClusterClick={mockOnClusterClick} />);
    
    const clusterItems = screen.getAllByRole('button');
    
    expect(clusterItems).toHaveLength(3);
    
    // Each cluster item should be clickable and have proper aria labels
    clusterItems.forEach((item, index) => {
      expect(item).toHaveAttribute('aria-label', expect.stringContaining(mockClusters[index].name));
    });
  });

  it('handles very small percentages', () => {
    const clustersWithSmallPercentages = [
      {
        ...mockClusters[0],
        percentage: 0.1,
        review_count: 1
      }
    ];
    
    render(<ClustersList clusters={clustersWithSmallPercentages} onClusterClick={mockOnClusterClick} />);
    
    expect(screen.getByText('0.1%')).toBeInTheDocument();
    expect(screen.getByText('1 review')).toBeInTheDocument(); // Singular form
  });

  it('handles large numbers correctly', () => {
    const clustersWithLargeNumbers = [
      {
        ...mockClusters[0],
        percentage: 99.9,
        review_count: 10000
      }
    ];
    
    render(<ClustersList clusters={clustersWithLargeNumbers} onClusterClick={mockOnClusterClick} />);
    
    expect(screen.getByText('99.9%')).toBeInTheDocument();
    expect(screen.getByText('10,000 reviews')).toBeInTheDocument(); // Should format large numbers
  });

  it('displays recency indicators', () => {
    render(<ClustersList clusters={mockClusters} onClusterClick={mockOnClusterClick} />);
    
    // Should show recency indicators (e.g., "Recent", "Moderate", "Old")
    const highRecencyCluster = screen.getByTestId('cluster-item-cluster-1');
    expect(highRecencyCluster).toHaveTextContent(/Recent|High/i);
    
    const mediumRecencyCluster = screen.getByTestId('cluster-item-cluster-2');
    expect(mediumRecencyCluster).toHaveTextContent(/Moderate|Medium/i);
  });

  it('shows expand/collapse indicators', () => {
    render(<ClustersList clusters={mockClusters} onClusterClick={mockOnClusterClick} />);
    
    // Should show visual indicators that clusters can be expanded
    const expandIcons = screen.getAllByTestId(/expand-icon/);
    expect(expandIcons).toHaveLength(3);
  });

  it('handles keyboard navigation', () => {
    render(<ClustersList clusters={mockClusters} onClusterClick={mockOnClusterClick} />);
    
    const firstCluster = screen.getByTestId('cluster-item-cluster-1');
    
    // Should be focusable
    firstCluster.focus();
    expect(firstCluster).toHaveFocus();
    
    // Should respond to Enter key
    fireEvent.keyDown(firstCluster, { key: 'Enter', code: 'Enter' });
    expect(mockOnClusterClick).toHaveBeenCalledWith(mockClusters[0]);
    
    // Should respond to Space key
    fireEvent.keyDown(firstCluster, { key: ' ', code: 'Space' });
    expect(mockOnClusterClick).toHaveBeenCalledTimes(2);
  });
});