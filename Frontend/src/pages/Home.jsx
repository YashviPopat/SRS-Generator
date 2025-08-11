import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, Settings, Download, Sparkles } from 'lucide-react';
import toast from 'react-hot-toast';
import UploadArea from '../components/UploadArea';
import { useDocumentData } from '../DocumentDataContext';

const Home = () => {
  const navigate = useNavigate();
  const { documentData, setDocumentData } = useDocumentData();
  const [projectTitle, setProjectTitle] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState([]);

  // No localStorage loading - files need to be uploaded fresh each time

  const handleStartProject = async () => {
    if (!projectTitle.trim()) {
      toast.error('Please enter a project title');
      return;
    }

    if (uploadedFiles.length === 0) {
      toast.error('Please upload at least one document');
      return;
    }

    try {
      // Extract text content from uploaded files (meeting summaries only, not PDFs)
      const formData = new FormData();
      
      // Get the actual File objects from the uploaded files
      const actualFiles = uploadedFiles.map(fileObj => fileObj.file).filter(Boolean);
      
      console.log('Uploaded files:', uploadedFiles);
      console.log('Actual files found:', actualFiles.length);
      
      if (actualFiles.length === 0) {
        toast.error('No files found. Please upload your documents first.');
        return;
      }
      
      actualFiles.forEach(file => {
        formData.append('files', file);
      });

      // Process meeting summary files for Gemini heading generation
      console.log('Sending meeting summary files to backend:', actualFiles.map(f => f.name));
      
      const response = await fetch('/process-meeting-summaries', {
        method: 'POST',
        body: formData
      });

      console.log('Response status:', response.status);
      
      if (response.ok) {
        const data = await response.json();
        
        console.log('Backend response:', data);
        console.log('Extracted text content:', data.extracted_text_content);
        console.log('Extracted text content keys:', Object.keys(data.extracted_text_content || {}));
        
        // Validate that we got extracted text content
        if (!data.extracted_text_content || Object.keys(data.extracted_text_content).length === 0) {
          console.error('❌ No extracted text content received from backend');
          toast.error('Failed to extract text from uploaded files. Please try again.');
          return;
        }
        
        // Store the extracted text content in context (meeting summaries only)
        const newDocumentData = {
          ...documentData,
          uploadedFiles: uploadedFiles,
          extractedTextContent: data.extracted_text_content || {},
          projectTitle: projectTitle,
          projectDescription: projectDescription
        };
        
        console.log('Setting new documentData:', newDocumentData);
        console.log('extractedTextContent in newDocumentData:', newDocumentData.extractedTextContent);
        console.log('extractedTextContent keys:', Object.keys(newDocumentData.extractedTextContent || {}));
        
        setDocumentData(newDocumentData);
        
        console.log('Updated documentData:', {
          uploadedFiles: uploadedFiles.length,
          extractedTextContent: Object.keys(data.extracted_text_content || {}).length,
          projectTitle,
          projectDescription
        });
        
        console.log('✅ Data processed successfully');
        console.log('Extracted text content keys:', Object.keys(data.extracted_text_content || {}));

        // Navigate immediately - the context should be updated
        console.log('Navigating to headings editor...');
        navigate('/headings-editor');
      } else {
        throw new Error('Failed to process files');
      }
    } catch (error) {
      console.error('Error processing files:', error);
      toast.error('Failed to process uploaded files');
    }
  };

  const features = [
    {
      icon: <Sparkles className="w-6 h-6" />,
      title: "AI-Powered Suggestions",
      description: "Get intelligent heading suggestions based on your project context and similar documents."
    },
    {
      icon: <FileText className="w-6 h-6" />,
      title: "Dynamic Structure",
      description: "Create custom SRS structures with drag-and-drop editing and real-time preview."
    },
    {
      icon: <Settings className="w-6 h-6" />,
      title: "Smart Comparison",
      description: "Compare your headings with standard templates and previous SRS documents."
    },
    {
      icon: <Download className="w-6 h-6" />,
      title: "Export to DOCX",
      description: "Generate professional Microsoft Word documents with proper formatting."
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                <FileText className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">SRS Dynamic Generator</h1>
                <p className="text-sm text-gray-600">AI-powered Software Requirements Specification</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            Generate Professional SRS Documents
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Upload your project documents and let AI help you create comprehensive 
            Software Requirements Specifications with intelligent heading suggestions.
          </p>
        </div>

        {/* Project Setup Form */}
        <div className="max-w-4xl mx-auto">
          <div className="card mb-8">
            <h3 className="text-2xl font-semibold text-gray-900 mb-6">
              Start Your Project
            </h3>
            
            <div className="space-y-6">
              {/* Project Details */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Project Title *
                  </label>
                  <input
                    type="text"
                    value={projectTitle}
                    onChange={(e) => setProjectTitle(e.target.value)}
                    placeholder="Enter your project title"
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Project Description
                  </label>
                  <input
                    type="text"
                    value={projectDescription}
                    onChange={(e) => setProjectDescription(e.target.value)}
                    placeholder="Brief description of your project"
                    className="input-field"
                  />
                </div>
              </div>

              {/* File Upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Upload Project Documents *
                </label>
                <UploadArea
                  onFilesUploaded={setUploadedFiles}
                  uploadedFiles={uploadedFiles}
                />
              </div>

              {/* Action Buttons */}
              <div className="flex justify-center pt-6 space-x-4">
                <button
                  onClick={handleStartProject}
                  disabled={!projectTitle.trim() || uploadedFiles.length === 0}
                  className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 px-8 py-3 text-lg"
                >
                  <Sparkles className="w-5 h-5" />
                  <span>SRS Generator</span>
                </button>
                
                {/* Debug button */}
                <button
                  onClick={() => {
                    console.log('=== DEBUG UPLOADED FILES ===');
                    console.log('uploadedFiles:', uploadedFiles);
                    console.log('uploadedFiles length:', uploadedFiles.length);
                    uploadedFiles.forEach((file, index) => {
                      console.log(`File ${index}:`, {
                        id: file.id,
                        name: file.name,
                        size: file.size,
                        type: file.type,
                        hasFile: !!file.file,
                        fileType: file.file ? typeof file.file : 'no file'
                      });
                    });
                    toast.info(`Debug: ${uploadedFiles.length} files loaded`);
                  }}
                  className="btn-secondary flex items-center space-x-2 px-4 py-3 text-sm"
                >
                  <span>🔍 Debug Files</span>
                </button>
                

              </div>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="mt-20">
          <h3 className="text-3xl font-bold text-gray-900 text-center mb-12">
            Why Choose SRS Dynamic Generator?
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div key={index} className="card-hover text-center">
                <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                  <div className="text-primary-600">
                    {feature.icon}
                  </div>
                </div>
                <h4 className="text-lg font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h4>
                <p className="text-gray-600 text-sm">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* How It Works */}
        <div className="mt-20">
          <h3 className="text-3xl font-bold text-gray-900 text-center mb-12">
            How It Works
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-white font-bold text-xl">1</span>
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-2">
                Upload Documents
              </h4>
              <p className="text-gray-600">
                Upload your project documents, requirements, or meeting transcripts.
              </p>
            </div>
            
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-white font-bold text-xl">2</span>
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-2">
                AI Analysis
              </h4>
              <p className="text-gray-600">
                Our AI analyzes your documents and suggests relevant SRS headings.
              </p>
            </div>
            
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-white font-bold text-xl">3</span>
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-2">
                Generate & Export
              </h4>
              <p className="text-gray-600">
                Customize your structure and export as a professional DOCX document.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Home; 