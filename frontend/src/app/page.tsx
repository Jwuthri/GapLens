'use client';

import { useEffect } from 'react';
import { AnalysisRequest } from '@/types';
import { ApiError } from '@/services/api';
import { useAnalysisState } from '@/hooks/useAnalysisState';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';
import AnalysisForm from '@/components/AnalysisForm';
import LoadingState from '@/components/LoadingState';
import ResultsDashboard from '@/components/ResultsDashboard';
import ErrorBoundary from '@/components/ErrorBoundary';
import ConnectionStatus from '@/components/ConnectionStatus';
import { ToastProvider, useToast } from '@/components/ToastContainer';
import { AlertCircle, RefreshCw, WifiOff } from 'lucide-react';

function HomeContent() {
  const [analysisState, analysisActions] = useAnalysisState();
  const [networkStatus, networkActions] = useNetworkStatus();
  const { showSuccess, showError, showWarning, showInfo } = useToast();

  // Monitor network status changes
  useEffect(() => {
    if (networkStatus.isOnline && networkStatus.isConnected) {
      if (!analysisState.isOnline) {
        showSuccess('Connection restored', 'You are back online');
      }
    } else if (!networkStatus.isOnline) {
      showWarning('Connection lost', 'Please check your internet connection');
    } else if (!networkStatus.isConnected) {
      showError('Server unreachable', 'Cannot connect to the analysis server');
    }
  }, [networkStatus.isOnline, networkStatus.isConnected, analysisState.isOnline, showSuccess, showWarning, showError]);

  // Handle analysis status changes
  useEffect(() => {
    if (analysisState.currentAnalysis?.status === 'COMPLETED') {
      showSuccess(
        'Analysis completed!', 
        `Found ${analysisState.currentAnalysis.clusters.length} complaint categories from ${analysisState.currentAnalysis.total_reviews} reviews`
      );
    } else if (analysisState.currentAnalysis?.status === 'FAILED') {
      showError('Analysis failed', 'The analysis could not be completed. Please try again.');
    }
  }, [analysisState.currentAnalysis?.status, analysisState.currentAnalysis?.clusters.length, analysisState.currentAnalysis?.total_reviews, showSuccess, showError]);

  const handleSubmitAnalysis = async (request: AnalysisRequest) => {
    if (!networkStatus.isOnline || !networkStatus.isConnected) {
      showError('No internet connection', 'Please check your connection and try again');
      return;
    }

    try {
      showInfo('Starting analysis...', 'This may take a few minutes depending on the number of reviews');
      
      await analysisActions.submitAnalysis(request);
      showSuccess('Analysis started', 'We are now collecting and analyzing reviews');
    } catch (error: any) {
      const errorMessage = error instanceof ApiError ? error.message : 'Failed to start analysis';
      
      showError(
        'Analysis failed to start', 
        errorMessage,
        {
          action: {
            label: 'Try Again',
            onClick: () => handleSubmitAnalysis(request)
          }
        }
      );
    }
  };

  const handleBack = () => {
    analysisActions.resetAnalysis();
  };

  const handleRetry = async () => {
    if (!networkStatus.isOnline || !networkStatus.isConnected) {
      showError('No internet connection', 'Please check your connection and try again');
      return;
    }

    if (analysisState.retryCount >= 3) {
      showError('Too many retry attempts', 'Please wait a moment before trying again');
      return;
    }

    try {
      showInfo(`Retry attempt ${analysisState.retryCount + 1}`, 'Attempting to restart the analysis');
      await analysisActions.retryAnalysis();
    } catch (error) {
      // Error handling is done in the action
    }
  };

  const handleErrorBoundaryError = () => {
    showError(
      'Application error',
      'An unexpected error occurred. The page will be reloaded.',
      { duration: 0 }
    );
  };

  return (
    <ErrorBoundary level="page" onError={handleErrorBoundaryError}>
      <main className="min-h-screen bg-hero-pattern relative overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-transparent to-blue-900/20"></div>
        <div className="absolute top-0 left-1/4 w-72 h-72 bg-purple-600/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl animate-pulse-slow delay-1000"></div>
        {/* Connection Status Bar */}
        {(!networkStatus.isOnline || !networkStatus.isConnected) && (
          <div className="bg-gradient-to-r from-red-600 to-red-700 text-white px-4 py-3 text-center text-sm border-b border-red-500/50 relative z-20">
            <div className="flex items-center justify-center space-x-2">
              <WifiOff className="h-4 w-4" />
              <span>
                {!networkStatus.isOnline 
                  ? 'You are currently offline. Please check your internet connection.'
                  : 'Cannot connect to the server. Please try again later.'
                }
              </span>
              {networkStatus.latency && (
                <span className="text-xs opacity-75">
                  (Last check: {networkStatus.latency}ms)
                </span>
              )}
            </div>
          </div>
        )}

        <div className="container mx-auto px-4 py-8">
          {/* Header */}
          <div className="text-center mb-16 relative">
            <div className="absolute inset-0 flex items-center justify-center opacity-10">
              <div className="w-96 h-96 bg-gradient-to-r from-purple-600 to-blue-600 rounded-full blur-3xl animate-pulse-slow"></div>
            </div>
            <div className="relative z-10">
              <div className="inline-block mb-6">
                <span className="text-sm font-semibold tracking-wider text-gray-400 uppercase">
                  R E V I E W  &nbsp; G A P  &nbsp; A N A L Y Z E R
                </span>
              </div>
              <h1 className="text-6xl font-bold mb-6 animate-float">
                <span className="gradient-text">Discover Hidden</span>
                <br />
                <span className="text-white">Product Opportunities</span>
              </h1>
              <p className="text-xl text-gray-300 max-w-3xl mx-auto leading-relaxed">
                Type a prompt, get a playable game instantly. No coding required.
                <br />
                <span className="text-gray-400 text-lg">Analyze app store reviews and website feedback using AI</span>
              </p>
            </div>
          </div>

          {/* Connection Status */}
          <div className="max-w-2xl mx-auto mb-8">
            <ConnectionStatus />
          </div>

          {/* Main Content */}
          {analysisState.error && (
            <div className="max-w-2xl mx-auto mb-8 relative z-10">
              <div className="card-dark border-red-500/50 p-6">
                <div className="flex items-center space-x-3">
                  <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
                  <div className="flex-1">
                    <h3 className="text-sm font-semibold text-red-300">Analysis Failed</h3>
                    <p className="text-sm text-red-200 mt-1">{analysisState.error}</p>
                    {analysisState.retryCount > 0 && (
                      <p className="text-xs text-red-400 mt-1">
                        Retry attempt {analysisState.retryCount} of 3
                      </p>
                    )}
                  </div>
                  <button
                    onClick={handleRetry}
                    disabled={!networkStatus.isOnline || !networkStatus.isConnected || analysisState.retryCount >= 3}
                    className="flex items-center space-x-1 px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300"
                  >
                    <RefreshCw className="h-4 w-4" />
                    <span>Retry</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          <ErrorBoundary level="section">
            {!analysisState.currentAnalysis && !analysisState.isLoading && (
              <AnalysisForm
                onSubmit={handleSubmitAnalysis}
                isLoading={analysisState.isSubmitting}
              />
            )}
          </ErrorBoundary>

          <ErrorBoundary level="section">
            {analysisState.isLoading && analysisState.currentAnalysis && analysisState.currentAnalysis.status !== 'COMPLETED' && (
              <div className="max-w-2xl mx-auto">
                <LoadingState
                  status={analysisState.currentAnalysis.status}
                  progress={analysisState.progress}
                  message={analysisState.statusMessage}
                  isConnected={networkStatus.isOnline && networkStatus.isConnected}
                  retryCount={analysisState.retryCount}
                  onRetry={handleRetry}
                  onCancel={handleBack}
                />
              </div>
            )}
          </ErrorBoundary>

          <ErrorBoundary level="section">
            {analysisState.currentAnalysis && analysisState.currentAnalysis.status === 'COMPLETED' && (
              <ResultsDashboard
                analysis={analysisState.currentAnalysis}
                onBack={handleBack}
              />
            )}
          </ErrorBoundary>

          {analysisState.currentAnalysis && analysisState.currentAnalysis.status === 'FAILED' && (
            <div className="max-w-2xl mx-auto text-center py-12 relative z-10">
              <div className="card-dark p-8">
                <div className="text-red-400 mb-6">
                  <AlertCircle className="h-16 w-16 mx-auto" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">Analysis Failed</h3>
                <p className="text-gray-300 mb-8 leading-relaxed">
                  We encountered an error while processing your request. This could be due to insufficient reviews, 
                  network issues, or temporary server problems.
                </p>
                <div className="space-x-4">
                  <button
                    onClick={handleRetry}
                    disabled={!networkStatus.isOnline || !networkStatus.isConnected || analysisState.retryCount >= 3}
                    className="btn-primary"
                  >
                    Try Again
                  </button>
                  <button
                    onClick={handleBack}
                    className="btn-secondary"
                  >
                    Start Over
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="border-t border-gray-700/50 bg-gray-900/50 backdrop-blur-sm mt-16 relative z-10">
          <div className="container mx-auto px-4 py-8">
            <div className="text-center text-gray-400">
              <p className="mb-2 text-gray-300">
                Review Gap Analyzer helps you discover product opportunities from user feedback
              </p>
              <p className="text-sm text-gray-500">
                Supports Google Play Store, App Store, and website review analysis
              </p>
              <div className="mt-4 text-xs text-gray-600">
                © 2024 Review Gap Analyzer. All rights reserved.
              </div>
            </div>
          </div>
        </footer>
      </main>
    </ErrorBoundary>
  );
}

export default function Home() {
  return (
    <ToastProvider>
      <HomeContent />
    </ToastProvider>
  );
}