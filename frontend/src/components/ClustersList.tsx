'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Users, TrendingUp, Quote } from 'lucide-react';
import { ComplaintCluster } from '@/types';
import { formatPercentage, truncateText } from '@/utils/validation';

interface ClustersListProps {
  clusters: ComplaintCluster[];
  onClusterClick: (cluster: ComplaintCluster) => void;
}

export default function ClustersList({ clusters, onClusterClick }: ClustersListProps) {
  const [expandedClusters, setExpandedClusters] = useState<Set<string>>(new Set());

  const toggleCluster = (clusterId: string) => {
    const newExpanded = new Set(expandedClusters);
    if (newExpanded.has(clusterId)) {
      newExpanded.delete(clusterId);
    } else {
      newExpanded.add(clusterId);
    }
    setExpandedClusters(newExpanded);
  };

  const getRecencyColor = (score: number) => {
    if (score >= 80) return 'text-red-600 bg-red-50';
    if (score >= 60) return 'text-orange-600 bg-orange-50';
    if (score >= 40) return 'text-yellow-600 bg-yellow-50';
    return 'text-green-600 bg-green-50';
  };

  if (clusters.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 mb-4">
          <Users className="h-12 w-12 mx-auto" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Complaint Clusters Found</h3>
        <p className="text-gray-500">
          Not enough negative reviews were found to generate meaningful clusters.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-900">Complaint Clusters</h2>
        <p className="text-sm text-gray-500">
          Ranked by frequency and recency
        </p>
      </div>

      {clusters.map((cluster, index) => {
        const isExpanded = expandedClusters.has(cluster.id);
        
        return (
          <div key={cluster.id} className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div 
              className="p-6 cursor-pointer hover:bg-gray-50 transition-colors"
              onClick={() => toggleCluster(cluster.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <span className="text-sm font-medium text-gray-500">#{index + 1}</span>
                    <h3 className="text-lg font-semibold text-gray-900">{cluster.name}</h3>
                    {isExpanded ? (
                      <ChevronDown className="h-5 w-5 text-gray-400" />
                    ) : (
                      <ChevronRight className="h-5 w-5 text-gray-400" />
                    )}
                  </div>
                  
                  <p className="text-gray-600 mb-3">{cluster.description}</p>
                  
                  <div className="flex items-center space-x-6">
                    <div className="flex items-center space-x-2">
                      <Users className="h-4 w-4 text-gray-400" />
                      <span className="text-sm text-gray-600">
                        {cluster.review_count} reviews ({formatPercentage(cluster.percentage)})
                      </span>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <TrendingUp className="h-4 w-4 text-gray-400" />
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${getRecencyColor(cluster.recency_score)}`}>
                        {cluster.recency_score.toFixed(0)}% recent
                      </span>
                    </div>
                  </div>
                </div>
                
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onClusterClick(cluster);
                  }}
                  className="ml-4 px-3 py-1 text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  View Details
                </button>
              </div>
            </div>

            {isExpanded && (
              <div className="border-t border-gray-200 bg-gray-50 p-6">
                <div className="space-y-4">
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 mb-2">Keywords</h4>
                    <div className="flex flex-wrap gap-2">
                      {cluster.keywords.map((keyword, idx) => (
                        <span 
                          key={idx}
                          className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                        >
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 mb-2">Sample Reviews</h4>
                    <div className="space-y-2">
                      {cluster.sample_reviews.slice(0, 3).map((review, idx) => (
                        <div key={idx} className="flex items-start space-x-2">
                          <Quote className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                          <p className="text-sm text-gray-600 italic">
                            "{truncateText(review, 150)}"
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}