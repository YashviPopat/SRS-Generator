import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, FileText, File, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { useDocumentData } from '../DocumentDataContext';

const UploadArea = ({ onFilesUploaded, uploadedFiles, acceptedFileTypes }) => {
  const { setDocumentData } = useDocumentData();
  
  const onDrop = useCallback(async (acceptedFiles, rejectedFiles) => {
    if (rejectedFiles.length > 0) {
      toast.error('Some files were rejected. Please check file types and sizes.');
      return;
    }

    const newFiles = acceptedFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'uploaded',
      documentId: null,
      processed: false
    }));

    // Add files to state immediately
    onFilesUploaded(prev => [...prev, ...newFiles]);

    // Update DocumentDataContext
    setDocumentData(prev => ({
      ...prev,
      uploadedFiles: [...(prev.uploadedFiles || []), ...newFiles],
    }));

    console.log('✅ Files uploaded successfully:', newFiles.map(f => f.name));
    toast.success(`${acceptedFiles.length} file(s) uploaded successfully!`);
  }, [onFilesUploaded, setDocumentData, uploadedFiles]);

  // Helper function to determine document type (commented out for future use)
  // const getDocumentType = (file) => {
  //   if (file.type.includes('pdf')) return 'srs';
  //   if (file.type.includes('word') || file.type.includes('document')) return 'requirements';
  //   if (file.type.includes('text') || file.type.includes('markdown')) return 'meeting_transcript';
  //   return 'other';
  // };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedFileTypes ? {
      'application/pdf': acceptedFileTypes.includes('.pdf') ? ['.pdf'] : [],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': acceptedFileTypes.includes('.docx') ? ['.docx'] : [],
      'application/msword': acceptedFileTypes.includes('.doc') ? ['.doc'] : [],
      'text/plain': acceptedFileTypes.includes('.txt') ? ['.txt'] : [],
      'text/markdown': acceptedFileTypes.includes('.md') ? ['.md'] : []
    } : {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: true
  });

  const removeFile = (fileId) => {
    onFilesUploaded(prev => prev.filter(file => file.id !== fileId));
    
    // Also remove from DocumentDataContext
    setDocumentData(prev => ({
      ...prev,
      uploadedFiles: prev.uploadedFiles.filter(file => file.id !== fileId)
    }));
    
    toast.success('File removed');
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (fileType) => {
    if (fileType.includes('pdf')) return <File className="w-5 h-5 text-red-500" />;
    if (fileType.includes('word') || fileType.includes('document')) return <FileText className="w-5 h-5 text-blue-500" />;
    return <File className="w-5 h-5 text-gray-500" />;
  };

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors duration-200 ${
          isDragActive
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p className="text-lg font-medium text-gray-900 mb-2">
          {isDragActive ? 'Drop files here...' : 'Drag & drop files here'}
        </p>
        <p className="text-gray-600 mb-4">
          or click to select files
        </p>
        <div className="text-sm text-gray-500">
          <p>Supported formats: PDF, DOCX, DOC, TXT, MD</p>
          <p>Maximum file size: 10MB</p>
          <p className="text-blue-600 font-medium mt-2">
            Files will be processed when you click "Generate Headings"
          </p>
        </div>
      </div>

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-700">
            Uploaded Files ({uploadedFiles.length})
          </h4>
          
          <div className="space-y-2">
            {uploadedFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
              >
                <div className="flex items-center space-x-3">
                  {getFileIcon(file.type)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(file.size)}
                    </p>
                    {file.processed && (
                      <p className="text-xs text-green-600 font-medium">
                        ✓ Processed
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  {file.status === 'uploaded' && !file.processed && (
                    <div className="w-2 h-2 bg-blue-500 rounded-full" />
                  )}
                  {file.processed && (
                    <div className="w-2 h-2 bg-green-500 rounded-full" />
                  )}
                  {file.status === 'error' && (
                    <AlertCircle className="w-4 h-4 text-red-500" />
                  )}
                  
                  <button
                    onClick={() => removeFile(file.id)}
                    className="p-1 hover:bg-gray-200 rounded transition-colors duration-200"
                    title="Remove file"
                  >
                    <X className="w-4 h-4 text-gray-500" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* File Type Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <div className="w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center mt-0.5">
            <span className="text-white text-xs font-bold">i</span>
          </div>
          <div>
            <h4 className="text-sm font-medium text-blue-900 mb-1">
              Supported File Types
            </h4>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• <strong>PDF files:</strong> Meeting summaries, SRS documents, requirements</li>
              <li>• <strong>Word documents:</strong> DOCX, DOC files with project requirements</li>
              <li>• <strong>Text files:</strong> TXT, MD files with meeting transcripts</li>
            </ul>
            <p className="text-sm text-blue-700 mt-2 font-medium">
              💡 Tip: Upload all your meeting summary PDFs first, then click "Generate Headings" to extract SRS headings from all files at once.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UploadArea; 