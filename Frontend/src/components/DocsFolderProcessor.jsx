import React, { useState } from 'react';
import { toast } from 'react-hot-toast';
import { 
  FolderIcon, 
  DocumentTextIcon, 
  SparklesIcon,
  ArrowDownTrayIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import { srsApi, errorHandler } from '../api/srsApi';

const DocsFolderProcessor = () => {
  const [processing, setProcessing] = useState(false);

  const [geminiSuggestions, setGeminiSuggestions] = useState({});
  const [selectedHeadings, setSelectedHeadings] = useState({});
  const [processingComplete, setProcessingComplete] = useState(false);

  const processDocsFolder = async () => {
    try {
      setProcessing(true);
      setProcessingComplete(false);
      
      toast.loading('Processing PDF files from docs folder... This may take a few minutes.', {
        duration: 10000
      });
      
      const response = await srsApi.processDocsFolder();
      
      if (response.success) {
        setGeminiSuggestions(response.gemini_suggestions || {});
        setProcessingComplete(true);
        
        toast.success(`✅ Successfully processed docs folder!`);
        
        console.log('Processing results:', {
          gemini_suggestions: response.gemini_suggestions,
          files_processed: response.files_processed
        });
      } else {
        throw new Error(response.message || 'Failed to process docs folder');
      }
      
    } catch (error) {
      console.error('Error processing docs folder:', error);
      toast.error(errorHandler.handleApiError(error));
    } finally {
      setProcessing(false);
    }
  };

  const handleHeadingToggle = (category, heading) => {
    setSelectedHeadings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [heading]: !prev[category]?.[heading]
      }
    }));
  };

  // Toggle all headings
  const toggleAllHeadings = () => {
    const selectedCount = Object.keys(selectedHeadings).length;
    
    if (selectedCount === 0) {
      // Select all if none are selected
      const allHeadings = {};
      Object.entries(headings).forEach(([category, categoryHeadings]) => {
        allHeadings[category] = {};
        Object.entries(categoryHeadings).forEach(([heading, purpose]) => {
          allHeadings[category][heading] = true;
        });
      });
      setSelectedHeadings(allHeadings);
    } else {
      // Deselect all if some or all are selected
      setSelectedHeadings({});
    }
  };

  const getAllSelectedHeadings = () => {
    const selected = [];
    
    Object.entries(selectedHeadings).forEach(([category, headings]) => {
      Object.entries(headings).forEach(([heading, isSelected]) => {
        if (isSelected) {
          selected.push({
            heading,
            purpose: '',
            source: 'Extracted from Docs Folder',
            category
          });
        }
      });
    });
    
    return selected;
  };

  const renderNestedHeadings = (headings, selectedHeadings, onToggle, title, toggleAllHandler) => {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-full">
        <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
          <DocumentTextIcon className="w-5 h-5 mr-2" />
          {title}
        </h2>
        
        {Object.keys(headings).length > 0 ? (
          <>
            {/* Toggle All button */}
            <div className="mb-4 flex justify-end">
              <button
                onClick={toggleAllHandler}
                className="bg-blue-600 text-white px-3 py-1 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 text-xs"
              >
                {Object.keys(selectedHeadings).length === 0 ? 'Select All' : 'Deselect All'}
              </button>
            </div>
            
            {Object.entries(headings).map(([category, categoryHeadings]) => (
              <div key={category} className="mb-6">
                <h3 className="text-lg font-medium text-gray-700 mb-3 border-b border-gray-200 pb-2">
                  {category}
                </h3>
                <div className="space-y-2">
                  {Object.entries(categoryHeadings).map(([heading, purpose]) => (
                    <div key={heading} className="flex items-start space-x-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50">
                      <input
                        type="checkbox"
                        checked={!!selectedHeadings[category]?.[heading]}
                        onChange={() => onToggle(category, heading)}
                        className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900">{heading}</div>
                        <div className="text-xs text-gray-500 mt-1">{purpose}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </>
        ) : (
          <div className="flex items-center justify-center h-32 text-gray-400 text-center">
            <span>No headings available. Process the docs folder to extract headings.</span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                <FolderIcon className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Docs Folder Processor</h1>
                <p className="text-sm text-gray-600">Extract headings from PDF files in docs folder</p>
              </div>
            </div>
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full">Vector Store</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Process Docs Folder Button */}
        <div className="mb-8 text-center">
          <button
            onClick={processDocsFolder}
            disabled={processing}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center mx-auto space-x-2"
          >
            {processing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Processing Docs Folder...</span>
              </>
            ) : (
              <>
                <SparklesIcon className="w-4 h-4" />
                <span>Process Docs Folder</span>
              </>
            )}
          </button>
          <p className="text-sm text-gray-500 mt-2">
            Click to extract headings from PDF files in the docs/Pdf_files folder using vector store
          </p>
        </div>

        {/* Processing Status */}
        {processingComplete && (
          <div className="mb-8 bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center">
              <CheckCircleIcon className="w-5 h-5 text-green-600 mr-2" />
              <span className="text-green-800 font-medium">
                Processing complete! Headings extracted and organized in nested format.
              </span>
            </div>
          </div>
        )}

        { }
        {Object.keys(AISuggestions).length > 0 && (
          <div className="mb-8">
            <div className="h-[600px] overflow-y-auto">
              {renderNestedHeadings(
                geminiSuggestions,
                selectedHeadings,
                handleHeadingToggle,
                'AI Generated Suggestions',
                toggleAllHeadings
              )}
            </div>
          </div>
        )}

        {/* Selected Headings Summary */}
        {Object.keys(selectedHeadings).length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
              <ArrowDownTrayIcon className="w-5 h-5 mr-2" />
              Selected Headings Summary
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(selectedHeadings).map(([category, headings]) => (
                <div key={category} className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-medium text-gray-700 mb-2">{category}</h3>
                  <div className="space-y-1">
                    {Object.entries(headings).map(([heading, isSelected]) => (
                      isSelected && (
                        <div key={heading} className="text-sm text-gray-600">
                          • {heading}
                        </div>
                      )
                    ))}
                  </div>
                </div>
              ))}
            </div>
            
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-500">
                Total selected: {getAllSelectedHeadings().length} headings
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocsFolderProcessor; 