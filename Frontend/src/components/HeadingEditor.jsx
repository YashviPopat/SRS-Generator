import React, { useState, useEffect } from 'react';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { Plus, Trash2, Edit3, Eye, Download, Sparkles, Save } from 'lucide-react';
import toast from 'react-hot-toast';
import { srsApi, errorHandler } from '../api/srsApi';

const HeadingEditor = ({ projectTitle, projectDescription, uploadedFiles }) => {
  const [headings, setHeadings] = useState([]);
  const [suggestedHeadings, setSuggestedHeadings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [editingHeading, setEditingHeading] = useState(null);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Load standard headings on component mount
  useEffect(() => {
    loadStandardHeadings();
  }, []);

  const loadStandardHeadings = async () => {
    try {
      setLoading(true);
      const response = await srsApi.getStandardHeadings();
      
      // Convert to flat list of headings
      const flatHeadings = flattenHeadings(response.headings);
      
      // Set initial headings (first 10 standard headings)
      setHeadings(flatHeadings.slice(0, 10).map((heading, index) => ({
        id: `heading-${index}`,
        heading: heading.heading,
        purpose: heading.purpose,
        isStandard: true,
        isCustom: false
      })));
      
      toast.success('Standard headings loaded successfully!');
    } catch (error) {
      console.error('Error loading headings:', error);
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
          flat.push({ heading: currentPath, purpose: value });
        } else {
          flat.push(...flattenHeadings(value, currentPath));
        }
      } else if (typeof value === 'string') {
        const currentPath = parentKey ? `${parentKey} > ${key}` : key;
        flat.push({ heading: currentPath, purpose: value });
      }
    }
    return flat;
  };

  const getHeadingSuggestions = async () => {
    try {
      setSuggestionsLoading(true);
      
      // Get document IDs from uploaded files
      const documentIds = uploadedFiles
        .filter(file => file.documentId)
        .map(file => file.documentId);

      const response = await srsApi.getHeadingSuggestions(
        headings.map(h => ({ heading: h.heading, purpose: h.purpose })),
        projectDescription,
        documentIds
      );

      setSuggestedHeadings([
        ...response.suggested_headings,
        ...response.missing_standard_headings
      ]);
      
      setShowSuggestions(true);
      toast.success(`Found ${response.suggested_headings.length + response.missing_standard_headings.length} suggestions!`);
    } catch (error) {
      console.error('Error getting suggestions:', error);
      toast.error(errorHandler.handleApiError(error));
    } finally {
      setSuggestionsLoading(false);
    }
  };

  const handleDragEnd = (result) => {
    if (!result.destination) return;

    const items = Array.from(headings);
    const [reorderedItem] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reorderedItem);

    setHeadings(items);
  };

  const addHeading = () => {
    const newHeading = {
      id: `heading-${Date.now()}`,
      heading: 'New Heading',
      purpose: 'Enter the purpose of this heading',
      isStandard: false,
      isCustom: true
    };
    setHeadings([...headings, newHeading]);
    setEditingHeading(newHeading.id);
  };

  const updateHeading = (id, field, value) => {
    setHeadings(prev => 
      prev.map(heading => 
        heading.id === id 
          ? { ...heading, [field]: value }
          : heading
      )
    );
  };

  const deleteHeading = (id) => {
    setHeadings(prev => prev.filter(heading => heading.id !== id));
    toast.success('Heading removed');
  };

  const addSuggestion = (suggestion) => {
    const newHeading = {
      id: `heading-${Date.now()}`,
      heading: suggestion.heading,
      purpose: suggestion.purpose,
      isStandard: suggestion.is_standard || false,
      isCustom: false
    };
    setHeadings([...headings, newHeading]);
    toast.success(`Added: ${suggestion.heading}`);
  };

  const generateSRS = async () => {
    try {
      setLoading(true);
      
      const response = await srsApi.buildSrsStructure(
        headings.map(h => ({ heading: h.heading, purpose: h.purpose })),
        projectTitle,
        projectDescription,
        true
      );

      toast.success(`SRS structure created with ${response.total_sections} sections!`);
      
      // Generate DOCX
      const docxResponse = await srsApi.generateDocx(response.structure_id, true);
      
      // Download the file
      const blob = await srsApi.downloadFile(docxResponse.file_id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = docxResponse.file_name;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success('SRS document downloaded successfully!');
    } catch (error) {
      console.error('Error generating SRS:', error);
      toast.error(errorHandler.handleApiError(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex flex-wrap gap-4 items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">SRS Structure Editor</h2>
          <p className="text-gray-600">Organize and customize your SRS headings</p>
        </div>
        
        <div className="flex gap-3">
          <button
            onClick={getHeadingSuggestions}
            disabled={suggestionsLoading}
            className="btn-outline flex items-center space-x-2"
          >
            <Sparkles className="w-4 h-4" />
            <span>{suggestionsLoading ? 'Getting Suggestions...' : 'Get AI Suggestions'}</span>
          </button>
          
          <button
            onClick={addHeading}
            className="btn-primary flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Add Heading</span>
          </button>
          
          <button
            onClick={generateSRS}
            disabled={loading || headings.length === 0}
            className="btn-primary bg-green-600 hover:bg-green-700 flex items-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>{loading ? 'Generating...' : 'Generate SRS'}</span>
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Headings List */}
        <div className="lg:col-span-2">
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              SRS Headings ({headings.length})
            </h3>
            
            {loading ? (
              <div className="text-center py-8">
                <div className="spinner mx-auto mb-4"></div>
                <p className="text-gray-600">Loading headings...</p>
              </div>
            ) : headings.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-600 mb-4">No headings yet. Add some to get started!</p>
                <button onClick={addHeading} className="btn-primary">
                  Add Your First Heading
                </button>
              </div>
            ) : (
              <DragDropContext onDragEnd={handleDragEnd}>
                <Droppable droppableId="headings">
                  {(provided) => (
                    <div
                      {...provided.droppableProps}
                      ref={provided.innerRef}
                      className="space-y-3"
                    >
                      {headings.map((heading, index) => (
                        <Draggable key={heading.id} draggableId={heading.id} index={index}>
                          {(provided) => (
                            <div
                              ref={provided.innerRef}
                              {...provided.draggableProps}
                              {...provided.dragHandleProps}
                              className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
                            >
                              <div className="flex-1">
                                {editingHeading === heading.id ? (
                                  <div className="space-y-2">
                                    <input
                                      type="text"
                                      value={heading.heading}
                                      onChange={(e) => updateHeading(heading.id, 'heading', e.target.value)}
                                      className="input-field text-sm"
                                      placeholder="Heading title"
                                    />
                                    <textarea
                                      value={heading.purpose}
                                      onChange={(e) => updateHeading(heading.id, 'purpose', e.target.value)}
                                      className="input-field text-sm"
                                      placeholder="Purpose description"
                                      rows="2"
                                    />
                                    <div className="flex gap-2">
                                      <button
                                        onClick={() => setEditingHeading(null)}
                                        className="btn-secondary text-xs px-2 py-1"
                                      >
                                        Save
                                      </button>
                                      <button
                                        onClick={() => deleteHeading(heading.id)}
                                        className="btn-outline text-xs px-2 py-1 text-red-600 border-red-600 hover:bg-red-50"
                                      >
                                        Delete
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  <div>
                                    <h4 className="font-medium text-gray-900">{heading.heading}</h4>
                                    <p className="text-sm text-gray-600 mt-1">{heading.purpose}</p>
                                    <div className="flex items-center gap-2 mt-2">
                                      {heading.isStandard && (
                                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                                          Standard
                                        </span>
                                      )}
                                      {heading.isCustom && (
                                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                                          Custom
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                )}
                              </div>
                              
                              {editingHeading !== heading.id && (
                                <div className="flex items-center gap-2 ml-4">
                                  <button
                                    onClick={() => setEditingHeading(heading.id)}
                                    className="p-1 hover:bg-gray-200 rounded transition-colors"
                                    title="Edit heading"
                                  >
                                    <Edit3 className="w-4 h-4 text-gray-500" />
                                  </button>
                                  <button
                                    onClick={() => deleteHeading(heading.id)}
                                    className="p-1 hover:bg-red-100 rounded transition-colors"
                                    title="Delete heading"
                                  >
                                    <Trash2 className="w-4 h-4 text-red-500" />
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
              </DragDropContext>
            )}
          </div>
        </div>

        {/* Suggestions Panel */}
        <div className="lg:col-span-1">
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                AI Suggestions
              </h3>
              <button
                onClick={() => setShowSuggestions(!showSuggestions)}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
              >
                <Eye className="w-4 h-4 text-gray-500" />
              </button>
            </div>
            
            {showSuggestions ? (
              <div className="space-y-3">
                {suggestedHeadings.map((suggestion, index) => (
                  <div
                    key={index}
                    className="p-3 bg-blue-50 border border-blue-200 rounded-lg"
                  >
                    <h4 className="font-medium text-blue-900 text-sm">
                      {suggestion.heading}
                    </h4>
                    <p className="text-xs text-blue-800 mt-1 mb-2">
                      {suggestion.purpose}
                    </p>
                    <button
                      onClick={() => addSuggestion(suggestion)}
                      className="btn-primary text-xs px-2 py-1 w-full"
                    >
                      Add to SRS
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Sparkles className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-600 text-sm">
                  Click "Get AI Suggestions" to see recommended headings based on your documents.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HeadingEditor; 