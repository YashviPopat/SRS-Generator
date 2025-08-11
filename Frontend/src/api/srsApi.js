import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 120000, // 2 minutes timeout for file processing
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('❌ API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('❌ API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// API Service Functions
export const srsApi = {
  // Health check
  healthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },

  // Get standard headings
  getStandardHeadings: async () => {
    const response = await api.get('/standard-headings');
    return response.data;
  },

  // Upload and analyze documents
  analyzeDocuments: async (file, documentType) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);

    const response = await api.post('/analyze-docs', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Get heading suggestions
  getHeadingSuggestions: async (currentHeadings, projectContext, documentIds) => {
    const response = await api.post('/suggest-headings', {
      current_headings: currentHeadings,
      project_context: projectContext,
      document_ids: documentIds,
    });
    return response.data;
  },

  // Build SRS structure
  buildSrsStructure: async (headings, projectTitle, projectDescription, includeContentPlaceholders = true) => {
    const response = await api.post('/build-structure', {
      headings: headings,
      project_title: projectTitle,
      project_description: projectDescription,
      include_content_placeholders: includeContentPlaceholders,
    });
    return response.data;
  },

  // Generate DOCX file
  generateDocx: async (structureId, includePlaceholders = true, customStyling = null) => {
    const response = await api.post('/generate-docx', {
      structure_id: structureId,
      include_placeholders: includePlaceholders,
      custom_styling: customStyling,
    });
    return response.data;
  },

  // Download generated file
  downloadFile: async (fileId) => {
    const response = await api.get(`/download/${fileId}`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Get specific structure
  getStructure: async (structureId) => {
    const response = await api.get(`/structures/${structureId}`);
    return response.data;
  },

  // List uploaded documents
  listDocuments: async () => {
    const response = await api.get('/documents');
    return response.data;
  },

  // Generate content for selected headings
  generateContent: async (selectedHeadings) => {
    const response = await api.post('/generate-content', {
      headings: selectedHeadings
    });
    return response.data;
  },

  // Process all uploaded files at once
  processAllFiles: async (files) => {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    const response = await api.post('/process-all-files', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Process meeting summaries for Gemini heading generation
  processMeetingSummaries: async (files) => {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    const response = await api.post('/process-meeting-summaries', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Process docs folder for TOC extraction only
  processDocsFolderTOC: async () => {
    const response = await api.post('/process-docs-folder-toc');
    return response.data;
  },

  // Process PDF files from docs folder (legacy)
  processDocsFolder: async () => {
    const response = await api.post('/process-docs-folder');
    return response.data;
  },
};

// Utility functions for file handling
export const fileUtils = {
  // Convert file to base64 for preview
  fileToBase64: (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result);
      reader.onerror = (error) => reject(error);
    });
  },

  // Format file size
  formatFileSize: (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  },

  // Get file type icon
  getFileTypeIcon: (fileType) => {
    if (fileType.includes('pdf')) return '📄';
    if (fileType.includes('word') || fileType.includes('document')) return '📝';
    if (fileType.includes('text')) return '📄';
    return '📁';
  },

  // Validate file type
  isValidFileType: (file) => {
    const validTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
      'text/plain',
      'text/markdown'
    ];
    return validTypes.includes(file.type);
  },

  // Validate file size (10MB limit)
  isValidFileSize: (file) => {
    const maxSize = 10 * 1024 * 1024; // 10MB
    return file.size <= maxSize;
  }
};

// Error handling utilities
export const errorHandler = {
  // Handle API errors
  handleApiError: (error) => {
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;
      switch (status) {
        case 400:
          return `Bad Request: ${data.detail || 'Invalid data provided'}`;
        case 404:
          return `Not Found: ${data.detail || 'Resource not found'}`;
        case 500:
          return `Server Error: ${data.detail || 'Internal server error'}`;
        default:
          return `Error ${status}: ${data.detail || 'Something went wrong'}`;
      }
    } else if (error.request) {
      // Network error
      return 'Network Error: Unable to connect to server';
    } else {
      // Other error
      return `Error: ${error.message}`;
    }
  },

  // Handle file upload errors
  handleFileError: (file) => {
    if (!fileUtils.isValidFileType(file)) {
      return `Invalid file type: ${file.name}. Supported types: PDF, DOCX, DOC, TXT, MD`;
    }
    if (!fileUtils.isValidFileSize(file)) {
      return `File too large: ${file.name}. Maximum size: 10MB`;
    }
    return null;
  }
};

export default srsApi; 