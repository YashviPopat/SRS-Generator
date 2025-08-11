import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText, Plus, Trash2, CheckSquare, Square, Sparkles, Download } from 'lucide-react';
import toast from 'react-hot-toast';
import { srsApi, errorHandler } from '../api/srsApi';

const Comparison = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { projectTitle, projectDescription, uploadedFiles } = location.state || {};

  const [standardHeadings, setStandardHeadings] = useState([]);
  const [selectedStandardHeadings, setSelectedStandardHeadings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generatingContent, setGeneratingContent] = useState(false);
  const [showAddHeading, setShowAddHeading] = useState(false);
  const [newHeading, setNewHeading] = useState({ title: '', purpose: '' });

  // Load data on component mount
  useEffect(() => {
    loadStandardHeadings();
  }, []);

  const loadStandardHeadings = async () => {
    try {
      setLoading(true);
      const response = await srsApi.getStandardHeadings();
      const flatHeadings = flattenHeadings(response.headings);
      setStandardHeadings(flatHeadings);
      toast.success('Standard headings loaded!');
    } catch (error) {
      console.error('Error loading standard headings:', error);
      toast.error(errorHandler.handleApiError(error));
    } finally {
      setLoading(false);
    }
  };

  const flattenHeadings = (headingsObj, parentKey = '') => {
    const flat = [];
    for (const [key, value] of Object.entries(headingsObj)) {
      if (typeof value === 'object' && value !== null) {
        const currentPath = parentKey ? `${parentKey} > ${key}` : key;
        if (typeof value === 'string') {
          flat.push({ id: `std-${flat.length}`, heading: currentPath, purpose: value, source: 'Standard Template' });
        } else {
          flat.push(...flattenHeadings(value, currentPath));
        }
      } else if (typeof value === 'string') {
        const currentPath = parentKey ? `${parentKey} > ${key}` : key;
        flat.push({ id: `std-${flat.length}`, heading: currentPath, purpose: value, source: 'Standard Template' });
      }
    }
    return flat;
  };

  const toggleStandardHeading = (headingId) => {
    setSelectedStandardHeadings(prev => 
      prev.includes(headingId)
        ? prev.filter(id => id !== headingId)
        : [...prev, headingId]
    );
  };

  const addCustomHeading = () => {
    if (!newHeading.title.trim() || !newHeading.purpose.trim()) {
      toast.error('Please enter both title and purpose');
      return;
    }

    const customHeading = {
      id: `custom-${Date.now()}`,
      heading: newHeading.title,
      purpose: newHeading.purpose,
      source: 'Custom Added'
    };

    setStandardHeadings(prev => [...prev, customHeading]);
    setNewHeading({ title: '', purpose: '' });
    setShowAddHeading(false);
    toast.success('Custom heading added!');
  };

  const removeHeading = (headingId) => {
    setStandardHeadings(prev => prev.filter(h => h.id !== headingId));
    setSelectedStandardHeadings(prev => prev.filter(id => id !== headingId));
    toast.success('Heading removed!');
  };

  const generateContentForSelected = async () => {
    const allSelected = selectedStandardHeadings.map(id => standardHeadings.find(h => h.id === id)).filter(Boolean);

    if (allSelected.length === 0) {
      toast.error('Please select at least one heading');
      return;
    }

    try {
      setGeneratingContent(true);
      
      // Call backend API to generate content
      toast.loading('Generating content...');
      const response = await srsApi.generateContent(allSelected);
      toast.dismiss();
      
      if (response.success && response.generated_content) {
        toast.success(`Generated content for ${response.total_sections} headings!`);
        
        navigate('/content-editor', {
          state: {
            projectTitle,
            projectDescription,
            selectedHeadings: allSelected,
            generatedContent: response.generated_content
          }
        });
      } else {
        toast.error('Failed to generate content');
      }
    } catch (error) {
      console.error('Error generating content:', error);
      toast.error('Failed to generate content');
    } finally {
      setGeneratingContent(false);
    }
  };

  const selectAllStandard = () => {
    if (selectedStandardHeadings.length === standardHeadings.length) {
      setSelectedStandardHeadings([]);
    } else {
      setSelectedStandardHeadings(standardHeadings.map(h => h.id));
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/editor')}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors duration-200"
              >
                <ArrowLeft className="w-5 h-5 text-gray-600" />
              </button>
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                  <FileText className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-gray-900">Heading Selection</h1>
                  <p className="text-sm text-gray-600">Select headings for content generation</p>
                </div>
              </div>
            </div>
            
            <div className="flex gap-3">
              <button
                onClick={() => setShowAddHeading(true)}
                className="btn-outline flex items-center space-x-2"
              >
                <Plus className="w-4 h-4" />
                <span>Add Heading</span>
              </button>
              
              <button
                onClick={generateContentForSelected}
                disabled={generatingContent || selectedStandardHeadings.length === 0}
                className="btn-primary bg-green-600 hover:bg-green-700 flex items-center space-x-2"
              >
                <Sparkles className="w-4 h-4" />
                <span>{generatingContent ? 'Generating...' : 'Generate Content'}</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Project Info */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            {projectTitle || 'Untitled Project'}
          </h2>
          {projectDescription && (
            <p className="text-gray-600">{projectDescription}</p>
          )}
        </div>

        {/* Headings Section */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              SRS Headings ({standardHeadings.length})
            </h3>
            <button
              onClick={selectAllStandard}
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              {selectedStandardHeadings.length === standardHeadings.length ? 'Deselect All' : 'Select All'}
            </button>
          </div>
          
          {loading ? (
            <div className="text-center py-8">
              <div className="spinner mx-auto mb-4"></div>
              <p className="text-gray-600">Loading headings...</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {standardHeadings.map((heading) => (
                <div
                  key={heading.id}
                  className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <button
                    onClick={() => toggleStandardHeading(heading.id)}
                    className="mt-1"
                  >
                    {selectedStandardHeadings.includes(heading.id) ? (
                      <CheckSquare className="w-5 h-5 text-primary-600" />
                    ) : (
                      <Square className="w-5 h-5 text-gray-400" />
                    )}
                  </button>
                  
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900 text-sm">
                      {heading.heading}
                    </h4>
                    <p className="text-xs text-gray-600 mt-1">
                      {heading.purpose}
                    </p>
                    <span className="text-xs text-blue-600 mt-1 block">
                      {heading.source}
                    </span>
                  </div>
                  
                  {heading.source === 'Custom Added' && (
                    <button
                      onClick={() => removeHeading(heading.id)}
                      className="p-1 hover:bg-red-100 rounded transition-colors"
                      title="Remove heading"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Selection Summary */}
        <div className="mt-8 card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Selection Summary
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-sm text-blue-600">Headings Selected</p>
              <p className="text-2xl font-bold text-blue-900">{selectedStandardHeadings.length}</p>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <p className="text-sm text-purple-600">Total Available</p>
              <p className="text-2xl font-bold text-purple-900">{standardHeadings.length}</p>
            </div>
          </div>
        </div>
      </main>

      {/* Add Heading Modal */}
      {showAddHeading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Add Custom Heading
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Heading Title *
                </label>
                <input
                  type="text"
                  value={newHeading.title}
                  onChange={(e) => setNewHeading(prev => ({ ...prev, title: e.target.value }))}
                  className="input-field"
                  placeholder="Enter heading title"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Purpose *
                </label>
                <textarea
                  value={newHeading.purpose}
                  onChange={(e) => setNewHeading(prev => ({ ...prev, purpose: e.target.value }))}
                  className="input-field"
                  placeholder="Enter the purpose of this heading"
                  rows="3"
                />
              </div>
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowAddHeading(false)}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                onClick={addCustomHeading}
                className="btn-primary flex-1"
              >
                Add Heading
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Comparison; 