import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { CheckCircleIcon, PlusIcon, DocumentTextIcon, SparklesIcon, ArrowRightIcon, PencilIcon } from '@heroicons/react/24/outline';
import UploadArea from '../components/UploadArea';
import DiagramEditor from '../components/DiagramEditor';
import { useDocumentData } from '../DocumentDataContext';
import { srsApi, errorHandler } from '../api/srsApi';
import { useNavigate } from 'react-router-dom';

const SRSGenerator = () => {
  const { documentData, setDocumentData } = useDocumentData();
  const navigate = useNavigate();
  const [standardHeadings, setStandardHeadings] = useState({});
  const [selectedStandardHeadings, setSelectedStandardHeadings] = useState({});
  const [customSections, setCustomSections] = useState([]);
  const [newSection, setNewSection] = useState({ title: '', purpose: '' });
  const [loading, setLoading] = useState(true);
  const [generatingAIHeadings, setGeneratingAIHeadings] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState(documentData.uploadedFiles || []);
  const [processingFiles, setProcessingFiles] = useState(false);
  const [filesProcessed, setFilesProcessed] = useState(false);
  const [aiGeneratedHeadings, setAiGeneratedHeadings] = useState({});
  const [selectedAiHeadings, setSelectedAiHeadings] = useState({});

  // Diagram Editor State
  const [showDiagramEditor, setShowDiagramEditor] = useState(false);
  const [currentDiagramData, setCurrentDiagramData] = useState(null);
  const [customSectionDiagrams, setCustomSectionDiagrams] = useState({});

  useEffect(() => {
    loadHeadings();
  }, []);

  // Separate useEffect for state restoration to avoid infinite loops
  useEffect(() => {
    // Restore state from documentData if available
    if (documentData.selectedStandardHeadings && Object.keys(selectedStandardHeadings).length === 0) {
      setSelectedStandardHeadings(documentData.selectedStandardHeadings);
    }
    if (documentData.customSections && customSections.length === 0) {
      setCustomSections(documentData.customSections);
    }
    if (documentData.aiGeneratedHeadings && Object.keys(aiGeneratedHeadings).length === 0) {
      setAiGeneratedHeadings(documentData.aiGeneratedHeadings);
    }
    if (documentData.selectedAiHeadings && Object.keys(selectedAiHeadings).length === 0) {
      setSelectedAiHeadings(documentData.selectedAiHeadings);
    }
    if (documentData.filesProcessed && !filesProcessed) {
      setFilesProcessed(documentData.filesProcessed);
    }
  }, [documentData.selectedStandardHeadings, documentData.customSections, documentData.aiGeneratedHeadings, documentData.selectedAiHeadings, documentData.filesProcessed]);

  const loadHeadings = async () => {
    try {
      setLoading(true);
      
      console.log('Loading standard headings...');
      
      // Load standard headings
      const standardResponse = await fetch('/standard-headings');
      console.log('Standard headings response:', standardResponse.status);
      if (standardResponse.ok) {
        const standardData = await standardResponse.json();
        console.log('Standard headings data:', standardData);
        setStandardHeadings(standardData.headings || standardData);
      } else {
        console.error('Failed to load standard headings:', standardResponse.status);
      }
      
    } catch (error) {
      console.error('Error loading headings:', error);
      toast.error('Failed to load headings');
    } finally {
      setLoading(false);
    }
  };

  const processAllFiles = async () => {
    if (uploadedFiles.length === 0) {
      toast.error('Please upload at least one file first');
      return;
    }

    try {
      setProcessingFiles(true);
      
      // Get the actual File objects from uploaded files
      const fileObjects = uploadedFiles.map(fileData => fileData.file);

      console.log('Processing files:', uploadedFiles.map(f => f.name));
      
      const response = await srsApi.processAllFiles(fileObjects);
      
      if (response.success) {
        // Update DocumentDataContext with all the data
        setDocumentData(prev => ({
          ...prev,
          geminiSuggestions: response.gemini_suggestions || {},
          uploadedFiles: prev.uploadedFiles.map(file => ({
            ...file,
            processed: true
          }))
        }));
        
        // Mark files as processed in local state
        setUploadedFiles(prev => prev.map(file => ({
          ...file,
          processed: true
        })));
        
                 setFilesProcessed(true);
         
         // Save to documentData
         setDocumentData(prev => ({
           ...prev,
           filesProcessed: true
         }));
         
         toast.success(`Successfully processed ${response.processed_files?.length || uploadedFiles.length} files!`);
        console.log('Processing results:', response);
      } else {
        throw new Error(response.message || 'Failed to process files');
      }
      
    } catch (error) {
      console.error('Error processing files:', error);
      toast.error(errorHandler.handleApiError(error));
    } finally {
      setProcessingFiles(false);
    }
  };

  const handleStandardHeadingToggle = (category, heading) => {
    setSelectedStandardHeadings(prev => {
      const newState = {
        ...prev,
        [category]: {
          ...prev[category],
          [heading]: !prev[category]?.[heading]
        }
      };
      
      // Save to documentData
      setDocumentData(prevData => ({
        ...prevData,
        selectedStandardHeadings: newState
      }));
      
      return newState;
    });
  };

  const addCustomSection = () => {
    if (!newSection.title.trim() || !newSection.purpose.trim()) {
      toast.error('Please fill in both title and purpose');
      return;
    }

    setCustomSections(prev => {
      const newSections = [...prev, { ...newSection, id: Date.now(), selected: true }];
      
      // Save to documentData
      setDocumentData(prevData => ({
        ...prevData,
        customSections: newSections
      }));
      
      return newSections;
    });
    setNewSection({ title: '', purpose: '' });
    toast.success('Custom section added');
  };

  const removeCustomSection = (id) => {
    setCustomSections(prev => {
      const newSections = prev.filter(section => section.id !== id);
      
      // Save to documentData
      setDocumentData(prevData => ({
        ...prevData,
        customSections: newSections
      }));
      
      return newSections;
    });
    toast.success('Custom section removed');
  };

  // Diagram Editor Functions
  const openDiagramEditor = (sectionId, sectionTitle, existingDiagram = null) => {
    const diagramType = detectDiagramType(sectionTitle);
    const initialCode = existingDiagram?.mermaidCode || generateInitialDiagramCode(diagramType, sectionTitle);

    setCurrentDiagramData({
      sectionId,
      sectionTitle,
      diagramType,
      initialCode,
      existingDiagram
    });
    setShowDiagramEditor(true);
  };

  const detectDiagramType = (title) => {
    const titleLower = title.toLowerCase();
    if (titleLower.includes('sequence') || titleLower.includes('flow') || titleLower.includes('workflow')) {
      return 'sequence';
    } else if (titleLower.includes('er') || titleLower.includes('database') || titleLower.includes('schema')) {
      return 'er';
    } else if (titleLower.includes('class') || titleLower.includes('object')) {
      return 'class';
    } else {
      return 'flowchart';
    }
  };

  const generateInitialDiagramCode = (type, title) => {
    const templates = {
      flowchart: `flowchart TD
    A[Start] --> B{Process}
    B -->|Success| C[Complete]
    B -->|Error| D[Handle Error]
    C --> E[End]
    D --> E`,
      sequence: `sequenceDiagram
    participant User
    participant System
    participant Database

    User->>System: Request
    System->>Database: Query
    Database-->>System: Data
    System-->>User: Response`,
      er: `erDiagram
    USER {
        int id PK
        string name
        string email
    }
    ORDER {
        int id PK
        int user_id FK
        date created_at
    }
    USER ||--o{ ORDER : places`,
      class: `classDiagram
    class User {
        +String name
        +String email
        +login()
        +logout()
    }
    class System {
        +processRequest()
        +sendResponse()
    }`
    };

    return templates[type] || templates.flowchart;
  };

  const saveDiagram = (diagramData) => {
    const { sectionId, sectionTitle } = currentDiagramData;

    // Save diagram to custom section diagrams
    setCustomSectionDiagrams(prev => ({
      ...prev,
      [sectionId]: {
        ...diagramData,
        sectionTitle,
        lastModified: new Date().toISOString()
      }
    }));

    // Update the custom section to indicate it has a diagram
    setCustomSections(prev => prev.map(section =>
      section.id === sectionId
        ? { ...section, hasDiagram: true, diagramType: diagramData.diagramType }
        : section
    ));

    setShowDiagramEditor(false);
    setCurrentDiagramData(null);
    toast.success('Diagram saved successfully!');
  };

  const removeDiagram = (sectionId) => {
    setCustomSectionDiagrams(prev => {
      const newDiagrams = { ...prev };
      delete newDiagrams[sectionId];
      return newDiagrams;
    });

    setCustomSections(prev => prev.map(section =>
      section.id === sectionId
        ? { ...section, hasDiagram: false, diagramType: null }
        : section
    ));

    toast.success('Diagram removed');
  };

  const handleAiHeadingToggle = (path) => {
    setSelectedAiHeadings(prev => {
      const newState = { ...prev, [path]: !prev[path] };
      
      // Save to documentData
      setDocumentData(prevData => ({
        ...prevData,
        selectedAiHeadings: newState
      }));
      
      return newState;
    });
  };

  const generateAIHeadings = async () => {
    if (uploadedFiles.length === 0) {
      toast.error('Please upload meeting summary files first');
      return;
    }

    if (!filesProcessed) {
      toast.error('Please process the uploaded files first');
      return;
    }

    try {
      setGeneratingAIHeadings(true);
      
      toast.loading('Generating AI headings and comparing with standard headings...');
      
      // Call backend to generate AI headings and compare with standard headings
      const response = await fetch('/generate-ai-headings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          standardHeadings: standardHeadings,
          uploadedFiles: documentData.uploadedFiles || []
        }),
      });

      if (response.ok) {
        const data = await response.json();
        toast.dismiss();
        
                 if (data.success) {
           toast.success(`Generated ${data.uniqueHeadings?.length || 0} unique AI headings!`);
           
           // Convert the unique headings to the format expected by the UI
           const aiHeadingsObject = {};
           data.uniqueHeadings.forEach(heading => {
             aiHeadingsObject[heading.heading] = heading.purpose;
           });
           
           console.log('=== AI HEADING GENERATION DEBUG ===');
           console.log('data.uniqueHeadings:', data.uniqueHeadings);
           console.log('aiHeadingsObject:', aiHeadingsObject);
           
           setAiGeneratedHeadings(aiHeadingsObject);
            
            // Auto-select all AI headings
            const allSelected = {};
            data.uniqueHeadings.forEach(heading => {
              allSelected[heading.heading] = true;
            });
            console.log('allSelected:', allSelected);
            setSelectedAiHeadings(allSelected);
            
            // Save to documentData
            setDocumentData(prevData => ({
              ...prevData,
              aiGeneratedHeadings: aiHeadingsObject,
              selectedAiHeadings: allSelected
            }));
            
            console.log('=== END AI HEADING DEBUG ===');
        } else {
          toast.error(data.message || 'Failed to generate AI headings');
        }
      } else {
        throw new Error('Failed to generate AI headings');
      }
    } catch (error) {
      console.error('Error generating AI headings:', error);
      toast.error('Failed to generate AI headings');
    } finally {
      setGeneratingAIHeadings(false);
    }
  };

  const navigateToTemplate = () => {
    // Convert selected AI headings to the format expected by Template page
    const selectedAiHeadingsArray = Object.entries(selectedAiHeadings)
      .filter(([path, selected]) => selected)
      .map(([path, selected]) => {
        // For AI headings, the path is the heading itself (no nested structure)
        const heading = path;
        const purpose = aiGeneratedHeadings[heading] || 'AI Generated';
        return {
          heading,
          purpose,
          category: 'AI',
          source: 'AI Generated'
        };
      });

    console.log('=== NAVIGATION DEBUG ===');
    console.log('selectedAiHeadings:', selectedAiHeadings);
    console.log('aiGeneratedHeadings:', aiGeneratedHeadings);
    console.log('selectedAiHeadingsArray:', selectedAiHeadingsArray);
    console.log('selectedAiHeadings entries:', Object.entries(selectedAiHeadings));
    console.log('Filtered entries:', Object.entries(selectedAiHeadings).filter(([path, selected]) => selected));
    console.log('=== END DEBUG ===');

    console.log('Navigating to template with:', {
      standardHeadings: selectedStandardHeadings,
      customSections: customSections,
      aiHeadings: selectedAiHeadingsArray,
      selectedAiHeadings: selectedAiHeadings,
      aiGeneratedHeadings: aiGeneratedHeadings
    });

    navigate('/template', {
      state: {
        standardHeadings: selectedStandardHeadings,
        customSections: customSections,
        aiHeadings: selectedAiHeadingsArray,
        customSectionDiagrams: customSectionDiagrams,
        projectTitle: documentData.projectTitle,
        projectDescription: documentData.projectDescription
      }
    });
  };

  const renderAiHeadings = (data, selected, onToggle, parentPath = '') => {
    return Object.entries(data).map(([heading, purpose]) => {
      const path = parentPath ? `${parentPath} > ${heading}` : heading;
      
      if (typeof purpose === 'object' && purpose !== null) {
        // This is a nested category, render it recursively
        return (
          <div key={heading} className="mb-4">
            <h4 className="text-md font-medium text-gray-600 mb-2 border-l-4 border-purple-200 pl-3">
              {heading}
            </h4>
            <div className="ml-4 space-y-2">
              {renderAiHeadings(purpose, path)}
            </div>
          </div>
        );
      } else {
        // This is a leaf heading with a string purpose
        return (
          <div key={heading} className="flex items-start space-x-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50">
            <button
              onClick={() => onToggle(path)}
              className={`flex-shrink-0 mt-1 ${
                selected[path]
                  ? 'text-green-600'
                  : 'text-gray-400 hover:text-gray-600'
              }`}
            >
              <CheckCircleIcon className="w-5 h-5" />
            </button>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900">
                {heading}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {typeof purpose === 'string' ? purpose : String(purpose)}
              </div>
            </div>
          </div>
        );
      }
    });
  };

  const renderHeadingList = (headings, selectedHeadings, onToggle, title) => {
    const renderCategoryHeadings = (categoryHeadings, categoryPath = '') => {
      return Object.entries(categoryHeadings).map(([heading, purpose]) => {
        const fullHeadingPath = categoryPath ? `${categoryPath} > ${heading}` : heading;
        
        if (typeof purpose === 'object' && purpose !== null) {
          // This is a nested category, render it recursively
          return (
            <div key={heading} className="mb-4">
              <h4 className="text-md font-medium text-gray-600 mb-2 border-l-4 border-blue-200 pl-3">
                {heading}
              </h4>
              <div className="ml-4 space-y-2">
                {renderCategoryHeadings(purpose, fullHeadingPath)}
              </div>
            </div>
          );
        } else {
          // This is a leaf heading with a string purpose
          return (
            <div key={heading} className="flex items-start space-x-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50">
              <button
                onClick={() => onToggle(categoryPath || 'Other', heading)}
                className={`flex-shrink-0 mt-1 ${
                  selectedHeadings[categoryPath || 'Other']?.[heading]
                    ? 'text-green-600'
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                <CheckCircleIcon className="w-5 h-5" />
              </button>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900">
                  {heading}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {typeof purpose === 'string' ? purpose : String(purpose)}
                </div>
              </div>
            </div>
          );
        }
      });
    };

    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-full">
        <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
          <DocumentTextIcon className="w-5 h-5 mr-2" />
          {title}
        </h2>
        
        {Object.entries(headings).map(([category, categoryHeadings]) => (
          <div key={category} className="mb-6">
            <h3 className="text-lg font-medium text-gray-700 mb-3 border-b border-gray-200 pb-2">
              {category}
            </h3>
            <div className="space-y-2">
              {renderCategoryHeadings(categoryHeadings, category)}
            </div>
          </div>
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading headings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            SRS Headings Generator
          </h1>
          <p className="text-gray-600">
            Select standard headings and upload meeting summaries to generate AI-powered heading suggestions.
          </p>
        </div>

        {/* File Upload Section */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
            <DocumentTextIcon className="w-5 h-5 mr-2" />
            Upload Meeting Summary PDFs
          </h2>
          <UploadArea
            onFilesUploaded={setUploadedFiles}
            uploadedFiles={uploadedFiles}
          />
          
          {/* Process Files Button */}
          {uploadedFiles.length > 0 && !filesProcessed && (
            <div className="mt-6 text-center">
              <button
                onClick={processAllFiles}
                disabled={processingFiles}
                className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center mx-auto"
              >
                {processingFiles ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    Processing Files...
                  </>
                ) : (
                  <>
                    <SparklesIcon className="w-5 h-5 mr-2" />
                    Process Files
                  </>
                )}
              </button>
              
              <p className="text-sm text-gray-500 mt-2">
                This will extract text from all uploaded files for AI processing
              </p>
            </div>
          )}
        </div>

        {/* Standard Headings Section */}
        <div className="mb-8">
          <div className="h-[600px] overflow-y-auto">
            {renderHeadingList(
              standardHeadings,
              selectedStandardHeadings,
              handleStandardHeadingToggle,
              'Standard SRS Headings'
            )}
          </div>
        </div>

        {/* Custom Sections */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
            <PlusIcon className="w-5 h-5 mr-2" />
            Custom Sections
          </h2>
          {/* Add New Section */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Section Title
              </label>
              <input
                type="text"
                value={newSection.title}
                onChange={(e) => setNewSection(prev => ({ ...prev, title: e.target.value }))}
                placeholder="Enter section title"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Purpose
              </label>
              <input
                type="text"
                value={newSection.purpose}
                onChange={(e) => setNewSection(prev => ({ ...prev, purpose: e.target.value }))}
                placeholder="Enter section purpose"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={addCustomSection}
                className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 flex items-center justify-center"
              >
                <PlusIcon className="w-4 h-4 mr-2" />
                Add Section
              </button>
            </div>
          </div>
          {/* Custom Sections List */}
          {customSections.length > 0 && (
            <div className="space-y-2">
              {customSections.map((section, idx) => (
                <div key={section.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      checked={section.selected !== false}
                      onChange={() => {
                        setCustomSections(prev => {
                          const newSections = prev.map((s, i) => i === idx ? { ...s, selected: !s.selected } : s);

                          // Save to documentData
                          setDocumentData(prevData => ({
                            ...prevData,
                            customSections: newSections
                          }));

                          return newSections;
                        });
                      }}
                      className="mr-3 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">{section.title}</div>
                      <div className="text-sm text-gray-500">{section.purpose}</div>
                      {section.hasDiagram && (
                        <div className="text-xs text-green-600 mt-1 flex items-center">
                          <CheckCircleIcon className="w-3 h-3 mr-1" />
                          {section.diagramType} diagram attached
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {/* Diagram Editor Button */}
                    <button
                      onClick={() => openDiagramEditor(
                        section.id,
                        section.title,
                        customSectionDiagrams[section.id]
                      )}
                      className="p-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-full transition-colors"
                      title={section.hasDiagram ? "Edit diagram" : "Add diagram"}
                    >
                      <PencilIcon className="w-4 h-4" />
                    </button>

                    {/* Remove Diagram Button */}
                    {section.hasDiagram && (
                      <button
                        onClick={() => removeDiagram(section.id)}
                        className="p-2 text-orange-600 hover:text-orange-800 hover:bg-orange-50 rounded-full transition-colors"
                        title="Remove diagram"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    )}

                    {/* Remove Section Button */}
                    <button
                      onClick={() => removeCustomSection(section.id)}
                      className="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-full transition-colors"
                      title="Remove section"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
                    )}
        </div>

        {/* AI Generated Headings Section */}
        {Object.keys(aiGeneratedHeadings).length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
              <SparklesIcon className="w-5 h-5 mr-2" />
              AI Generated Headings
            </h2>
            <div className="h-[400px] overflow-y-auto">
              {renderAiHeadings(
                aiGeneratedHeadings,
                selectedAiHeadings,
                handleAiHeadingToggle,
                'AI Generated Headings'
              )}
            </div>
          </div>
        )}

                                    {/* Action Buttons */}
          <div className="text-center mb-8 space-y-4">
                         {/* Generate AI Headings Button */}
             <div>
               <button
                 onClick={generateAIHeadings}
                 disabled={generatingAIHeadings || !filesProcessed || uploadedFiles.length === 0}
                 className="bg-blue-600 text-white px-8 py-4 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center mx-auto space-x-2 text-lg font-medium"
               >
                 {generatingAIHeadings ? (
                   <>
                     <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                     <span>Generating AI Headings...</span>
                   </>
                 ) : (
                   <>
                     <SparklesIcon className="w-5 h-5" />
                     <span>Generate AI Headings</span>
                   </>
                 )}
               </button>
               
               <p className="text-sm text-gray-500 mt-2">
                 {filesProcessed ? 
                   "Generate AI headings from your meeting summaries" : 
                   "Please process your files first to generate AI headings"
                 }
               </p>
             </div>

             {/* Continue to Template Button */}
             {(() => {
               const hasSelectedStandard = Object.values(selectedStandardHeadings).some(category => 
                 Object.values(category).some(selected => selected)
               );
               const hasSelectedCustom = customSections.some(section => section.selected !== false);
               const hasAIHeadings = Object.keys(aiGeneratedHeadings).length > 0;
               const hasSelectedAI = Object.values(selectedAiHeadings).some(selected => selected);
               
               console.log('Button condition check:', {
                 hasSelectedStandard,
                 hasSelectedCustom,
                 hasAIHeadings,
                 hasSelectedAI,
                 selectedAiHeadings,
                 aiGeneratedHeadings
               });
               
               return (hasSelectedStandard || hasSelectedCustom || hasAIHeadings || hasSelectedAI) ? (
                 <div>
                   <button
                     onClick={navigateToTemplate}
                     className="bg-green-600 text-white px-8 py-4 rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 flex items-center mx-auto space-x-2 text-lg font-medium"
                   >
                     <ArrowRightIcon className="w-5 h-5" />
                     <span>Continue to SRS Template</span>
                   </button>
                   
                   <p className="text-sm text-gray-500 mt-2">
                     Review and finalize your selected headings
                   </p>
                 </div>
               ) : (
                 <div className="text-sm text-gray-500 mt-2">
                   Please select at least one heading to continue
                 </div>
               );
                           })()}
            
                                      {/* Debug Button */}
              <div className="mt-2">
                <button
                  onClick={() => {
                    console.log('=== DEBUG CURRENT STATE ===');
                    console.log('aiGeneratedHeadings:', aiGeneratedHeadings);
                    console.log('selectedAiHeadings:', selectedAiHeadings);
                    console.log('Object.keys(aiGeneratedHeadings):', Object.keys(aiGeneratedHeadings));
                    console.log('Object.entries(selectedAiHeadings):', Object.entries(selectedAiHeadings));
                    console.log('=== END DEBUG ===');
                  }}
                  className="bg-yellow-600 text-white px-4 py-1 rounded text-xs"
                >
                  Debug AI State
                </button>
              </div>

              {/* Test Navigation Button */}
              <div className="mt-4">
                <button
                  onClick={() => {
                    console.log('Navigating to template page...');
                    // Get any existing AI headings from documentData
                    const existingAIHeadings = documentData.geminiSuggestions ? 
                      Object.entries(documentData.geminiSuggestions).map(([heading, purpose]) => ({
                        heading,
                        purpose: typeof purpose === 'string' ? purpose : 'AI Generated',
                        category: 'AI'
                      })) : [];
                    
                    // Also test with current AI headings
                    const currentAIHeadings = Object.entries(aiGeneratedHeadings).map(([heading, purpose]) => ({
                      heading,
                      purpose: typeof purpose === 'string' ? purpose : 'AI Generated',
                      category: 'AI',
                      source: 'AI Generated'
                    }));
                    
                    console.log('Test navigation - existingAIHeadings:', existingAIHeadings);
                    console.log('Test navigation - currentAIHeadings:', currentAIHeadings);
                    
                    navigate('/template', {
                      state: {
                        standardHeadings: selectedStandardHeadings,
                        customSections: customSections,
                        aiHeadings: currentAIHeadings.length > 0 ? currentAIHeadings : existingAIHeadings, // Use current AI headings if available
                        projectTitle: 'Test Project',
                        projectDescription: 'Test Description'
                      }
                    });
                  }}
                  className="bg-gray-600 text-white px-6 py-2 rounded-lg hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 text-sm"
                >
                  Test Template Page
                </button>
              </div>
          </div>
      </div>

      {/* Diagram Editor Modal */}
      {showDiagramEditor && currentDiagramData && (
        <DiagramEditor
          initialMermaidCode={currentDiagramData.initialCode}
          diagramType={currentDiagramData.diagramType}
          onSave={saveDiagram}
          onClose={() => {
            setShowDiagramEditor(false);
            setCurrentDiagramData(null);
          }}
        />
      )}
    </div>
  );
};

export default SRSGenerator; 