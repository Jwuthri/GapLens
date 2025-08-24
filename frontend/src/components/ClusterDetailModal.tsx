'use client';

import { X, Users, TrendingUp, Quote, Tag, Download } from 'lucide-react';
import { ComplaintCluster } from '@/types';
import { formatPercentage } from '@/utils/validation';

interface ClusterDetailModalProps {
  cluster: ComplaintCluster | null;
  onClose: () => void;
}

export default function ClusterDetailModal({ cluster, onClose }: ClusterDetailModalProps) {
  if (!cluster) return null;

  const getRecencyColor = (score: number) => {
    if (score >= 80) return 'text-red-600 bg-red-50 border-red-200';
    if (score >= 60) return 'text-orange-600 bg-orange-50 border-orange-200';
    if (score >= 40) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-green-600 bg-green-50 border-green-200';
  };

  const handleExport = () => {
    const data = {
      cluster_name: cluster.name,
      description: cluster.description,
      review_count: cluster.review_count,
      percentage: cluster.percentage,
      recency_score: cluster.recency_score,
      keywords: cluster.keywords,
      sample_reviews: cluster.sample_reviews,
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cluster-${cluster.name.toLowerCase().replace(/\s+/g, '-')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex-1">
            <h2 className="text-xl font-bold text-gray-900">{cluster.name}</h2>
            <p className="text-gray-600 mt-1">{cluster.description}</p>
          </div>
          <button
            onClick={onClose}
            className="ml-4 p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          {/* Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center space-x-2">
                <Users className="h-5 w-5 text-blue-600" />
                <span className="text-sm font-medium text-blue-900">Affected Reviews</span>
              </div>
              <p className="text-2xl font-bold text-blue-900 mt-1">
                {cluster.review_count}
              </p>
              <p className="text-sm text-blue-700">
                {formatPercentage(cluster.percentage)} of negative reviews
              </p>
            </div>

            <div className={`border rounded-lg p-4 ${getRecencyColor(cluster.recency_score)}`}>
              <div className="flex items-center space-x-2">
                <TrendingUp className="h-5 w-5" />
                <span className="text-sm font-medium">Recency Score</span>
              </div>
              <p className="text-2xl font-bold mt-1">
                {cluster.recency_score.toFixed(0)}%
              </p>
              <p className="text-sm">
                {cluster.recency_score >= 70 ? 'Very recent' : 
                 cluster.recency_score >= 50 ? 'Recent' : 
                 cluster.recency_score >= 30 ? 'Moderate' : 'Older'}
              </p>
            </div>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <div className="flex items-center space-x-2">
                <Tag className="h-5 w-5 text-gray-600" />
                <span className="text-sm font-medium text-gray-900">Keywords</span>
              </div>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {cluster.keywords.length}
              </p>
              <p className="text-sm text-gray-600">
                Key terms identified
              </p>
            </div>
          </div>

          {/* Keywords */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Keywords</h3>
            <div className="flex flex-wrap gap-2">
              {cluster.keywords.map((keyword, idx) => (
                <span 
                  key={idx}
                  className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full font-medium"
                >
                  {keyword}
                </span>
              ))}
            </div>
          </div>

          {/* Sample Reviews */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-gray-900">Sample Reviews</h3>
              <span className="text-sm text-gray-500">
                {cluster.sample_reviews.length} examples
              </span>
            </div>
            <div className="space-y-4">
              {cluster.sample_reviews.map((review, idx) => (
                <div key={idx} className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <Quote className="h-5 w-5 text-gray-400 mt-0.5 flex-shrink-0" />
                    <p className="text-gray-700 italic leading-relaxed">
                      "{review}"
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
          <p className="text-sm text-gray-500">
            This cluster represents {formatPercentage(cluster.percentage)} of all negative reviews
          </p>
          <div className="flex space-x-3">
            <button
              onClick={handleExport}
              className="flex items-center space-x-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Download className="h-4 w-4" />
              <span>Export</span>
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}