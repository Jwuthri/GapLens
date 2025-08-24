import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ExportModal from '../ExportModal';
import { Analysis } from '@/types';
import * as exportService from '@/services/exportService';

// Mock the export service
jest.mock('@/services/exportService');

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
      sample_reviews: ['App crashes constantly'],
      keywords: ['crash', 'freeze']
    }
  ]
};

const mockExportService = exportService.ExportService as jest.MockedClass<typeof exportService.ExportService>;

describe('ExportModal', () => {
  const mockOnClose = jest.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
    jest.clearAllMocks();
  });

  it('does not render when isOpen is false', () => {
    render(
      <ExportModal
        analysis={mockAnalysis}
        isOpen={false}
        onClose={mockOnClose}
      />
    );

    expect(screen.queryByText('Export Analysis')).not.toBeInTheDocument();
  });

  it('renders modal content when isOpen is true', () => {
    render(
      <ExportModal
        analysis={mockAnalysis}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('Export Analysis')).toBeInTheDocument();
    expect(screen.getByText('Analysis Details')).toBeInTheDocument();
    expect(screen.getByText('CSV Format')).toBeInTheDocument();
    expect(screen.getByText('JSON Format')).toBeInTheDocument();
  });

  it('displays correct analysis information for app analysis', () => {
    render(
      <ExportModal
        analysis={mockAnalysis}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('com.example.app (GOOGLE_PLAY)')).toBeInTheDocument();
    expect(screen.getByText('1,000')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument(); // clusters count
  });

  it('displays correct analysis information for website analysis', () => {
    const websiteAnalysis = {
      ...mockAnalysis,
      analysis_type: 'WEBSITE' as const,
      app_id: undefined,
      website_url: 'https://example.com'
    };

    render(
      <ExportModal
        analysis={websiteAnalysis}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('https://example.com')).toBeInTheDocument();
  });

  it('closes modal when close button is clicked', () => {
    render(
      <ExportModal
        analysis={mockAnalysis}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('closes modal when X button is clicked', () => {
    render(
      <ExportModal
        analysis={mockAnalysis}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const xButton = screen.getByRole('button', { name: '' }); // X button has no text
    fireEvent.click(xButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  describe('CSV Export', () => {
    it('initiates CSV export when CSV button is clicked', async () => {
      const mockBlob = new Blob(['csv content'], { type: 'text/csv' });
      const mockExportToCSV = jest.fn().mockResolvedValue(mockBlob);
      const mockGenerateFilename = jest.fn().mockReturnValue('test.csv');
      const mockDownloadFile = jest.fn().mockResolvedValue(undefined);

      mockExportService.mockImplementation(() => ({
        exportToCSV: mockExportToCSV,
        exportToJSON: jest.fn(),
      }) as any);

      mockExportService.generateFilename = mockGenerateFilename;
      mockExportService.downloadFile = mockDownloadFile;

      render(
        <ExportModal
          analysis={mockAnalysis}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const csvButton = screen.getByText('CSV Format').closest('button');
      fireEvent.click(csvButton!);

      await waitFor(() => {
        expect(mockExportToCSV).toHaveBeenCalledWith(mockAnalysis);
      });

      expect(mockGenerateFilename).toHaveBeenCalledWith(mockAnalysis, 'csv');
      expect(mockDownloadFile).toHaveBeenCalledWith(mockBlob, 'test.csv');
    });

    it('shows success message after successful CSV export', async () => {
      const mockBlob = new Blob(['csv content'], { type: 'text/csv' });
      const mockExportToCSV = jest.fn().mockResolvedValue(mockBlob);

      mockExportService.mockImplementation(() => ({
        exportToCSV: mockExportToCSV,
        exportToJSON: jest.fn(),
      }) as any);

      mockExportService.generateFilename = jest.fn().mockReturnValue('test.csv');
      mockExportService.downloadFile = jest.fn().mockResolvedValue(undefined);

      render(
        <ExportModal
          analysis={mockAnalysis}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const csvButton = screen.getByText('CSV Format').closest('button');
      fireEvent.click(csvButton!);

      await waitFor(() => {
        expect(screen.getByText('Successfully exported as test.csv')).toBeInTheDocument();
      });
    });
  });

  describe('JSON Export', () => {
    it('initiates JSON export when JSON button is clicked', async () => {
      const mockBlob = new Blob(['json content'], { type: 'application/json' });
      const mockExportToJSON = jest.fn().mockResolvedValue(mockBlob);
      const mockGenerateFilename = jest.fn().mockReturnValue('test.json');
      const mockDownloadFile = jest.fn().mockResolvedValue(undefined);

      mockExportService.mockImplementation(() => ({
        exportToCSV: jest.fn(),
        exportToJSON: mockExportToJSON,
      }) as any);

      mockExportService.generateFilename = mockGenerateFilename;
      mockExportService.downloadFile = mockDownloadFile;

      render(
        <ExportModal
          analysis={mockAnalysis}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const jsonButton = screen.getByText('JSON Format').closest('button');
      fireEvent.click(jsonButton!);

      await waitFor(() => {
        expect(mockExportToJSON).toHaveBeenCalledWith(mockAnalysis);
      });

      expect(mockGenerateFilename).toHaveBeenCalledWith(mockAnalysis, 'json');
      expect(mockDownloadFile).toHaveBeenCalledWith(mockBlob, 'test.json');
    });
  });

  describe('Progress Tracking', () => {
    it('shows progress indicator during export', async () => {
      let progressCallback: (progress: any) => void;
      
      mockExportService.mockImplementation((callback) => {
        progressCallback = callback;
        return {
          exportToCSV: jest.fn().mockImplementation(async () => {
            progressCallback({ stage: 'preparing', progress: 50, message: 'Preparing data...' });
            return new Blob(['csv content'], { type: 'text/csv' });
          }),
          exportToJSON: jest.fn(),
        } as any;
      });

      mockExportService.generateFilename = jest.fn().mockReturnValue('test.csv');
      mockExportService.downloadFile = jest.fn().mockResolvedValue(undefined);

      render(
        <ExportModal
          analysis={mockAnalysis}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const csvButton = screen.getByText('CSV Format').closest('button');
      fireEvent.click(csvButton!);

      await waitFor(() => {
        expect(screen.getByText('Preparing data...')).toBeInTheDocument();
        expect(screen.getByText('50%')).toBeInTheDocument();
      });
    });

    it('disables buttons during export', async () => {
      mockExportService.mockImplementation(() => ({
        exportToCSV: jest.fn().mockImplementation(() => new Promise(() => {})), // Never resolves
        exportToJSON: jest.fn(),
      }) as any);

      render(
        <ExportModal
          analysis={mockAnalysis}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const csvButton = screen.getByText('CSV Format').closest('button');
      const jsonButton = screen.getByText('JSON Format').closest('button');
      const closeButton = screen.getByRole('button', { name: /close/i });

      fireEvent.click(csvButton!);

      await waitFor(() => {
        expect(csvButton).toBeDisabled();
        expect(jsonButton).toBeDisabled();
        expect(closeButton).toHaveTextContent('Exporting...');
      });
    });
  });

  describe('Error Handling', () => {
    it('shows error message when export fails', async () => {
      const mockError = new Error('Export failed');
      
      mockExportService.mockImplementation(() => ({
        exportToCSV: jest.fn().mockRejectedValue(mockError),
        exportToJSON: jest.fn(),
      }) as any);

      render(
        <ExportModal
          analysis={mockAnalysis}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const csvButton = screen.getByText('CSV Format').closest('button');
      fireEvent.click(csvButton!);

      await waitFor(() => {
        expect(screen.getByText('Export failed')).toBeInTheDocument();
      });
    });

    it('re-enables buttons after export error', async () => {
      const mockError = new Error('Export failed');
      
      mockExportService.mockImplementation(() => ({
        exportToCSV: jest.fn().mockRejectedValue(mockError),
        exportToJSON: jest.fn(),
      }) as any);

      render(
        <ExportModal
          analysis={mockAnalysis}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const csvButton = screen.getByText('CSV Format').closest('button');
      const closeButton = screen.getByRole('button', { name: /close/i });

      fireEvent.click(csvButton!);

      await waitFor(() => {
        expect(screen.getByText('Export failed')).toBeInTheDocument();
      });

      expect(csvButton).not.toBeDisabled();
      expect(closeButton).toHaveTextContent('Close');
    });
  });
});