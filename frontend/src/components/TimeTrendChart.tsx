'use client';

import { useEffect, useMemo } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js';
import 'chartjs-adapter-date-fns';
import { ComplaintCluster } from '@/types';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

interface TimeTrendChartProps {
  clusters: ComplaintCluster[];
  selectedClusterIds?: string[];
}

export default function TimeTrendChart({ clusters, selectedClusterIds }: TimeTrendChartProps) {
  // Generate mock time series data based on recency scores
  // In a real implementation, this would come from the backend with actual time-based data
  const timeSeriesData = useMemo(() => {
    const months: string[] = [];
    const currentDate = new Date();
    
    // Generate last 12 months
    for (let i = 11; i >= 0; i--) {
      const date = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1);
      months.push(date.toISOString().slice(0, 7)); // YYYY-MM format
    }

    // Filter clusters to show (either selected ones or top 5)
    const clustersToShow = selectedClusterIds && selectedClusterIds.length > 0
      ? clusters.filter(c => selectedClusterIds.includes(c.id))
      : clusters.sort((a, b) => b.percentage - a.percentage).slice(0, 5);

    return {
      months,
      clusters: clustersToShow.map(cluster => ({
        ...cluster,
        data: months.map((month, index) => {
          // Generate synthetic trend data based on recency score
          const baseValue = cluster.percentage;
          const recencyFactor = cluster.recency_score / 100;
          const timeDecay = Math.exp(-index * 0.1); // Older months have lower values
          const randomVariation = 0.8 + Math.random() * 0.4; // ±20% variation
          
          return Math.max(0, baseValue * recencyFactor * timeDecay * randomVariation);
        })
      }))
    };
  }, [clusters, selectedClusterIds]);

  const colors = [
    'rgb(59, 130, 246)',   // blue
    'rgb(239, 68, 68)',    // red
    'rgb(34, 197, 94)',    // green
    'rgb(245, 158, 11)',   // yellow
    'rgb(168, 85, 247)',   // purple
    'rgb(236, 72, 153)',   // pink
    'rgb(14, 165, 233)',   // sky
    'rgb(99, 102, 241)',   // indigo
  ];

  const data = {
    labels: timeSeriesData.months,
    datasets: timeSeriesData.clusters.map((cluster, index) => ({
      label: cluster.name.length > 30 ? cluster.name.substring(0, 30) + '...' : cluster.name,
      data: cluster.data,
      borderColor: colors[index % colors.length],
      backgroundColor: colors[index % colors.length] + '20', // 20% opacity
      tension: 0.4,
      fill: false,
      pointRadius: 4,
      pointHoverRadius: 6,
    }))
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          padding: 20,
        }
      },
      title: {
        display: true,
        text: 'Complaint Trends Over Time',
        font: {
          size: 16,
          weight: 'bold' as const,
        },
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        callbacks: {
          label: (context: any) => {
            return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}% of reviews`;
          },
        },
      },
    },
    scales: {
      x: {
        type: 'category' as const,
        title: {
          display: true,
          text: 'Month',
        },
        ticks: {
          callback: (value: any, index: number) => {
            const date = new Date(timeSeriesData.months[index] + '-01');
            return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
          },
        },
      },
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
    },
    interaction: {
      mode: 'nearest' as const,
      axis: 'x' as const,
      intersect: false,
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
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Trend Data Available</h3>
          <p className="text-gray-500">
            Time trend chart will appear here once complaint data is available.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="h-80">
        <Line data={data} options={options} />
      </div>
      <div className="mt-4 text-sm text-gray-500">
        <p>
          Showing trends for {timeSeriesData.clusters.length} complaint categories over the last 12 months.
          {selectedClusterIds && selectedClusterIds.length > 0 
            ? ' Filtered to selected clusters.' 
            : ' Displaying top 5 clusters by frequency.'
          }
        </p>
      </div>
    </div>
  );
}