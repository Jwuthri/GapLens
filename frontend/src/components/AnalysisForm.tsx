'use client';

import { useState, useEffect, useCallback } from 'react';
import { Search, Loader2, AlertCircle, CheckCircle, AlertTriangle, Info } from 'lucide-react';
import { validateInput, ValidationResult } from '@/utils/validation';
import { AnalysisRequest } from '@/types';

interface AnalysisFormProps {
  onSubmit: (request: AnalysisRequest) => void;
  isLoading: boolean;
}

export default function AnalysisForm({ onSubmit, isLoading }: AnalysisFormProps) {
  const [input, setInput] = useState('');
  const [analysisType, setAnalysisType] = useState<'APP' | 'WEBSITE'>('APP');
  const [validation, setValidation] = useState<ValidationResult>({ isValid: false });
  const [showValidation, setShowValidation] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [userSelectedType, setUserSelectedType] = useState(false);

  // Debounced validation
  const validateInputDebounced = useCallback(
    debounce((value: string) => {
      if (value.trim()) {
        const result = validateInput(value, { strictMode: true });
        setValidation(result);
        setShowValidation(hasInteracted);
      } else {
        setValidation({ isValid: false });
        setShowValidation(false);
      }
    }, 300),
    [hasInteracted]
  );

  useEffect(() => {
    validateInputDebounced(input);
  }, [input, validateInputDebounced]);

  const handleInputChange = (value: string) => {
    setInput(value);
    setHasInteracted(true);
    
    // Only auto-detect analysis type if user hasn't explicitly selected one
    if (value.trim() && !userSelectedType) {
      const quickValidation = validateInput(value);
      if (quickValidation.isValid && quickValidation.type) {
        setAnalysisType(quickValidation.type);
      }
    }
  };

  const handleInputBlur = () => {
    if (input.trim()) {
      setShowValidation(true);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const finalValidation = validateInput(input, { strictMode: true });
    setValidation(finalValidation);
    setShowValidation(true);
    
    if (!finalValidation.isValid) {
      return;
    }

    onSubmit({
      input: input.trim(),
      analysis_type: analysisType,
    });
  };

  const getValidationIcon = () => {
    if (!showValidation || !input.trim()) return null;
    
    if (validation.isValid) {
      return <CheckCircle className="h-4 w-4 text-green-400" />;
    } else {
      return <AlertCircle className="h-4 w-4 text-red-400" />;
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto relative z-10">
      <div className="card-dark p-8 glow-purple">
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Analysis Type Selection */}
          <div className="flex space-x-4 justify-center">
            <button
              type="button"
              onClick={() => {
                setAnalysisType('APP');
                setUserSelectedType(true);
              }}
              className={`px-8 py-4 rounded-xl font-semibold transition-all duration-300 transform hover:scale-105 ${
                analysisType === 'APP'
                  ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-600'
              }`}
            >
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                <span>App Store Analysis</span>
              </div>
            </button>
            <button
              type="button"
              onClick={() => {
                setAnalysisType('WEBSITE');
                setUserSelectedType(true);
              }}
              className={`px-8 py-4 rounded-xl font-semibold transition-all duration-300 transform hover:scale-105 ${
                analysisType === 'WEBSITE'
                  ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-600'
              }`}
            >
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                <span>Website Analysis</span>
              </div>
            </button>
          </div>

          {/* Terminal-style Input */}
          <div className="space-y-4">
            <div className="terminal-window">
              <div className="terminal-header">
                <div className="flex items-center space-x-2">
                  <div className="terminal-dot bg-red-500"></div>
                  <div className="terminal-dot bg-yellow-500"></div>
                  <div className="terminal-dot bg-green-500"></div>
                </div>
                <div className="flex-1 text-center">
                  <span className="text-xs text-gray-400 font-mono">
                    {analysisType === 'APP' ? 'app-analyzer' : 'web-analyzer'} — zsh — 80×24
                  </span>
                </div>
              </div>
              <div className="p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-green-400 font-mono text-sm">$</span>
                  <span className="text-gray-400 font-mono text-sm">analyze</span>
                  <span className="text-purple-400 font-mono text-sm">
                    {analysisType === 'APP' ? '--app' : '--website'}
                  </span>
                </div>
                <div className="relative">
                  <input
                    id="input"
                    type="text"
                    value={input}
                    onChange={(e) => handleInputChange(e.target.value)}
                    onBlur={handleInputBlur}
                    placeholder={
                      analysisType === 'APP'
                        ? 'https://play.google.com/store/apps/details?id=com.example.app'
                        : 'https://example.com'
                    }
                    className="w-full bg-transparent text-white font-mono text-sm border-none outline-none placeholder-gray-500"
                    disabled={isLoading}
                  />
                  <div className="absolute right-0 top-0 flex items-center space-x-2">
                    {getValidationIcon()}
                  </div>
                </div>
                {input && (
                  <div className="mt-2 text-xs text-gray-500 font-mono">
                    Generating game logic... Creating game engine...
                  </div>
                )}
              </div>
            </div>
            
            {/* Helper Text */}
            <p className="text-sm text-gray-400 text-center">
              {analysisType === 'APP' 
                ? 'Enter a Google Play Store or App Store URL, or just the app ID'
                : 'Enter a website URL to analyze reviews from Google, Yelp, and social media'
              }
            </p>
          </div>

          {/* Validation Messages */}
          {showValidation && input.trim() && (
            <div className="space-y-3">
              {/* Error Message */}
              {!validation.isValid && validation.error && (
                <div className="flex items-center space-x-3 text-red-300 bg-red-900/30 border border-red-500/50 p-4 rounded-lg">
                  <AlertCircle className="h-5 w-5 flex-shrink-0" />
                  <span className="text-sm">{validation.error}</span>
                </div>
              )}

              {/* Success Message */}
              {validation.isValid && (
                <div className="flex items-center space-x-3 text-green-300 bg-green-900/30 border border-green-500/50 p-4 rounded-lg">
                  <CheckCircle className="h-5 w-5 flex-shrink-0" />
                  <span className="text-sm">
                    {validation.type === 'APP' 
                      ? 'Valid app identifier detected'
                      : 'Valid website URL detected'
                    }
                  </span>
                </div>
              )}

              {/* Warning Messages */}
              {validation.warnings && validation.warnings.length > 0 && (
                <div className="space-y-2">
                  {validation.warnings.map((warning, index) => (
                    <div key={index} className="flex items-start space-x-3 text-yellow-300 bg-yellow-900/30 border border-yellow-500/50 p-4 rounded-lg">
                      <AlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                      <span className="text-sm">{warning}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading || !input.trim() || (showValidation && !validation.isValid)}
            className="btn-primary animate-glow mx-auto px-8 py-2 flex items-center space-x-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-6 w-6 animate-spin" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <Search className="h-5 w-5" />
                <span>Start Analysis →</span>
              </>
            )}
          </button>

          {/* Feature Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
            <div className="card p-4 text-center">
              <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg mx-auto mb-3 flex items-center justify-center">
                <Search className="h-6 w-6 text-white" />
              </div>
              <h3 className="font-semibold text-white mb-2">Chat to Create</h3>
              <p className="text-sm text-gray-400">Simply describe your game idea in natural language and watch it come to life</p>
            </div>
            <div className="card p-4 text-center">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-green-500 rounded-lg mx-auto mb-3 flex items-center justify-center">
                <CheckCircle className="h-6 w-6 text-white" />
              </div>
              <h3 className="font-semibold text-white mb-2">No Coding Required</h3>
              <p className="text-sm text-gray-400">Create complex games without writing a single line of code</p>
            </div>
            <div className="card p-4 text-center">
              <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-purple-500 rounded-lg mx-auto mb-3 flex items-center justify-center">
                <AlertTriangle className="h-6 w-6 text-white" />
              </div>
              <h3 className="font-semibold text-white mb-2">Instantly Playable</h3>
              <p className="text-sm text-gray-400">Get a working game in seconds that you can play and share immediately</p>
            </div>
          </div>

          {/* Additional Info */}
          <div className="card p-6 border-purple-500/30">
            <div className="flex items-start space-x-3">
              <Info className="h-6 w-6 text-purple-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-gray-300">
                <p className="font-semibold mb-2 text-white">Get Early Access</p>
                <ul className="space-y-2 text-gray-400">
                  <li>• We collect and analyze negative reviews (1-2 stars)</li>
                  <li>• Reviews are grouped by similar complaints using AI</li>
                  <li>• Results show the most common issues ranked by frequency</li>
                  <li>• Analysis typically takes 1-3 minutes depending on review volume</li>
                </ul>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

// Debounce utility function
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}