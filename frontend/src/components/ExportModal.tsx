'use client';

import { useState } from 'react';
import { X, Download, FileText, Database, CheckCircle, AlertCircle } from 'lucide-react';
import { Analysis } from '@/types';
import { ExportService, ExportProgress } from '@/services/exportService';
import { useToast } from '@/components/ToastContainer';

interface ExportModalProps {
  analysis: Analysis;
  isOpen: boolean;
  onClose: () => void;
}

export default function ExportModal({ analysis, isOpen, onClose }: ExportModalProps) {
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState<ExportProgress | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);
  
  const { showSuccess, showError, showInfo } = useToast();

  if (!isOpen) return null;

  const handleExport = async (format: 'csv' | 'json') => {
    setIsExporting(true);
    setExportError(null);
    setExportSuccess(null);
    setExportProgress(null);

    showInfo('Starting export...', `Preparing ${format.toUpperCase()} file for download`);

    try {
      const exportService = new ExportService((progress) => {
        setExportProgress(progress);
      });

      let blob: Blob;
      if (format === 'csv') {
        blob = await exportService.exportToCSV(analysis);
      } else {
        blob = await exportService.exportToJSON(analysis);
      }

      const filename = ExportService.generateFilename(analysis, format);
      await ExportService.downloadFile(blob, filename);

      const successMessage = `Successfully exported as ${filename}`;
      setExportSuccess(successMessage);
      setExportProgress(null);
      
      showSuccess('Export completed!', `File ${filename} has been downloaded`);
      
      // Auto-close modal after successful export
      setTimeout(() => {
        onClose();
      }, 2000);
    } catch (error) {
      console.error('Export failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Export failed';
      setExportError(errorMessage);
      setExportProgress(null);
      
      showError(
        'Export failed', 
        errorMessage,
        {
          action: {
            label: 'Try Again',
            onClick: () => handleExport(format)
          }
        }
      );
    } finally {
      setIsExporting(false);
    }
  };

  const getAnalysisTitle = () => {
    if (analysis.analysis_type === 'APP') {
      return `${analysis.app_id} (${analysis.platform})`;
    } else {
      return analysis.website_url || 'Website Analysis';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Export Analysis</h2>
          <button
            onClick={onClose}
            disabled={isExporting}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Analysis Info */}
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-900 mb-2">Analysis Details</h3>
            <div className="bg-gray-50 rounded-lg p-3 text-sm">
              <div className="flex justify-between mb-1">
                <span className="text-gray-600">Source:</span>
                <span className="font-medium">{getAnalysisTitle()}</span>
              </div>
              <div className="flex justify-between mb-1">
                <span className="text-gray-600">Total Reviews:</span>
                <span className="font-medium">{analysis.total_reviews.toLocaleString()}</span>
              </div>
              <div className="flex justify-between mb-1">
                <span className="text-gray-600">Complaint Clusters:</span>
                <span className="font-medium">{analysis.clusters.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Analysis Date:</span>
                <span className="font-medium">
                  {new Date(analysis.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>

          {/* Progress Indicator */}
          {exportProgress && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">
                  {exportProgress.message}
                </span>
                <span className="text-sm text-gray-500">
                  {exportProgress.progress}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${exportProgress.progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Success Message */}
          {exportSuccess && (
            <div className="mb-6 p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center">
                <CheckCircle className="h-5 w-5 text-green-600 mr-2" />
                <span className="text-sm text-green-800">{exportSuccess}</span>
              </div>
            </div>
          )}

          {/* Error Message */}
          {exportError && (
            <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center">
                <AlertCircle className="h-5 w-5 text-red-600 mr-2" />
                <span className="text-sm text-red-800">{exportError}</span>
              </div>
            </div>
          )}

          {/* Export Options */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-gray-900">Export Format</h3>
            
            {/* CSV Export */}
            <button
              onClick={() => handleExport('csv')}
              disabled={isExporting}
              className="w-full flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <div className="flex items-center">
                <FileText className="h-5 w-5 text-green-600 mr-3" />
                <div className="text-left">
                  <div className="font-medium text-gray-900">CSV Format</div>
                  <div className="text-sm text-gray-500">
                    Spreadsheet-friendly format with metadata and cluster details
                  </div>
                </div>
              </div>
              <Download className="h-4 w-4 text-gray-400" />
            </button>

            {/* JSON Export */}
            <button
              onClick={() => handleExport('json')}
              disabled={isExporting}
              className="w-full flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <div className="flex items-center">
                <Database className="h-5 w-5 text-blue-600 mr-3" />
                <div className="text-left">
                  <div className="font-medium text-gray-900">JSON Format</div>
                  <div className="text-sm text-gray-500">
                    Structured data with insights and recommendations
                  </div>
                </div>
              </div>
              <Download className="h-4 w-4 text-gray-400" />
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end space-x-3 p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            disabled={isExporting}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            {isExporting ? 'Exporting...' : 'Close'}
          </button>
        </div>
      </div>
    </div>
  );
}