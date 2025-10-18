// filepath: c:\workspace\CognitoForge-Ai\src\lib\api.ts
// API service for backend communication

// Get backend URL from environment variable with fallback
const BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';

/**
 * Base API configuration
 */
export const apiConfig = {
  baseURL: BASE_URL,
  timeout: 10000, // 10 seconds
  headers: {
    'Content-Type': 'application/json',
  },
};

/**
 * Generic API request wrapper with error handling
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  
  const config: RequestInit = {
    ...options,
    headers: {
      ...apiConfig.headers,
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error(`API request failed for ${endpoint}:`, error);
    throw error;
  }
}

/**
 * Health check endpoint
 */
export async function healthCheck(): Promise<{ status: string; message?: string }> {
  try {
    const response = await fetch(`${BASE_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Add timeout for health check
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });
    
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Health check failed:', error);
    throw error;
  }
}

/**
 * Upload repository for analysis
 */
export async function uploadRepository(repoUrl: string, analysisType: string) {
  return apiRequest('/api/upload', {
    method: 'POST',
    body: JSON.stringify({
      repoUrl,
      analysisType,
    }),
  });
}

/**
 * Start security analysis simulation
 */
export async function startAnalysis(repoId: string, config: any) {
  return apiRequest('/api/simulate', {
    method: 'POST',
    body: JSON.stringify({
      repoId,
      config,
    }),
  });
}

/**
 * Get latest analysis report
 */
export async function getLatestReport(repoId?: string) {
  const endpoint = repoId ? `/api/reports/${repoId}` : '/api/reports/latest';
  return apiRequest(endpoint, {
    method: 'GET',
  });
}

/**
 * Get analysis status
 */
export async function getAnalysisStatus(analysisId: string) {
  return apiRequest(`/api/analysis/${analysisId}/status`, {
    method: 'GET',
  });
}

/**
 * Download analysis report
 */
export async function downloadReport(reportId: string, format: 'pdf' | 'json' = 'pdf') {
  const response = await fetch(`${BASE_URL}/api/reports/${reportId}/download?format=${format}`, {
    method: 'GET',
    headers: {
      'Accept': format === 'pdf' ? 'application/pdf' : 'application/json',
    },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to download report: ${response.status}`);
  }
  
  return response.blob();
}

export default {
  healthCheck,
  uploadRepository,
  startAnalysis,
  getLatestReport,
  getAnalysisStatus,
  downloadReport,
};