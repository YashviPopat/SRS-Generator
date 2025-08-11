import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText } from 'lucide-react';
import HeadingEditor from '../components/HeadingEditor';

const Editor = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { projectTitle, projectDescription, uploadedFiles } = location.state || {};

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/')}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors duration-200"
              >
                <ArrowLeft className="w-5 h-5 text-gray-600" />
              </button>
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                  <FileText className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-gray-900">SRS Editor</h1>
                  <p className="text-sm text-gray-600">Structure your requirements</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="card">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              {projectTitle || 'Untitled Project'}
            </h2>
            {projectDescription && (
              <p className="text-gray-600">{projectDescription}</p>
            )}
          </div>

          {/* Project Info */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h3 className="font-medium text-blue-900 mb-2">Project Title</h3>
              <p className="text-blue-800">{projectTitle || 'Not specified'}</p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <h3 className="font-medium text-green-900 mb-2">Documents Uploaded</h3>
              <p className="text-green-800">{uploadedFiles?.length || 0} files</p>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <h3 className="font-medium text-purple-900 mb-2">Status</h3>
              <p className="text-purple-800">Ready for analysis</p>
            </div>
          </div>

          {/* Navigation Buttons */}
          <div className="flex gap-4 mb-8">
            <button
              onClick={() => navigate('/comparison', { state: { projectTitle, projectDescription, uploadedFiles } })}
              className="btn-primary flex items-center space-x-2"
            >
              <FileText className="w-4 h-4" />
              <span>Compare Headings</span>
            </button>
          </div>

          {/* SRS Structure Editor */}
          <HeadingEditor
            projectTitle={projectTitle}
            projectDescription={projectDescription}
            uploadedFiles={uploadedFiles}
          />
        </div>
      </main>
    </div>
  );
};

export default Editor; 