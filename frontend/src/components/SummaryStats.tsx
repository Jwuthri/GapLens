'use client';

import { TrendingDown, MessageSquare, AlertTriangle, Target } from 'lucide-react';
import { Analysis } from '@/types';
import { formatPercentage } from '@/utils/validation';

interface SummaryStatsProps {
  analysis: Analysis;
}

export default function SummaryStats({ analysis }: SummaryStatsProps) {
  const negativePercentage = analysis.total_reviews > 0 
    ? (analysis.negative_reviews / analysis.total_reviews) * 100 
    : 0;

  const stats = [
    {
      label: 'Total Reviews',
      value: analysis.total_reviews.toLocaleString(),
      icon: MessageSquare,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      label: 'Negative Reviews',
      value: analysis.negative_reviews.toLocaleString(),
      icon: TrendingDown,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
    },
    {
      label: 'Negative Rate',
      value: formatPercentage(negativePercentage),
      icon: AlertTriangle,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
    {
      label: 'Complaint Clusters',
      value: analysis.clusters.length.toString(),
      icon: Target,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {stats.map((stat, index) => {
        const Icon = stat.icon;
        return (
          <div key={index} className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{stat.label}</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
              </div>
              <div className={`${stat.bgColor} p-3 rounded-lg`}>
                <Icon className={`h-6 w-6 ${stat.color}`} />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}