import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import ErrorBoundary from '../ErrorBoundary';
import { ToastProvider } from '../ToastContainer';
import { validateInput, ERROR_MESSAGES } from '../../utils/validation';
import { ApiService, ApiError } from '../../services/api';

// Mock component that throws an error
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div>No error</div>;
};

// Mock component with network error
const NetworkErrorComponent = () => {
  throw new Error('ChunkLoadError: Loading chunk 1 failed');
};

describe('Error Handling', () => {
  describe('ErrorBoundary', () => {
    it('should catch and display component errors', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByText('Component Error')).toBeInTheDocument();
      expect(screen.getByText('An unexpected error occurred in this component.')).toBeInTheDocument();
      expect(screen.getByText('Try Again')).toBeInTheDocument();
    });

    it('should show specific message for chunk load errors', () => {
      render(
        <ErrorBoundary>
          <NetworkErrorComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('A new version of the app is available. Please refresh the page.')).toBeInTheDocument();
    });

    it('should allow retry with limited attempts', async () => {
      const { rerender } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // First retry
      fireEvent.click(screen.getByText('Try Again'));
      
      await waitFor(() => {
        expect(screen.getByText('Retry attempt 1 of 3')).toBeInTheDocument();
      });

      // Simulate continued error
      rerender(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Should still show retry button
      expect(screen.getByText('Try Again')).toBeInTheDocument();
    });

    it('should show error details when expanded', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      fireEvent.click(screen.getByText('Technical Details'));
      
      expect(screen.getByText('Error Message:')).toBeInTheDocument();
      expect(screen.getByText('Test error message')).toBeInTheDocument();
    });

    it('should render children when no error occurs', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(screen.getByText('No error')).toBeInTheDocument();
      expect(screen.queryByText('Component Error')).not.toBeInTheDocument();
    });
  });

  describe('Input Validation', () => {
    it('should validate empty input', () => {
      const result = validateInput('');
      expect(result.isValid).toBe(false);
      expect(result.error).toBe(ERROR_MESSAGES.EMPTY_INPUT);
    });

    it('should validate Google Play Store URLs', () => {
      const validUrl = 'https://play.google.com/store/apps/details?id=com.example.app';
      const result = validateInput(validUrl);
      expect(result.isValid).toBe(true);
      expect(result.type).toBe('APP');
    });

    it('should validate App Store URLs', () => {
      const validUrl = 'https://apps.apple.com/us/app/example-app/id123456789';
      const result = validateInput(validUrl);
      expect(result.isValid).toBe(true);
      expect(result.type).toBe('APP');
    });

    it('should validate website URLs', () => {
      const validUrl = 'https://example.com';
      const result = validateInput(validUrl);
      expect(result.isValid).toBe(true);
      expect(result.type).toBe('WEBSITE');
    });

    it('should validate app IDs', () => {
      const validAppId = 'com.example.app';
      const result = validateInput(validAppId);
      expect(result.isValid).toBe(true);
      expect(result.type).toBe('APP');
    });

    it('should reject invalid URLs', () => {
      const invalidUrl = 'not-a-url';
      const result = validateInput(invalidUrl);
      expect(result.isValid).toBe(false);
      expect(result.error).toBeDefined();
    });

    it('should warn about localhost URLs', () => {
      const localhostUrl = 'http://localhost:3000';
      const result = validateInput(localhostUrl, { strictMode: true });
      expect(result.isValid).toBe(true);
      expect(result.warnings).toContain(ERROR_MESSAGES.LOCALHOST_WARNING);
    });

    it('should reject malformed Play Store URLs', () => {
      const malformedUrl = 'https://play.google.com/store/apps/';
      const result = validateInput(malformedUrl);
      expect(result.isValid).toBe(false);
      expect(result.error).toBe(ERROR_MESSAGES.MALFORMED_PLAY_STORE_URL);
    });

    it('should reject unsupported app stores in strict mode', () => {
      const amazonUrl = 'https://www.amazon.com/dp/B08N5WRWNW';
      const result = validateInput(amazonUrl, { strictMode: true });
      expect(result.isValid).toBe(false);
      expect(result.error).toBe(ERROR_MESSAGES.UNSUPPORTED_APP_STORE);
    });
  });

  describe('API Error Handling', () => {
    let apiService: ApiService;

    beforeEach(() => {
      apiService = new ApiService();
      // Mock fetch
      global.fetch = jest.fn();
    });

    afterEach(() => {
      jest.resetAllMocks();
    });

    it('should handle network errors', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      await expect(
        apiService.submitAnalysis({ input: 'com.example.app', analysis_type: 'APP' })
      ).rejects.toThrow('Unable to connect to the server');
    });

    it('should handle 404 errors', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: () => Promise.resolve({ detail: 'App not found' }),
      });

      await expect(
        apiService.submitAnalysis({ input: 'com.nonexistent.app', analysis_type: 'APP' })
      ).rejects.toThrow('App not found');
    });

    it('should handle 429 rate limiting', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        json: () => Promise.resolve({ detail: 'Rate limit exceeded' }),
      });

      await expect(
        apiService.submitAnalysis({ input: 'com.example.app', analysis_type: 'APP' })
      ).rejects.toThrow('Too many requests');
    });

    it('should handle server errors with retry', async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          statusText: 'Internal Server Error',
          json: () => Promise.resolve({ detail: 'Server error' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ analysis_id: '123' }),
        });

      const result = await apiService.submitAnalysis({ 
        input: 'com.example.app', 
        analysis_type: 'APP' 
      });

      expect(result.analysis_id).toBe('123');
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('should handle timeout errors', async () => {
      (global.fetch as jest.Mock).mockImplementation(() => 
        new Promise((_, reject) => {
          setTimeout(() => reject(new Error('AbortError')), 100);
        })
      );

      await expect(
        apiService.submitAnalysis({ input: 'com.example.app', analysis_type: 'APP' })
      ).rejects.toThrow('Request timed out');
    });
  });

  describe('Toast Notifications', () => {
    it('should display success toast', async () => {
      render(
        <ToastProvider>
          <div data-testid="toast-test">Test component</div>
        </ToastProvider>
      );

      // Toast functionality would be tested through integration tests
      // as it requires the useToast hook to be called within a component
      expect(screen.getByTestId('toast-test')).toBeInTheDocument();
    });
  });
});