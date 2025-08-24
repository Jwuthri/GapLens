'use client';

import { useState } from 'react';
import { Download, BarChart3, List, ArrowLeft, TrendingUp } from 'lucide-react';
import { Analysis, ComplaintCluster } from '@/types';
import SummaryStats from './SummaryStats';
import ClustersList from './ClustersList';
import ClustersChart from './ClustersChart';
import TimeTrendChart from './TimeTrendChart';
import ClusterDetailModal from './ClusterDetailModal';
import ExportModal from './ExportModal';
import ErrorBoundary from './ErrorBoundary';

interface ResultsDashboardProps {
  analysis: Analysis;
  onBack: () => void;
}

export default function ResultsDashboard({ analysis, onBack }: ResultsDashboardProps) {
  const [selectedCluster, setSelectedCluster] = useState<ComplaintCluster | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'chart' | 'trends'>('list');
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const [selectedClusterIds, setSelectedClusterIds] = useState<string[]>([]);

  const handleClusterSelection = (clusterId: string, selected: boolean) => {
    if (selected) {
      setSelectedClusterIds(prev => [...prev, clusterId]);
    } else {
      setSelectedClusterIds(prev => prev.filter(id => id !== clusterId));
    }
  };

  const getAnalysisTitle = () => {
    if (analysis.analysis_type === 'APP') {
      return `App Analysis: ${analysis.app_id}`;
    } else {
      return `Website Analysis: ${analysis.website_url}`;
    }
  };

  const getAnalysisSubtitle = () => {
    if (analysis.analysis_type === 'APP') {
      return `${analysis.platform} • Analyzed ${analysis.total_reviews.toLocaleString()} reviews`;
    } else {
      return `Website Reviews • Analyzed ${analysis.total_reviews.toLocaleString()} reviews from multiple platforms`;
    }
  };

  return (
    <ErrorBoundary>
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="h-5 w-5 text-gray-600" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {getAnalysisTitle()}
              </h1>
              <p className="text-gray-600">
                {getAnalysisSubtitle()}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* View Mode Toggle */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setViewMode('list')}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  viewMode === 'list'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <List className="h-4 w-4" />
              </button>
              <button
                onClick={() => setViewMode('chart')}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  viewMode === 'chart'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <BarChart3 className="h-4 w-4" />
              </button>
              <button
                onClick={() => setViewMode('trends')}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  viewMode === 'trends'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <TrendingUp className="h-4 w-4" />
              </button>
            </div>

            {/* Export Button */}
            <button
              onClick={() => setIsExportModalOpen(true)}
              className="flex items-center space-x-2 bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <Download className="h-4 w-4" />
              <span>Export</span>
            </button>
          </div>
        </div>

        {/* Summary Statistics */}
        <SummaryStats analysis={analysis} />

        {/* Clusters Visualization */}
        <div className="space-y-6">
          {viewMode === 'list' ? (
            <ClustersList 
              clusters={analysis.clusters} 
              onClusterClick={setSelectedCluster}
            />
          ) : viewMode === 'chart' ? (
            <ClustersChart 
              clusters={analysis.clusters}
              onClusterClick={setSelectedCluster}
            />
          ) : (
            <TimeTrendChart 
              clusters={analysis.clusters}
              selectedClusterIds={selectedClusterIds}
            />
          )}
        </div>

        {/* Cluster Selection for Trends */}
        {viewMode === 'trends' && analysis.clusters.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Filter Trend Lines</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {analysis.clusters.slice(0, 8).map((cluster) => (
                <label key={cluster.id} className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedClusterIds.includes(cluster.id)}
                    onChange={(e) => handleClusterSelection(cluster.id, e.target.checked)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700 truncate">
                    {cluster.name} ({cluster.percentage.toFixed(1)}%)
                  </span>
                </label>
              ))}
            </div>
            {selectedClusterIds.length === 0 && (
              <p className="text-sm text-gray-500 mt-2">
                Select clusters to filter the trend chart, or leave empty to show top 5 clusters.
              </p>
            )}
          </div>
        )}

        {/* Additional Insights */}
        {analysis.clusters.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-blue-900 mb-2">Key Insights</h3>
            <div className="space-y-2 text-blue-800">
              <p>
                • The top complaint affects {analysis.clusters[0]?.percentage.toFixed(1)}% of negative reviews
              </p>
              <p>
                • {analysis.clusters.filter(c => c.recency_score > 70).length} clusters show recent activity (last 3 months)
              </p>
              <p>
                • Focus on the top {Math.min(3, analysis.clusters.length)} clusters to address {
                  analysis.clusters.slice(0, 3).reduce((sum, c) => sum + c.percentage, 0).toFixed(1)
                }% of user complaints
              </p>
            </div>
          </div>
        )}

        {/* Cluster Detail Modal */}
        <ClusterDetailModal 
          cluster={selectedCluster}
          onClose={() => setSelectedCluster(null)}
        />

        {/* Export Modal */}
        <ExportModal
          analysis={analysis}
          isOpen={isExportModalOpen}
          onClose={() => setIsExportModalOpen(false)}
        />
      </div>
    </ErrorBoundary>
  );
}