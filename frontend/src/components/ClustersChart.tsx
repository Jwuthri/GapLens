'use client';

import { useEffect, useRef } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { ComplaintCluster } from '@/types';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface ClustersChartProps {
  clusters: ComplaintCluster[];
  onClusterClick?: (cluster: ComplaintCluster) => void;
}

export default function ClustersChart({ clusters, onClusterClick }: ClustersChartProps) {
  const chartRef = useRef<ChartJS<'bar'>>(null);

  // Sort clusters by percentage and take top 10
  const topClusters = clusters
    .sort((a, b) => b.percentage - a.percentage)
    .slice(0, 10);

  const data = {
    labels: topClusters.map(cluster => 
      cluster.name.length > 20 
        ? cluster.name.substring(0, 20) + '...' 
        : cluster.name
    ),
    datasets: [
      {
        label: 'Percentage of Reviews',
        data: topClusters.map(cluster => cluster.percentage),
        backgroundColor: topClusters.map((_, index) => {
          const opacity = 0.8 - (index * 0.05);
          return `rgba(59, 130, 246, ${Math.max(opacity, 0.3)})`;
        }),
        borderColor: topClusters.map(() => 'rgba(59, 130, 246, 1)'),
        borderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: true,
        text: 'Top Complaint Clusters by Frequency',
        font: {
          size: 16,
          weight: 'bold' as const,
        },
      },
      tooltip: {
        callbacks: {
          label: (context: any) => {
            const cluster = topClusters[context.dataIndex];
            return [
              `${cluster.percentage.toFixed(1)}% of reviews`,
              `${cluster.review_count} reviews affected`,
              `Recency: ${cluster.recency_score.toFixed(0)}%`,
            ];
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Percentage of Reviews (%)',
        },
        ticks: {
          callback: (value: any) => `${value}%`,
        },
      },
      x: {
        title: {
          display: true,
          text: 'Complaint Categories',
        },
        ticks: {
          maxRotation: 45,
          minRotation: 45,
        },
      },
    },
    onClick: (event: any, elements: any[]) => {
      if (elements.length > 0 && onClusterClick) {
        const index = elements[0].index;
        const cluster = topClusters[index];
        onClusterClick(cluster);
      }
    },
  };

  if (clusters.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8">
        <div className="text-center">
          <div className="text-gray-400 mb-4">
            <svg className="h-12 w-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Data to Display</h3>
          <p className="text-gray-500">
            Chart will appear here once complaint clusters are generated.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="h-96">
        <Bar ref={chartRef} data={data} options={options} />
      </div>
      {onClusterClick && (
        <p className="text-sm text-gray-500 mt-4 text-center">
          Click on bars to view detailed information about each cluster
        </p>
      )}
    </div>
  );
}