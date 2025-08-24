import { Analysis, AnalysisRequest } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(
    public status: number, 
    message: string, 
    public code?: string,
    public retryable: boolean = false
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// User-friendly error messages for common scenarios
export const API_ERROR_MESSAGES = {
  NETWORK_ERROR: 'Unable to connect to the server. Please check your internet connection.',
  APP_NOT_FOUND: 'App not found. Please verify the URL or app ID is correct.',
  INVALID_INPUT: 'The provided input is not valid. Please check your URL or app ID.',
  RATE_LIMITED: 'Too many requests. Please wait a moment before trying again.',
  SERVER_ERROR: 'Server is experiencing issues. Please try again later.',
  TIMEOUT: 'Request timed out. Please try again.',
  INSUFFICIENT_REVIEWS: 'Not enough reviews found for meaningful analysis.',
  ANALYSIS_FAILED: 'Analysis failed to complete. Please try again.',
  EXPORT_FAILED: 'Failed to export results. Please try again.',
  UNKNOWN_ERROR: 'An unexpected error occurred. Please try again.',
} as const;

interface RetryOptions {
  maxRetries?: number;
  baseDelay?: number;
  maxDelay?: number;
  retryCondition?: (error: ApiError) => boolean;
}

export class ApiService {
  private defaultRetryOptions: RetryOptions = {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 10000,
    retryCondition: (error) => error.retryable || error.status >= 500 || error.status === 429,
  };

  private requestQueue: Map<string, Promise<any>> = new Map();
  private healthCheckInterval: NodeJS.Timeout | null = null;
  private isHealthy: boolean = true;

  private async sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private getRetryDelay(attempt: number, baseDelay: number, maxDelay: number): number {
    const exponentialDelay = baseDelay * Math.pow(2, attempt);
    const jitter = Math.random() * 0.1 * exponentialDelay;
    return Math.min(exponentialDelay + jitter, maxDelay);
  }

  private getUserFriendlyErrorMessage(error: ApiError): string {
    switch (error.status) {
      case 0:
        return API_ERROR_MESSAGES.NETWORK_ERROR;
      case 400:
        if (error.message.toLowerCase().includes('not found')) {
          return API_ERROR_MESSAGES.APP_NOT_FOUND;
        }
        if (error.message.toLowerCase().includes('invalid')) {
          return API_ERROR_MESSAGES.INVALID_INPUT;
        }
        return error.message;
      case 404:
        return API_ERROR_MESSAGES.APP_NOT_FOUND;
      case 422:
        return API_ERROR_MESSAGES.INVALID_INPUT;
      case 429:
        return API_ERROR_MESSAGES.RATE_LIMITED;
      case 500:
      case 502:
      case 503:
      case 504:
        return API_ERROR_MESSAGES.SERVER_ERROR;
      default:
        return error.message || API_ERROR_MESSAGES.UNKNOWN_ERROR;
    }
  }

  private async request<T>(
    endpoint: string, 
    options?: RequestInit, 
    retryOptions?: RetryOptions
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const finalRetryOptions = { ...this.defaultRetryOptions, ...retryOptions };
    
    let lastError: ApiError;

    for (let attempt = 0; attempt <= finalRetryOptions.maxRetries!; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

        const response = await fetch(url, {
          headers: {
            'Content-Type': 'application/json',
            ...options?.headers,
          },
          signal: controller.signal,
          ...options,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const isRetryable = response.status >= 500 || response.status === 429;
          
          throw new ApiError(
            response.status,
            errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`,
            errorData.code,
            isRetryable
          );
        }

        return await response.json();
      } catch (error) {
        if (error instanceof ApiError) {
          lastError = error;
        } else if (error instanceof Error && error.name === 'AbortError') {
          lastError = new ApiError(0, API_ERROR_MESSAGES.TIMEOUT, 'TIMEOUT', true);
        } else {
          lastError = new ApiError(0, API_ERROR_MESSAGES.NETWORK_ERROR, 'NETWORK_ERROR', true);
        }

        // Check if we should retry
        if (
          attempt < finalRetryOptions.maxRetries! &&
          finalRetryOptions.retryCondition!(lastError)
        ) {
          const delay = this.getRetryDelay(
            attempt, 
            finalRetryOptions.baseDelay!, 
            finalRetryOptions.maxDelay!
          );
          await this.sleep(delay);
          continue;
        }

        // Enhance error message for user display
        lastError.message = this.getUserFriendlyErrorMessage(lastError);
        throw lastError;
      }
    }

    throw lastError!;
  }

  async submitAnalysis(request: AnalysisRequest): Promise<{ analysis_id: string }> {
    // Transform frontend request to backend format
    const backendRequest = request.analysis_type === 'APP' 
      ? { app_url_or_id: request.input }
      : { website_url: request.input };

    return this.request('/api/v1/analysis', {
      method: 'POST',
      body: JSON.stringify(backendRequest),
    });
  }

  async getAnalysis(analysisId: string): Promise<Analysis> {
    return this.request(`/api/v1/analysis/${analysisId}`, undefined, {
      maxRetries: 2, // Fewer retries for data fetching
    });
  }

  async getAnalysisStatus(analysisId: string): Promise<{ status: string; progress?: number }> {
    return this.request(`/api/v1/analysis/${analysisId}/status`, undefined, {
      maxRetries: 1, // Minimal retries for status checks
      baseDelay: 500,
    });
  }

  async exportAnalysis(analysisId: string, format: 'csv' | 'json'): Promise<Blob> {
    const url = `${API_BASE_URL}/api/v1/analysis/${analysisId}/export?format=${format}`;
    
    try {
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new ApiError(response.status, API_ERROR_MESSAGES.EXPORT_FAILED);
      }
      
      return response.blob();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(0, API_ERROR_MESSAGES.EXPORT_FAILED);
    }
  }

  // Health check method
  async healthCheck(): Promise<boolean> {
    try {
      await this.request('/health', undefined, { maxRetries: 1 });
      this.isHealthy = true;
      return true;
    } catch {
      this.isHealthy = false;
      return false;
    }
  }

  // Start periodic health checks
  startHealthChecking(interval: number = 30000): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }

    this.healthCheckInterval = setInterval(async () => {
      await this.healthCheck();
    }, interval);
  }

  // Stop health checks
  stopHealthChecking(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
  }

  // Get current health status
  getHealthStatus(): boolean {
    return this.isHealthy;
  }

  // Request deduplication for identical requests
  private getRequestKey(endpoint: string, options?: RequestInit): string {
    return `${options?.method || 'GET'}:${endpoint}:${JSON.stringify(options?.body || '')}`;
  }

  private async requestWithDeduplication<T>(
    endpoint: string,
    options?: RequestInit,
    retryOptions?: RetryOptions
  ): Promise<T> {
    const requestKey = this.getRequestKey(endpoint, options);
    
    // Return existing promise if same request is in flight
    if (this.requestQueue.has(requestKey)) {
      return this.requestQueue.get(requestKey);
    }

    const requestPromise = this.request<T>(endpoint, options, retryOptions);
    
    // Store the promise
    this.requestQueue.set(requestKey, requestPromise);
    
    // Clean up after request completes
    requestPromise.finally(() => {
      this.requestQueue.delete(requestKey);
    });

    return requestPromise;
  }

  // Enhanced analysis submission with progress callbacks
  async submitAnalysisWithProgress(
    request: AnalysisRequest,
    onProgress?: (progress: number, message: string) => void
  ): Promise<{ analysis_id: string }> {
    onProgress?.(0, 'Validating request...');
    
    try {
      onProgress?.(10, 'Submitting analysis request...');
      const result = await this.requestWithDeduplication<{ analysis_id: string }>('/api/v1/analyze', {
        method: 'POST',
        body: JSON.stringify(request),
      });
      
      onProgress?.(20, 'Analysis request accepted...');
      return result;
    } catch (error) {
      onProgress?.(0, 'Failed to submit analysis');
      throw error;
    }
  }

  // Enhanced status polling with progress tracking
  async pollAnalysisStatus(
    analysisId: string,
    onProgress?: (progress: number, message: string) => void,
    onStatusChange?: (status: string) => void
  ): Promise<Analysis> {
    try {
      const analysis = await this.getAnalysis(analysisId);
      
      // Calculate progress based on status
      let progress = 0;
      let message = '';
      
      switch (analysis.status) {
        case 'PENDING':
          progress = 10;
          message = 'Analysis queued...';
          break;
        case 'PROCESSING':
          progress = 50;
          message = 'Processing reviews...';
          break;
        case 'COMPLETED':
          progress = 100;
          message = 'Analysis complete!';
          break;
        case 'FAILED':
          progress = 0;
          message = 'Analysis failed';
          break;
      }
      
      onProgress?.(progress, message);
      onStatusChange?.(analysis.status);
      
      return analysis;
    } catch (error) {
      onProgress?.(0, 'Failed to check status');
      throw error;
    }
  }

  // Batch export with progress tracking
  async exportAnalysisWithProgress(
    analysisId: string,
    format: 'csv' | 'json',
    onProgress?: (progress: number, message: string) => void
  ): Promise<Blob> {
    onProgress?.(0, 'Preparing export...');
    
    try {
      onProgress?.(25, 'Generating export file...');
      const blob = await this.exportAnalysis(analysisId, format);
      
      onProgress?.(100, 'Export ready for download');
      return blob;
    } catch (error) {
      onProgress?.(0, 'Export failed');
      throw error;
    }
  }

  // Connection test with detailed diagnostics
  async testConnection(): Promise<{
    isConnected: boolean;
    latency: number;
    error?: string;
  }> {
    const startTime = Date.now();
    
    try {
      await this.healthCheck();
      const latency = Date.now() - startTime;
      
      return {
        isConnected: true,
        latency,
      };
    } catch (error) {
      return {
        isConnected: false,
        latency: Date.now() - startTime,
        error: error instanceof ApiError ? error.message : 'Connection failed',
      };
    }
  }
}

export const apiService = new ApiService();