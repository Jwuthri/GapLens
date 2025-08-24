'use client';

import { Component, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, Bug, ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: any) => void;
  level?: 'page' | 'component' | 'section';
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: any;
  showDetails: boolean;
  retryCount: number;
}

export default class ErrorBoundary extends Component<Props, State> {
  private retryTimeoutId?: NodeJS.Timeout;

  constructor(props: Props) {
    super(props);
    this.state = { 
      hasError: false, 
      showDetails: false,
      retryCount: 0
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Error caught by boundary:', error, errorInfo);
    
    this.setState({ errorInfo });
    
    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log error to monitoring service (if available)
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'exception', {
        description: error.message,
        fatal: false,
      });
    }
  }

  componentWillUnmount() {
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId);
    }
  }

  handleRetry = () => {
    const newRetryCount = this.state.retryCount + 1;
    
    // Limit retry attempts
    if (newRetryCount > 3) {
      return;
    }

    this.setState({ 
      hasError: false, 
      error: undefined, 
      errorInfo: undefined,
      retryCount: newRetryCount
    });

    // Add a small delay to prevent immediate re-error
    this.retryTimeoutId = setTimeout(() => {
      this.forceUpdate();
    }, 100);
  };

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  toggleDetails = () => {
    this.setState(prev => ({ showDetails: !prev.showDetails }));
  };

  getErrorTitle = (): string => {
    const { level = 'component' } = this.props;
    
    switch (level) {
      case 'page':
        return 'Page Error';
      case 'section':
        return 'Section Error';
      default:
        return 'Component Error';
    }
  };

  getErrorMessage = (): string => {
    const { level = 'component' } = this.props;
    const { error } = this.state;
    
    // Check for specific error types
    if (error?.message.includes('ChunkLoadError') || error?.message.includes('Loading chunk')) {
      return 'A new version of the app is available. Please refresh the page.';
    }
    
    if (error?.message.includes('Network Error') || error?.message.includes('fetch')) {
      return 'Network connection issue. Please check your internet connection and try again.';
    }

    switch (level) {
      case 'page':
        return 'An error occurred while loading this page. This might be due to a temporary issue.';
      case 'section':
        return 'An error occurred in this section. Other parts of the page should still work.';
      default:
        return 'An unexpected error occurred in this component.';
    }
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { level = 'component' } = this.props;
      const { error, errorInfo, showDetails, retryCount } = this.state;
      const canRetry = retryCount < 3;

      return (
        <div className={`flex items-center justify-center p-6 ${
          level === 'page' ? 'min-h-[400px]' : 'min-h-[200px]'
        }`}>
          <div className="text-center space-y-4 max-w-lg mx-auto">
            <div className="text-red-500 mb-4">
              <AlertTriangle className={`mx-auto ${
                level === 'page' ? 'h-12 w-12' : 'h-8 w-8'
              }`} />
            </div>
            
            <h2 className={`font-semibold text-gray-900 ${
              level === 'page' ? 'text-xl' : 'text-lg'
            }`}>
              {this.getErrorTitle()}
            </h2>
            
            <p className="text-gray-600">
              {this.getErrorMessage()}
            </p>

            {retryCount > 0 && (
              <p className="text-sm text-yellow-600">
                Retry attempt {retryCount} of 3
              </p>
            )}

            {/* Action Buttons */}
            <div className="flex flex-wrap justify-center gap-3">
              {canRetry && (
                <button
                  onClick={this.handleRetry}
                  className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <RefreshCw className="h-4 w-4" />
                  <span>Try Again</span>
                </button>
              )}
              
              {level === 'page' && (
                <>
                  <button
                    onClick={this.handleReload}
                    className="inline-flex items-center space-x-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                  >
                    <RefreshCw className="h-4 w-4" />
                    <span>Reload Page</span>
                  </button>
                  
                  <button
                    onClick={this.handleGoHome}
                    className="inline-flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  >
                    <Home className="h-4 w-4" />
                    <span>Go Home</span>
                  </button>
                </>
              )}
            </div>

            {/* Error Details */}
            {(error || errorInfo) && (
              <div className="mt-6">
                <button
                  onClick={this.toggleDetails}
                  className="inline-flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
                >
                  <Bug className="h-4 w-4" />
                  <span>Technical Details</span>
                  {showDetails ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </button>

                {showDetails && (
                  <div className="mt-3 text-left bg-gray-50 border rounded-lg p-4 text-sm">
                    {error && (
                      <div className="mb-3">
                        <h4 className="font-medium text-gray-700 mb-1">Error Message:</h4>
                        <pre className="text-red-600 whitespace-pre-wrap break-words">
                          {error.message}
                        </pre>
                      </div>
                    )}
                    
                    {error?.stack && (
                      <div className="mb-3">
                        <h4 className="font-medium text-gray-700 mb-1">Stack Trace:</h4>
                        <pre className="text-gray-600 whitespace-pre-wrap break-words text-xs max-h-32 overflow-y-auto">
                          {error.stack}
                        </pre>
                      </div>
                    )}
                    
                    {errorInfo?.componentStack && (
                      <div>
                        <h4 className="font-medium text-gray-700 mb-1">Component Stack:</h4>
                        <pre className="text-gray-600 whitespace-pre-wrap break-words text-xs max-h-32 overflow-y-auto">
                          {errorInfo.componentStack}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Help Text */}
            <div className="mt-6 text-xs text-gray-500">
              <p>If this problem persists, please try refreshing the page or contact support.</p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}