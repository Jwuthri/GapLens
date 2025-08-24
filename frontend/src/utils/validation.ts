export interface ValidationResult {
  isValid: boolean;
  error?: string;
  type?: 'APP' | 'WEBSITE';
  warnings?: string[];
}

export interface ValidationOptions {
  allowEmpty?: boolean;
  strictMode?: boolean;
}

// Common error messages for consistency
export const ERROR_MESSAGES = {
  EMPTY_INPUT: 'Please enter a URL or app ID',
  INVALID_URL: 'Please enter a valid URL',
  INVALID_APP_ID: 'App ID should be in format com.example.app',
  UNSUPPORTED_APP_STORE: 'Only Google Play Store and App Store URLs are supported',
  MALFORMED_PLAY_STORE_URL: 'Google Play Store URL should contain app ID parameter',
  MALFORMED_APP_STORE_URL: 'App Store URL should contain valid app identifier',
  SUSPICIOUS_URL: 'This URL looks suspicious. Please verify it\'s correct',
  WEBSITE_URL_TOO_SHORT: 'Website URL seems too short. Please enter a complete URL',
  LOCALHOST_WARNING: 'Localhost URLs cannot be analyzed for reviews',
} as const;

export function validateInput(input: string, options: ValidationOptions = {}): ValidationResult {
  const { allowEmpty = false, strictMode = false } = options;
  
  if (!input.trim()) {
    return { 
      isValid: allowEmpty, 
      error: allowEmpty ? undefined : ERROR_MESSAGES.EMPTY_INPUT 
    };
  }

  const trimmedInput = input.trim();
  const warnings: string[] = [];

  // URL validation
  if (trimmedInput.startsWith('http://') || trimmedInput.startsWith('https://')) {
    try {
      const url = new URL(trimmedInput);
      const hostname = url.hostname.toLowerCase();
      const pathname = url.pathname.toLowerCase();
      
      // Check for localhost
      if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname.endsWith('.local')) {
        warnings.push(ERROR_MESSAGES.LOCALHOST_WARNING);
      }

      // App Store URL validation
      if (hostname.includes('play.google.com')) {
        if (!url.searchParams.get('id') && !pathname.includes('/details')) {
          return { 
            isValid: false, 
            error: ERROR_MESSAGES.MALFORMED_PLAY_STORE_URL 
          };
        }
        return { isValid: true, type: 'APP', warnings };
      }

      if (hostname.includes('apps.apple.com') || hostname.includes('itunes.apple.com')) {
        if (!pathname.includes('/app/') && !pathname.includes('/id')) {
          return { 
            isValid: false, 
            error: ERROR_MESSAGES.MALFORMED_APP_STORE_URL 
          };
        }
        return { isValid: true, type: 'APP', warnings };
      }

      // Check for other app store URLs that we don't support
      if (strictMode && (
        hostname.includes('amazon.com') && pathname.includes('/dp/') ||
        hostname.includes('microsoft.com') && pathname.includes('/store/') ||
        hostname.includes('samsung.com') && pathname.includes('/galaxy-store/')
      )) {
        return { 
          isValid: false, 
          error: ERROR_MESSAGES.UNSUPPORTED_APP_STORE 
        };
      }

      // Website URL validation
      if (url.pathname === '/' && !url.search && trimmedInput.length < 15) {
        warnings.push(ERROR_MESSAGES.WEBSITE_URL_TOO_SHORT);
      }

      // Check for suspicious patterns
      if (strictMode && (
        hostname.includes('bit.ly') || 
        hostname.includes('tinyurl.com') ||
        hostname.includes('t.co') ||
        url.pathname.includes('..') ||
        url.search.includes('<') || 
        url.search.includes('>')
      )) {
        warnings.push(ERROR_MESSAGES.SUSPICIOUS_URL);
      }

      return { isValid: true, type: 'WEBSITE', warnings };
    } catch {
      return { isValid: false, error: ERROR_MESSAGES.INVALID_URL };
    }
  }

  // App ID validation (without URL)
  if (trimmedInput.includes('.')) {
    // Basic package name validation
    const parts = trimmedInput.split('.');
    
    if (parts.length < 2) {
      return { 
        isValid: false, 
        error: ERROR_MESSAGES.INVALID_APP_ID 
      };
    }

    // Check for valid package name format
    const isValidPackageName = parts.every(part => 
      part.length > 0 && 
      /^[a-zA-Z][a-zA-Z0-9_]*$/.test(part)
    );

    if (strictMode && !isValidPackageName) {
      return { 
        isValid: false, 
        error: ERROR_MESSAGES.INVALID_APP_ID 
      };
    }

    return { isValid: true, type: 'APP', warnings };
  }

  // If it doesn't look like a URL or app ID
  return { 
    isValid: false, 
    error: 'Please enter a valid URL or app ID (e.g., com.example.app)' 
  };
}

export function validateAppId(appId: string): ValidationResult {
  return validateInput(appId, { strictMode: true });
}

export function validateWebsiteUrl(url: string): ValidationResult {
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    return { isValid: false, error: 'Website URL must start with http:// or https://' };
  }
  return validateInput(url, { strictMode: true });
}

// Utility functions for formatting
export function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function truncateText(text: string, maxLength: number = 100): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength).trim() + '...';
}