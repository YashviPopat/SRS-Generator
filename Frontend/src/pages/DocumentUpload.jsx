import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, ArrowRight, CheckCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import UploadArea from '../components/UploadArea';
import { useDocumentData } from '../DocumentDataContext';

const DocumentUpload = () => {
  const navigate = useNavigate();
  const { setDocumentData } = useDocumentData();
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerateSRS = async () => {
    if (uploadedFiles.length === 0) {
      toast.error('Please upload at least one meeting summary document');
      return;
    }

    try {
      setIsGenerating(true);
      
      // Store uploaded files in context
      setDocumentData(prev => ({
        ...prev,
        uploadedFiles: uploadedFiles
      }));

      // Navigate to headings editor page
      navigate('/headings-editor');
      
    } catch (error) {
      console.error('Error preparing for SRS generation:', error);
      toast.error('Failed to prepare SRS generation');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                <FileText className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">SRS Dynamic Generator</h1>
                <p className="text-sm text-gray-600">Step 1: Upload Meeting Summaries</p>
              </div>
            </div>
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full">Step 1 of 2</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            Upload Your Meeting Summaries
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Upload your Fathom meeting summary PDFs to generate comprehensive SRS headings and content.
          </p>
        </div>

        {/* Upload Section */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Upload className="w-8 h-8 text-blue-600" />
            </div>
            <h3 className="text-2xl font-semibold text-gray-900 mb-2">
              Upload Meeting Summary Documents
            </h3>
            <p className="text-gray-600">
              Supported formats: PDF, DOCX, DOC, TXT
            </p>
          </div>

          <UploadArea
            onFilesUploaded={setUploadedFiles}
            uploadedFiles={uploadedFiles}
            acceptedFileTypes={['.pdf', '.docx', '.doc', '.txt']}
          />

          {/* File List */}
          {uploadedFiles.length > 0 && (
            <div className="mt-8">
              <h4 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
                Uploaded Files ({uploadedFiles.length})
              </h4>
              <div className="space-y-3">
                {uploadedFiles.map((file, index) => (
                  <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <FileText className="w-5 h-5 text-blue-600" />
                      <div>
                        <p className="font-medium text-gray-900">{file.name}</p>
                        <p className="text-sm text-gray-500">
                          {(file.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="text-center">
          <button
            onClick={handleGenerateSRS}
            disabled={uploadedFiles.length === 0 || isGenerating}
            className="bg-blue-600 text-white px-8 py-4 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center mx-auto space-x-2 text-lg font-medium"
          >
            {isGenerating ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                <span>Preparing...</span>
              </>
            ) : (
              <>
                <span>Continue to SRS Generator</span>
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
          
          {uploadedFiles.length === 0 && (
            <p className="text-sm text-gray-500 mt-4">
              Please upload at least one meeting summary document to continue
            </p>
          )}
        </div>

        {/* Instructions */}
        <div className="mt-12 bg-blue-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-4">
            How it works:
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-white font-bold">1</span>
              </div>
              <h4 className="font-medium text-blue-900 mb-2">Upload Documents</h4>
              <p className="text-sm text-blue-700">
                Upload your Fathom meeting summary PDFs or other project documents
              </p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-white font-bold">2</span>
              </div>
              <h4 className="font-medium text-blue-900 mb-2">AI Analysis</h4>
              <p className="text-sm text-blue-700">
                AI will extract headings and generate SRS suggestions from your documents
              </p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-white font-bold">3</span>
              </div>
              <h4 className="font-medium text-blue-900 mb-2">Generate SRS</h4>
              <p className="text-sm text-blue-700">
                Select headings and generate your final SRS document
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default DocumentUpload; 