import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { 
  PlusIcon, 
  DocumentTextIcon, 
  SparklesIcon,
  ArrowLeftIcon,
  ArrowDownTrayIcon
} from '@heroicons/react/24/outline';
import { useDocumentData } from '../DocumentDataContext';
import { srsApi, errorHandler } from '../api/srsApi';
import DiagramManager from '../components/DiagramManager';

const SRSHeadingsEditor = () => {
  const navigate = useNavigate();
  const { documentData, setDocumentData } = useDocumentData();
  const [loading, setLoading] = useState(true);
  const [processingFiles, setProcessingFiles] = useState(false);
  const [generatingSRS, setGeneratingSRS] = useState(false);
  const [generatedDocumentId, setGeneratedDocumentId] = useState(null);
  const [showDiagramManager, setShowDiagramManager] = useState(false);
  
  // State for different types of headings
  const [aiGeneratedHeadings, setAiGeneratedHeadings] = useState(documentData.aiGeneratedHeadings || {});
  const [standardHeadings, setStandardHeadings] = useState({});
  const [customSections, setCustomSections] = useState(documentData.customSections || []);
  
  // State for selections - use context state with fallback to local state
  const [selectedAiHeadings, setSelectedAiHeadings] = useState(documentData.selectedAiHeadings || {});
  const [selectedStandardHeadings, setSelectedStandardHeadings] = useState(documentData.selectedStandardHeadings || {});
  
  // State for new custom section
  const [newSection, setNewSection] = useState({ title: '', purpose: '', userPrompt: '' });

  // State for managing subheadings
  const [showSubheadings, setShowSubheadings] = useState({});
  const [newSubheading, setNewSubheading] = useState({});

  // State for OpenAI processing
  const [generatingOpenAIHeadings, setGeneratingOpenAIHeadings] = useState(false);
  const [userPrompt, setUserPrompt] = useState('');

  // Add state to track custom prompts for each heading
  const [headingCustomPrompts, setHeadingCustomPrompts] = useState({});
  const [showPromptBox, setShowPromptBox] = useState({});



  // Helper function to toggle custom prompt box visibility
  const togglePromptBox = (headingKey) => {
    setShowPromptBox(prev => ({
      ...prev,
      [headingKey]: !prev[headingKey]
    }));
  };

  // Helper function to update custom prompt for a heading
  const updateCustomPrompt = (headingKey, prompt) => {
    setHeadingCustomPrompts(prev => ({
      ...prev,
      [headingKey]: prompt
    }));
  };



  // Helper functions for managing subheadings
  const toggleSubheadingView = (sectionId) => {
    setShowSubheadings(prev => ({
      ...prev,
      [sectionId]: !prev[sectionId]
    }));
  };

  const addSubheading = (sectionId) => {
    const subheadingData = newSubheading[sectionId];
    if (!subheadingData?.title?.trim() || !subheadingData?.purpose?.trim()) {
      toast.error('Please fill in both subheading title and purpose');
      return;
    }

    const updatedSections = customSections.map(section => {
      if (section.id === sectionId) {
        const subheadings = section.subheadings || [];
        return {
          ...section,
          subheadings: [...subheadings, {
            id: Date.now(),
            title: subheadingData.title.trim(),
            purpose: subheadingData.purpose.trim(),
            selected: true
          }]
        };
      }
      return section;
    });

    setCustomSections(updatedSections);

    // Update context state
    setDocumentData(prev => ({
      ...prev,
      customSections: updatedSections
    }));

    // Clear the input for this section
    setNewSubheading(prev => ({
      ...prev,
      [sectionId]: { title: '', purpose: '' }
    }));

    toast.success('Subheading added successfully');
  };

  const removeSubheading = (sectionId, subheadingId) => {
    const updatedSections = customSections.map(section => {
      if (section.id === sectionId) {
        return {
          ...section,
          subheadings: (section.subheadings || []).filter(sub => sub.id !== subheadingId)
        };
      }
      return section;
    });

    setCustomSections(updatedSections);

    // Update context state
    setDocumentData(prev => ({
      ...prev,
      customSections: updatedSections
    }));

    toast.success('Subheading removed');
  };

  const toggleSubheading = (sectionId, subheadingId) => {
    const updatedSections = customSections.map(section => {
      if (section.id === sectionId) {
        return {
          ...section,
          subheadings: (section.subheadings || []).map(sub =>
            sub.id === subheadingId ? { ...sub, selected: !sub.selected } : sub
          )
        };
      }
      return section;
    });

    setCustomSections(updatedSections);

    // Update context state
    setDocumentData(prev => ({
      ...prev,
      customSections: updatedSections
    }));
  };

  const updateNewSubheading = (sectionId, field, value) => {
    setNewSubheading(prev => ({
      ...prev,
      [sectionId]: {
        ...prev[sectionId],
        [field]: value
      }
    }));
  };

  useEffect(() => {
    initializePage();
  }, []);

  // Clean up duplicate custom sections on component mount
  useEffect(() => {
    if (customSections.length > 0) {
      const uniqueSections = [];
      const seenTitles = new Set();
      
      customSections.forEach(section => {
        const titleKey = section.title.toLowerCase().trim();
        if (!seenTitles.has(titleKey)) {
          seenTitles.add(titleKey);
          uniqueSections.push(section);
        } else {
          console.log(`Removing duplicate custom section: ${section.title}`);
        }
      });
      
      if (uniqueSections.length !== customSections.length) {
        console.log(`Cleaned up ${customSections.length - uniqueSections.length} duplicate custom sections`);
        setCustomSections(uniqueSections);
        setDocumentData(prev => ({
          ...prev,
          customSections: uniqueSections
        }));
      }
    }
  }, []);
  
  // Debug: Log when documentData changes
  useEffect(() => {
    console.log('documentData changed:', {
      extractedTextContent: documentData.extractedTextContent,
      keys: Object.keys(documentData.extractedTextContent || {})
    });
  }, [documentData.extractedTextContent]);
  
  // No localStorage dependencies - rely on React Context only

  const initializePage = async () => {
    try {
      setLoading(true);
      
      console.log('=== SRS Headings Editor Initialization ===');
      console.log('Initial documentData:', documentData);
      console.log('extractedTextContent:', documentData.extractedTextContent);
      console.log('uploadedFiles:', documentData.uploadedFiles);
      
      // Load standard headings
      await loadStandardHeadings();
      
      // No localStorage dependencies - rely on React Context only
      console.log('✅ Initialization complete - using React Context data');
      
    } catch (error) {
      console.error('Error initializing page:', error);
      toast.error('Failed to initialize page');
    } finally {
      setLoading(false);
    }
  };

  // Helper function to extract all headings and subheadings from a nested structure
  const extractAllHeadings = (data, parentPath = '') => {
    const headings = [];
    Object.entries(data).forEach(([heading, value]) => {
      const path = parentPath ? `${parentPath} > ${heading}` : heading;
      headings.push(path);
      if (typeof value === 'object' && value !== null) {
        headings.push(...extractAllHeadings(value, path));
      }
    });
    return headings;
  };

  // Helper function to extract all headings from standard headings structure
  const extractStandardHeadings = (standardData) => {
    const headings = [];
    Object.entries(standardData).forEach(([category, categoryHeadings]) => {
      if (typeof categoryHeadings === 'object' && categoryHeadings !== null) {
        Object.keys(categoryHeadings).forEach(heading => {
          headings.push(heading);
        });
      }
    });
    return headings;
  };

  // Helper function to compare and filter unique headings
  const getUniqueHeadings = (openAIHeadings, standardHeadingsData) => {
    const openAIAllHeadings = extractAllHeadings(openAIHeadings);
    const standardAllHeadings = extractStandardHeadings(standardHeadingsData);
    
    console.log('OpenAI headings:', openAIAllHeadings);
    console.log('Standard headings:', standardAllHeadings);
    
    // Create a map of unique headings from OpenAI that don't exist in standard headings
    const uniqueHeadings = {};
    
    const processHeadings = (data, parentPath = '') => {
      Object.entries(data).forEach(([heading, value]) => {
        const path = parentPath ? `${parentPath} > ${heading}` : heading;
        
        // Check if this heading exists in standard headings (case-insensitive)
        const existsInStandard = standardAllHeadings.some(standardHeading => 
          standardHeading.toLowerCase() === heading.toLowerCase()
        );
        
        if (!existsInStandard) {
          if (typeof value === 'string') {
            // Leaf node - add to unique headings
            if (parentPath) {
              // Nested heading
              if (!uniqueHeadings[parentPath]) {
                uniqueHeadings[parentPath] = {};
              }
              uniqueHeadings[parentPath][heading] = value;
            } else {
              // Top-level heading
              uniqueHeadings[heading] = value;
            }
          } else if (typeof value === 'object' && value !== null) {
            // Nested node - process recursively
            processHeadings(value, path);
          }
        }
      });
    };
    
    processHeadings(openAIHeadings);
    
    console.log('Unique headings (not in standard):', uniqueHeadings);
    return uniqueHeadings;
  };

  const generateOpenAIHeadings = async () => {
    try {
      setGeneratingOpenAIHeadings(true);
      
      console.log('=== OPENAI HEADINGS DEBUG ===');
      console.log('DocumentData:', documentData);
      console.log('extractedTextContent:', documentData.extractedTextContent);
      console.log('extractedTextContent keys:', Object.keys(documentData.extractedTextContent || {}));
      
      // Get uploaded document content for OpenAI
      let transcriptText = "";
      let extractedTextContent = documentData.extractedTextContent;
      
      // Check if we have extracted text content
      if (!extractedTextContent || Object.keys(extractedTextContent).length === 0) {
        console.log('No extracted text content found in context');
        toast.error('No meeting summary content available. Please upload files and process them on the home page first.');
        return;
      }
      
      if (extractedTextContent && Object.keys(extractedTextContent).length > 0) {
        for (const docId in extractedTextContent) {
          const docInfo = extractedTextContent[docId];
          const textContent = docInfo.text_content;
          if (textContent && !textContent.startsWith("Error extracting text")) {
            transcriptText += `\n--- ${docInfo.file_name} ---\n`;
            if (textContent.length > 8000) {
              transcriptText += `${textContent.substring(0, 8000)}...\n[Content truncated for processing]`;
            } else {
              transcriptText += textContent;
            }
          }
        }
      }
      
      console.log('Transcript text length:', transcriptText.length);
      
      if (!transcriptText) {
        toast.error('No meeting summary content available. Please upload files (PDF, DOCX, TXT) on the home page first.');
        return;
      }
      
      // Call OpenAI API to generate headings
      const response = await fetch('/generate-gemini-headings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          transcript_text: transcriptText
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('✅ OpenAI response received:', data);
        console.log('✅ OpenAI response success:', data.success);
        console.log('✅ OpenAI response message:', data.message);
        console.log('✅ OpenAI headings data:', data.gemini_headings);
        console.log('✅ OpenAI headings type:', typeof data.gemini_headings);
        console.log('✅ OpenAI headings keys:', Object.keys(data.gemini_headings || {}));
        console.log('✅ OpenAI headings length:', Object.keys(data.gemini_headings || {}).length);
        
        // Check if we got valid headings
        if (data.gemini_headings && Object.keys(data.gemini_headings).length > 0) {
          console.log('✅ Valid headings found, processing unique headings...');
          
          // Get unique headings (not in standard headings)
          const uniqueHeadings = getUniqueHeadings(data.gemini_headings, standardHeadings);
          
          // Set only unique headings
          setAiGeneratedHeadings(uniqueHeadings);
          
          // Update context state
          setDocumentData(prev => ({
            ...prev,
            aiGeneratedHeadings: uniqueHeadings
          }));
          
          const uniqueCount = Object.keys(uniqueHeadings).length;
          if (uniqueCount > 0) {
            toast.success(`OpenAI headings generated successfully! Found ${uniqueCount} unique headings not in standard template.`);
          } else {
            toast.success('OpenAI headings generated successfully! All headings already exist in standard template.');
          }
        } else {
          console.log('❌ No valid headings found in response');
          console.log('🔧 Setting fallback headings for testing...');
          const fallbackHeadings = {
            "Introduction": "Overview and purpose of the system",
            "Functional Requirements": "Core system functions and features", 
            "Non-Functional Requirements": "Performance, security, and usability requirements",
            "System Architecture": "Technical design and component structure",
            "User Interface": "UI/UX specifications and wireframes"
          };
          
          // Get unique fallback headings
          const uniqueFallbackHeadings = getUniqueHeadings(fallbackHeadings, standardHeadings);
          setAiGeneratedHeadings(uniqueFallbackHeadings);
          
          // Update context state
          setDocumentData(prev => ({
            ...prev,
            aiGeneratedHeadings: uniqueFallbackHeadings
          }));
        }
        
        // Check if we got sample headings (API key missing)
        if (data.gemini_headings && Object.keys(data.gemini_headings).length > 0) {
          const firstKey = Object.keys(data.gemini_headings)[0];
          if (firstKey === "Introduction" && data.gemini_headings[firstKey] === "Overview and purpose of the system") {
            toast.success('Note: Using sample headings. Gemini API is configured for AI-generated headings.');
          }
        }
        
        // Debug: Check state after setting
        setTimeout(() => {
          console.log('aiGeneratedHeadings state after setting:', aiGeneratedHeadings);
          console.log('aiGeneratedHeadings keys:', Object.keys(aiGeneratedHeadings || {}));
        }, 100);
      } else {
        throw new Error('Failed to generate Gemini headings');
      }
      
    } catch (error) {
      console.error('Error generating OpenAI headings:', error);
      toast.error('Failed to generate OpenAI headings');
    } finally {
      setGeneratingOpenAIHeadings(false);
    }
  };

  const loadStandardHeadings = async () => {
    try {
      const response = await srsApi.getStandardHeadings();
      setStandardHeadings(response.headings || response);
    } catch (error) {
      console.error('Failed to load standard headings:', error);
      toast.error('Failed to load standard headings');
    }
  };

  const processDocsFolderForTOC = async () => {
    try {
      setProcessingFiles(true);
      
      // Show initial progress message
      toast.loading('Processing docs folder PDFs for TOC extraction... This may take a few minutes.', {
        duration: 10000
      });
      
      console.log('Processing docs folder for TOC extraction...');
      
      const response = await srsApi.processDocsFolderTOC();
      
      if (response.success) {
        const filesProcessed = response.files_processed || [];
        
        toast.success(`✅ Successfully processed docs folder! Processed ${filesProcessed.length} PDF files.`);
        
        console.log('Docs folder processing results:', {
          files_processed: filesProcessed
        });
      } else {
        throw new Error(response.message || 'Failed to process docs folder');
      }
      
    } catch (error) {
      console.error('Error processing docs folder:', error);
      
      // Show more specific error messages
      if (error.message.includes('timeout')) {
        toast.error('Processing took too long. Please try again.');
      } else if (error.message.includes('Network Error')) {
        toast.error('Cannot connect to server. Please check if the backend is running.');
      } else {
        toast.error(errorHandler.handleApiError(error));
      }
    } finally {
      setProcessingFiles(false);
    }
  };

  // Selection handlers
  const handleAiHeadingToggle = (path) => {
    const newSelectedAiHeadings = { ...selectedAiHeadings, [path]: !selectedAiHeadings[path] };
    setSelectedAiHeadings(newSelectedAiHeadings);
    
    // Update context state
    setDocumentData(prev => ({
      ...prev,
      selectedAiHeadings: newSelectedAiHeadings
    }));
  };

  // Toggle all AI headings (select all if none selected, deselect all if some/all selected)
  const toggleAllAiHeadings = () => {
    const totalHeadings = Object.keys(aiGeneratedHeadings).length;
    const selectedCount = Object.keys(selectedAiHeadings).length;
    
    if (selectedCount === 0) {
      // Select all if none are selected
      const allHeadings = {};
      const collectHeadings = (data, parentPath = '') => {
        Object.entries(data).forEach(([heading, value]) => {
          const path = parentPath ? `${parentPath} > ${heading}` : heading;
          if (typeof value === 'string') {
            allHeadings[path] = true;
          } else if (typeof value === 'object' && value !== null) {
            collectHeadings(value, path);
          }
        });
      };
      collectHeadings(aiGeneratedHeadings);
      setSelectedAiHeadings(allHeadings);
      
      // Update context state
      setDocumentData(prev => ({
        ...prev,
        selectedAiHeadings: allHeadings
      }));
    } else {
      // Deselect all if some or all are selected
      setSelectedAiHeadings({});
      
      // Update context state
      setDocumentData(prev => ({
        ...prev,
        selectedAiHeadings: {}
      }));
    }
  };

  const handleStandardHeadingToggle = (category, heading) => {
    const newSelectedStandardHeadings = {
      ...selectedStandardHeadings,
      [category]: {
        ...selectedStandardHeadings[category],
        [heading]: !selectedStandardHeadings[category]?.[heading]
      }
    };
    setSelectedStandardHeadings(newSelectedStandardHeadings);
    
    // Update context state
    setDocumentData(prev => ({
      ...prev,
      selectedStandardHeadings: newSelectedStandardHeadings
    }));
  };

  // Toggle all standard headings
  const toggleAllStandardHeadings = () => {
    const selectedCount = Object.keys(selectedStandardHeadings).length;
    
    if (selectedCount === 0) {
      // Select all if none are selected
      const allHeadings = {};
      Object.entries(standardHeadings).forEach(([category, categoryHeadings]) => {
        allHeadings[category] = {};
        const collectCategoryHeadings = (headings, categoryPath = '') => {
          Object.entries(headings).forEach(([heading, purpose]) => {
            if (typeof purpose === 'object' && purpose !== null) {
              collectCategoryHeadings(purpose, categoryPath ? `${categoryPath} > ${heading}` : heading);
            } else {
              const finalCategory = categoryPath || category;
              if (!allHeadings[finalCategory]) {
                allHeadings[finalCategory] = {};
              }
              allHeadings[finalCategory][heading] = true;
            }
          });
        };
        collectCategoryHeadings(categoryHeadings);
      });
      setSelectedStandardHeadings(allHeadings);
      
      // Update context state
      setDocumentData(prev => ({
        ...prev,
        selectedStandardHeadings: allHeadings
      }));
    } else {
      // Deselect all if some or all are selected
      setSelectedStandardHeadings({});
      
      // Update context state
      setDocumentData(prev => ({
        ...prev,
        selectedStandardHeadings: {}
      }));
    }
  };



  // Custom section handlers
  const addCustomSection = () => {
    console.log('=== ADDING CUSTOM SECTION ===');
    console.log('Current customSections:', customSections);
    console.log('New section to add:', newSection);
    
    if (!newSection.title.trim() || !newSection.purpose.trim()) {
      toast.error('Please fill in both title and purpose');
      return;
    }

    // Check for duplicate titles
    const existingSection = customSections.find(section => 
      section.title.toLowerCase().trim() === newSection.title.toLowerCase().trim()
    );
    
    if (existingSection) {
      toast.error('A section with this title already exists');
      return;
    }

    const newId = Date.now() + Math.random();
    const newCustomSections = [...customSections, { 
      ...newSection, 
      id: newId, // More unique ID
      selected: true,
      userPrompt: newSection.userPrompt || ""
    }];
    
    console.log('New customSections array:', newCustomSections);
    console.log('New ID generated:', newId);
    
    setCustomSections(newCustomSections);
    setNewSection({ title: '', purpose: '', userPrompt: '' });
    setUserPrompt(''); // Clear the prompt after use
    
    // Update context state
    setDocumentData(prev => ({
      ...prev,
      customSections: newCustomSections
    }));
    
    toast.success('Custom section added');
  };

  const removeCustomSection = (id) => {
    const newCustomSections = customSections.filter(section => section.id !== id);
    setCustomSections(newCustomSections);
    
    // Update context state
    setDocumentData(prev => ({
      ...prev,
      customSections: newCustomSections
    }));
    
    toast.success('Custom section removed');
  };

  const toggleCustomSection = (id) => {
    const newCustomSections = customSections.map(section => 
      section.id === id ? { ...section, selected: !section.selected } : section
    );
    setCustomSections(newCustomSections);
    
    // Update context state
    setDocumentData(prev => ({
      ...prev,
      customSections: newCustomSections
    }));
  };

  // Get all selected headings
  const getAllSelectedHeadings = () => {
    const selected = [];
    const addedHeadings = new Set(); // Track all added headings to prevent duplicates
    
    // Helper function to get purpose from nested structure
    const getPurposeFromNested = (data, category, heading) => {
      if (!data[category]) return '';
      if (typeof data[category][heading] === 'string') {
        return data[category][heading];
      }
      if (typeof data[category][heading] === 'object' && data[category][heading] !== null) {
        return `Nested category: ${heading}`;
      }
      return '';
    };

    // Helper to get purpose from AI generated headings
    const getPurposeFromAi = (data, path) => {
      const parts = path.split(' > ');
      let current = data;
      for (let i = 0; i < parts.length; i++) {
        if (!current) return '';
        if (i === parts.length - 1) {
          if (typeof current[parts[i]] === 'string') return current[parts[i]];
          return '';
        }
        current = current[parts[i]];
      }
      return '';
    };
    
    // Add selected AI generated headings
    Object.entries(selectedAiHeadings).forEach(([path, isSelected]) => {
      if (isSelected) {
        const headingKey = path.toLowerCase().trim();
        if (!addedHeadings.has(headingKey)) {
          addedHeadings.add(headingKey);
          selected.push({
            heading: path,
            purpose: getPurposeFromAi(aiGeneratedHeadings, path),
            source: 'AI Generated',
            category: 'AI'
          });
        }
      }
    });
    
    // Add selected standard headings
    Object.entries(selectedStandardHeadings).forEach(([category, headings]) => {
      Object.entries(headings).forEach(([heading, isSelected]) => {
        if (isSelected) {
          const headingKey = heading.toLowerCase().trim();
          if (!addedHeadings.has(headingKey)) {
            addedHeadings.add(headingKey);
            selected.push({
              heading,
              purpose: getPurposeFromNested(standardHeadings, category, heading),
              source: 'Standard Template',
              category
            });
          }
        }
      });
    });
    

    
    // Add custom sections and their subheadings
    console.log('=== CUSTOM SECTIONS DEBUG ===');
    console.log('customSections array:', customSections);
    console.log('customSections length:', customSections.length);

    customSections.forEach((section, index) => {
      console.log(`Custom section ${index}:`, section);

      // Add main custom section if selected
      if (section.selected !== false) {
        const headingKey = section.title.toLowerCase().trim();
        if (!addedHeadings.has(headingKey)) {
          console.log(`Adding custom section: ${section.title}`);
          addedHeadings.add(headingKey);
          selected.push({
            heading: section.title,
            purpose: section.purpose,
            source: 'Custom Section',
            category: 'Custom'
          });
        } else {
          console.log(`Skipping duplicate custom section: ${section.title}`);
        }

        // Add selected subheadings
        if (section.subheadings && section.subheadings.length > 0) {
          section.subheadings.forEach((subheading) => {
            if (subheading.selected !== false) {
              const subheadingKey = `${section.title} - ${subheading.title}`.toLowerCase().trim();
              if (!addedHeadings.has(subheadingKey)) {
                console.log(`Adding subheading: ${subheading.title} under ${section.title}`);
                addedHeadings.add(subheadingKey);
                selected.push({
                  heading: `${section.title} - ${subheading.title}`,
                  purpose: subheading.purpose,
                  source: 'Custom Subheading',
                  category: 'Custom',
                  parentSection: section.title
                });
              }
            }
          });
        }
      } else {
        console.log(`Skipping custom section: ${section.title} (not selected)`);
      }
    });
    
    console.log('Final selected array:', selected);
    
    return selected;
  };

  // Helper function to find custom prompt for a heading
  const findCustomPromptForHeading = (heading) => {
    console.log(`🔍 Looking for custom prompt for heading: "${heading}"`);
    console.log(`📋 Available prompts:`, headingCustomPrompts);

    // Check different possible keys for the heading
    const possibleKeys = [
      `merged_${heading}`,
      `standard_${heading}`,
      `ai_${heading}`,
      `ai_${heading.replace(/[^a-zA-Z0-9]/g, '_')}`, // AI-generated headings use sanitized keys
      // Also check for category-level prompts
      `category_${heading}`,
      `ai_category_${heading}`
    ];

    // Add AI-generated heading keys (handle nested paths)
    Object.entries(aiGeneratedHeadings).forEach((entry) => {
      const addAiKeys = (data, parentPath = '') => {
        Object.entries(data).forEach(([aiHeading, value]) => {
          const path = parentPath ? `${parentPath} > ${aiHeading}` : aiHeading;
          if (path === heading || aiHeading === heading) {
            const aiKey = `ai_${path.replace(/[^a-zA-Z0-9]/g, '_')}`;
            possibleKeys.push(aiKey);
          }
          if (typeof value === 'object' && value !== null) {
            addAiKeys(value, path);
          }
        });
      };
      addAiKeys(entry[1] || {});
    });

    // Check for standard headings with category prefix (standard_category_heading format)
    Object.entries(standardHeadings).forEach(([category, categoryHeadings]) => {
      if (typeof categoryHeadings === 'object' && categoryHeadings !== null) {
        Object.keys(categoryHeadings).forEach(headingName => {
          if (headingName === heading) {
            possibleKeys.push(`standard_${category}_${heading}`);
          }
        });
      }
    });

    console.log(`🔑 Checking keys for "${heading}":`, possibleKeys);

    for (const key of possibleKeys) {
      if (headingCustomPrompts[key] && headingCustomPrompts[key].trim()) {
        console.log(`✅ Found custom prompt for "${heading}" with key "${key}":`, headingCustomPrompts[key]);
        return headingCustomPrompts[key].trim();
      }
    }

    // Check for custom sections
    const customSection = customSections.find(section => section.title === heading);
    if (customSection) {
      const customKey = `custom_${customSection.id}`;
      if (headingCustomPrompts[customKey] && headingCustomPrompts[customKey].trim()) {
        console.log(`✅ Found custom prompt for custom section "${heading}":`, headingCustomPrompts[customKey]);
        return headingCustomPrompts[customKey].trim();
      }
    }

    // Check for subheadings (format: "Section Title - Subheading Title")
    if (heading.includes(' - ')) {
      const [sectionTitle, subheadingTitle] = heading.split(' - ');
      const parentSection = customSections.find(section => section.title === sectionTitle);
      if (parentSection && parentSection.subheadings) {
        const subheading = parentSection.subheadings.find(sub => sub.title === subheadingTitle);
        if (subheading) {
          const subheadingKey = `custom_sub_${parentSection.id}_${subheading.id}`;
          if (headingCustomPrompts[subheadingKey] && headingCustomPrompts[subheadingKey].trim()) {
            console.log(`✅ Found custom prompt for subheading "${heading}":`, headingCustomPrompts[subheadingKey]);
            return headingCustomPrompts[subheadingKey].trim();
          }
        }
      }
    }

    console.log(`❌ No custom prompt found for "${heading}"`);
    return null;
  };

  // Generate SRS
  const generateSRS = async () => {
    // Build selectedHeadings from user selections
    const selectedHeadings = getAllSelectedHeadings();
    let customSectionsToSend = [...customSections];
    let customInstructions = "";

    // Build the final selectedHeadings array with custom prompts
    const allSelectedHeadings = [
      ...selectedHeadings.map(heading => {
        const customPrompt = findCustomPromptForHeading(heading.heading);
        return {
          ...heading,
          userPrompt: customPrompt // Backend expects 'userPrompt' field
        };
      }),
      ...customSectionsToSend.filter(
        section => section.purpose && section.purpose.trim() !== ""
      ).map(section => {
        const customPrompt = findCustomPromptForHeading(section.title);
        return {
          heading: section.title,
          purpose: section.purpose,
          category: section.category || "Custom",
          source: section.source || "Custom Section",
          userPrompt: customPrompt // Backend expects 'userPrompt' field
        };
      })
    ];

    // Debug log
    console.log("selectedHeadings being sent:", allSelectedHeadings);
    console.log("headingCustomPrompts:", headingCustomPrompts);
    try {
      setGeneratingSRS(true);
      let meetingSummary = "";
      if (documentData.extractedTextContent && Object.keys(documentData.extractedTextContent).length > 0) {
        for (const docId in documentData.extractedTextContent) {
          const docInfo = documentData.extractedTextContent[docId];
          const textContent = docInfo.text_content;
          if (textContent && !textContent.startsWith("Error extracting text")) {
            meetingSummary += `\n--- ${docInfo.file_name} ---\n`;
            meetingSummary += textContent;
          }
        }
      }
      const response = await fetch('/generate-srs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          selectedHeadings: allSelectedHeadings,
          customInstructions, // Only present if user said 'apply to all sections'
          meetingSummary: meetingSummary,
          // Ensure backend receives the user-entered project title
          projectTitle: documentData?.projectTitle || documentData?.title || ''
        }),
      });
      if (response.ok) {
        // Extract document ID from response headers
        const documentId = response.headers.get('X-Document-ID');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'generated-srs.docx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        // Store document ID and show diagram manager
        if (documentId) {
          setGeneratedDocumentId(documentId);
          setShowDiagramManager(true);
        }

        toast.success('SRS generated successfully! Check below for diagram customization options.');
      } else {
        throw new Error('Failed to generate SRS');
      }
    } catch (error) {
      console.error('Error generating SRS:', error);
      toast.error('Failed to generate SRS');
    } finally {
      setGeneratingSRS(false);
    }
  };

  // Helper function to merge standard headings with unique AI headings
  const getMergedHeadings = () => {
    const merged = {};
    
    // Add all standard headings to the merged structure
    Object.entries(standardHeadings).forEach(([category, categoryHeadings]) => {
      if (typeof categoryHeadings === 'object' && categoryHeadings !== null) {
        Object.entries(categoryHeadings).forEach(([heading, purpose]) => {
          // Ensure purpose is a string
          const purposeText = typeof purpose === 'string' ? purpose : 'Purpose for ' + heading;
          merged[heading] = purposeText;
        });
      }
    });
    
    // Add unique AI headings to the merged structure (flattened, no categories)
    Object.entries(aiGeneratedHeadings).forEach(([heading, value]) => {
      if (typeof value === 'string') {
        // Only add if not already in standard headings (case-insensitive)
        const existsInStandard = Object.keys(merged).some(standardHeading => 
          standardHeading.toLowerCase() === heading.toLowerCase()
        );
        if (!existsInStandard) {
          merged[heading] = value;
        }
      } else if (typeof value === 'object' && value !== null) {
        // Handle nested AI headings - flatten them
        Object.entries(value).forEach(([subHeading, subValue]) => {
          if (typeof subValue === 'string') {
            const fullHeading = `${heading} > ${subHeading}`;
            const existsInStandard = Object.keys(merged).some(standardHeading => 
              standardHeading.toLowerCase() === fullHeading.toLowerCase()
            );
            if (!existsInStandard) {
              merged[fullHeading] = subValue;
            }
          } else if (typeof subValue === 'object' && subValue !== null) {
            // Handle deeper nesting - flatten further
            Object.entries(subValue).forEach(([deepSubHeading, deepSubValue]) => {
              if (typeof deepSubValue === 'string') {
                const fullHeading = `${heading} > ${subHeading} > ${deepSubHeading}`;
                const existsInStandard = Object.keys(merged).some(standardHeading => 
                  standardHeading.toLowerCase() === fullHeading.toLowerCase()
                );
                if (!existsInStandard) {
                  merged[fullHeading] = deepSubValue;
                }
              }
            });
          }
        });
      }
    });
    
    // Final check: ensure all values are strings
    Object.keys(merged).forEach(heading => {
      if (typeof merged[heading] !== 'string') {
        merged[heading] = 'Purpose for ' + heading;
      }
    });
    
    return merged;
  };

  // Helper function to merge selected headings from both sources
  const getMergedSelectedHeadings = () => {
    const merged = {};
    
    // Add standard heading selections
    Object.entries(selectedStandardHeadings).forEach(([category, headings]) => {
      Object.entries(headings).forEach(([heading, isSelected]) => {
        if (isSelected) {
          merged[heading] = true;
        }
      });
    });
    
    // Add AI heading selections
    Object.entries(selectedAiHeadings).forEach(([path, isSelected]) => {
      if (isSelected) {
        merged[path] = true;
      }
    });
    
    return merged;
  };

  // Unified toggle handler for merged headings
  const handleMergedHeadingToggle = (heading) => {
    // Check if it's an AI heading (has path with >)
    if (heading.includes(' > ')) {
      // Handle AI heading toggle
      const newSelectedAiHeadings = { ...selectedAiHeadings, [heading]: !selectedAiHeadings[heading] };
      setSelectedAiHeadings(newSelectedAiHeadings);
      
      // Update context state
      setDocumentData(prev => ({
        ...prev,
        selectedAiHeadings: newSelectedAiHeadings
      }));
    } else {
      // Handle standard heading toggle - find which category it belongs to
      let found = false;
      Object.entries(selectedStandardHeadings).forEach(([category, headings]) => {
        if (headings.hasOwnProperty(heading)) {
          const newSelectedStandardHeadings = { ...selectedStandardHeadings };
          newSelectedStandardHeadings[category][heading] = !newSelectedStandardHeadings[category][heading];
          setSelectedStandardHeadings(newSelectedStandardHeadings);
          
          // Update context state
          setDocumentData(prev => ({
            ...prev,
            selectedStandardHeadings: newSelectedStandardHeadings
          }));
          found = true;
        }
      });
      
      if (!found) {
        // If not found in standard, treat as AI heading
        const newSelectedAiHeadings = { ...selectedAiHeadings, [heading]: !selectedAiHeadings[heading] };
        setSelectedAiHeadings(newSelectedAiHeadings);
        
        // Update context state
        setDocumentData(prev => ({
          ...prev,
          selectedAiHeadings: newSelectedAiHeadings
        }));
      }
    }
  };

  // Unified toggle all handler for merged headings
  const toggleAllMergedHeadings = () => {
    const mergedHeadings = getMergedHeadings();
    const totalHeadings = Object.keys(mergedHeadings).length;
    const currentSelected = Object.keys(selectedStandardHeadings).reduce((count, category) => 
      count + Object.keys(selectedStandardHeadings[category]).length, 0
    ) + Object.keys(selectedAiHeadings).length;
    
    if (currentSelected === 0) {
      // Select all
      const allStandardSelections = {};
      Object.entries(standardHeadings).forEach(([category, categoryHeadings]) => {
        if (typeof categoryHeadings === 'object' && categoryHeadings !== null) {
          allStandardSelections[category] = {};
          Object.keys(categoryHeadings).forEach(heading => {
            allStandardSelections[category][heading] = true;
          });
        }
      });
      setSelectedStandardHeadings(allStandardSelections);
      
      const allAiSelections = {};
      Object.keys(mergedHeadings).forEach(heading => {
        // If it's not in standard headings, it's an AI heading
        const isStandardHeading = Object.values(standardHeadings).some(category => 
          typeof category === 'object' && category !== null && category.hasOwnProperty(heading)
        );
        if (!isStandardHeading) {
          allAiSelections[heading] = true;
        }
      });
      setSelectedAiHeadings(allAiSelections);
      
      // Update context state
      setDocumentData(prev => ({
        ...prev,
        selectedStandardHeadings: allStandardSelections,
        selectedAiHeadings: allAiSelections
      }));
    } else {
      // Deselect all
      setSelectedStandardHeadings({});
      setSelectedAiHeadings({});
      
      // Update context state
      setDocumentData(prev => ({
        ...prev,
        selectedStandardHeadings: {},
        selectedAiHeadings: {}
      }));
    }
  };

  // Render AI generated headings recursively
  const renderAiHeadings = (data, selected, onToggle, parentPath = '') => {
    return Object.entries(data).map(([heading, value]) => {
      const path = parentPath ? `${parentPath} > ${heading}` : heading;
      const headingKey = `ai_${path.replace(/[^a-zA-Z0-9]/g, '_')}`;

      if (typeof value === 'string') {
        // Leaf node - add + button like predefined headings
        return (
          <div key={path}>
            <div className="flex items-start space-x-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50">
              <input
                type="checkbox"
                checked={!!selected[path]}
                onChange={() => onToggle(path)}
                className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium text-gray-900">{heading}</div>
                  <button
                    onClick={() => togglePromptBox(headingKey)}
                    className="ml-2 p-2 text-blue-800 hover:text-blue-900 hover:bg-blue-50 rounded-full transition-colors"
                    title="Add custom prompt for this section"
                  >
                    <PlusIcon className="w-5 h-5" />
                  </button>
                </div>
                <div className="text-xs text-gray-500 mt-1">{value}</div>
              </div>
            </div>
            {/* Custom Prompt Box for AI-Generated Headings */}
            {showPromptBox[headingKey] && (
              <div className="ml-6 mb-2">
                <textarea
                  value={headingCustomPrompts[headingKey] || ''}
                  onChange={(e) => updateCustomPrompt(headingKey, e.target.value)}
                  placeholder={`Enter custom instructions for "${heading}" (e.g., "Give me 10 functional requirements in bullet points")`}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  rows="3"
                />
                <p className="text-xs text-gray-500 mt-1">
                  This prompt will be applied specifically to the "{heading}" section
                </p>
              </div>
            )}
          </div>
        );
      } else if (typeof value === 'object' && value !== null) {
        // Nested node
        return (
          <div key={path} className="mb-4">
            <div className="text-md font-semibold text-gray-700 mb-2 border-l-4 border-blue-200 pl-3">
              {heading}
            </div>
            <div className="ml-4 space-y-2">
              {renderAiHeadings(value, selected, onToggle, path)}
            </div>
          </div>
        );
      } else {
        return null;
      }
    });
  };

  // Render heading list for standard and extracted headings
  const renderHeadingList = (headings, selectedHeadings, onToggle, title, emptyMessage, toggleAllHandler) => {
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
              <input
                type="checkbox"
                checked={!!selectedHeadings[categoryPath || 'Other']?.[heading]}
                onChange={() => onToggle(categoryPath || 'Other', heading)}
                className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
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
                  {renderCategoryHeadings(categoryHeadings, category)}
                </div>
              </div>
            ))}
          </>
        ) : (
          <div className="flex items-center justify-center h-32 text-gray-400 text-center">
            <span>{emptyMessage}</span>
          </div>
        )}
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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                <DocumentTextIcon className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">SRS Headings Editor</h1>
                <p className="text-sm text-gray-600">Step 2: Select Headings for SRS</p>
              </div>
            </div>
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full">Step 2 of 2</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">SRS Headings Editor</h1>
              <p className="text-gray-600 mt-2">Select and organize headings for your Software Requirements Specification</p>
            </div>
            <button
              onClick={() => navigate('/')}
              className="flex items-center space-x-2 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              <ArrowLeftIcon className="w-4 h-4" />
              <span>Back to Home</span>
            </button>
          </div>
        </div>

        {/* Section 1: OpenAI Headings Generation */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
            <SparklesIcon className="w-5 h-5 mr-2" />
            🤖 Smart AI Headings
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            AI-powered headings generated from your uploaded documents and meeting summaries
          </p>
          
          {documentData.extractedTextContent && Object.keys(documentData.extractedTextContent).length > 0 && (
            <div className="mb-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-800">
                📄 Selected files for processing: {Object.keys(documentData.extractedTextContent).length} files
              </p>
              <p className="text-xs text-blue-600 mt-1">
                Files: {Object.keys(documentData.extractedTextContent).map(key => documentData.extractedTextContent[key].file_name).join(', ')}
              </p>
            </div>
          )}
          
          <div className="text-center">
            <button
              onClick={generateOpenAIHeadings}
              disabled={generatingOpenAIHeadings}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center mx-auto space-x-2"
            >
              {generatingOpenAIHeadings ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>🤖 Generating Smart Headings...</span>
                </>
              ) : (
                <>
                  <SparklesIcon className="w-4 h-4" />
                  <span>🤖 Generate Smart AI Headings</span>
                </>
              )}
            </button>
            <p className="text-sm text-gray-500 mt-2">
              ✨ AI will analyze your documents and suggest relevant SRS headings automatically
            </p>
          </div>
        </div>

        {/* Section 2: All Available Headings (Standard + AI Generated) */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
            <DocumentTextIcon className="w-5 h-5 mr-2" />
             Standard SRS Templates + AI Suggestions
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            SRS headings and AI-generated suggestions based on your documents
          </p>

          {/* Toggle All button for merged headings */}
          <div className="mb-4 flex justify-end">
            <button
              onClick={toggleAllMergedHeadings}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              {Object.keys(selectedStandardHeadings).length === 0 && Object.keys(selectedAiHeadings).length === 0
                ? '✅ Select All Headings'
                : '❌ Deselect All Headings'}
            </button>
          </div>

          <div className="h-[600px] overflow-y-auto">
            {/* Standard Headings Section */}
            <div className="mb-8">
              <div className="flex items-center mb-4 p-3 bg-blue-50 rounded-lg">
                <DocumentTextIcon className="w-5 h-5 mr-2 text-blue-600" />
                <h3 className="text-lg font-semibold text-blue-800"> Standard SRS Templates</h3>
                <span className="ml-2 text-sm text-blue-600"></span>
              </div>

              {Object.keys(standardHeadings).length > 0 ? (
                <div className="space-y-4">
                  {Object.entries(standardHeadings).map(([category, categoryHeadings]) => (
                    <div key={category} className="mb-6">
                      <h4 className="text-md font-medium text-gray-700 mb-3 border-l-4 border-blue-200 pl-3">
                        {category}
                      </h4>
                      <div className="space-y-2 ml-4">
                        {Object.entries(categoryHeadings).map(([heading, purpose]) => {
                          const headingKey = `standard_${category}_${heading}`;
                          return (
                            <div key={heading} className="space-y-2">
                              <div className="flex items-start space-x-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50">
                                <input
                                  type="checkbox"
                                  checked={!!selectedStandardHeadings[category]?.[heading]}
                                  onChange={() => handleStandardHeadingToggle(category, heading)}
                                  className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center justify-between">
                                    <div className="text-sm font-medium text-gray-900">{heading}</div>
                                    <button
                                      onClick={() => togglePromptBox(headingKey)}
                                      className="ml-2 p-2 text-blue-800 hover:text-blue-900 hover:bg-blue-50 rounded-full transition-colors"
                                      title="Add custom prompt for this section"
                                    >
                                      <PlusIcon className="w-5 h-5" />
                                    </button>
                                  </div>
                                  <div className="text-xs text-gray-500 mt-1">{typeof purpose === 'string' ? purpose : String(purpose)}</div>
                                </div>
                              </div>
                              {showPromptBox[headingKey] && (
                                <div className="ml-6 mb-2">
                                  <textarea
                                    value={headingCustomPrompts[headingKey] || ''}
                                    onChange={(e) => updateCustomPrompt(headingKey, e.target.value)}
                                    placeholder={`Enter custom instructions for "${heading}" (e.g., "Give me 10 functional requirements in bullet points")`}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                    rows="3"
                                  />
                                  <p className="text-xs text-gray-500 mt-1">
                                    This prompt will be applied specifically to the "{heading}" section
                                  </p>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4">
                  <p className="text-gray-500">📋 Loading standard headings...</p>
                </div>
              )}
            </div>

            {/* AI Generated Headings Section */}
            {Object.keys(aiGeneratedHeadings).length > 0 && (
              <div className="mb-8">
                <div className="flex items-center mb-4 p-3 bg-blue-50 rounded-lg">
                  <SparklesIcon className="w-5 h-5 mr-2 text-blue-600" />
                  <h3 className="text-lg font-semibold text-blue-600">AI Generated Suggestions</h3>
                  <span className="ml-2 text-sm  text-blue-600"></span>
                </div>

                <div className="space-y-2 ml-4">
                  {renderAiHeadings(aiGeneratedHeadings, selectedAiHeadings, handleAiHeadingToggle)}
                </div>
              </div>
            )}

            {Object.keys(standardHeadings).length === 0 && Object.keys(aiGeneratedHeadings).length === 0 && (
              <div className="text-center py-8">
                <p className="text-gray-500">📋 No headings available yet. Click "🤖 Generate Smart AI Headings" above to get started!</p>
              </div>
            )}
          </div>
        </div>

        {/* Section 3: Custom Sections */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
            <PlusIcon className="w-5 h-5 mr-2" />
            Your Custom Sections
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Create personalized sections with subheadings tailored to your specific project requirements
          </p>
          
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
                value={newSection.purpose || ""}
                onChange={e => setNewSection(prev => ({ ...prev, purpose: e.target.value }))}
                placeholder="Why do you want to add this section.?"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={addCustomSection}
                className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-600 flex items-center justify-center"
              >
                <PlusIcon className="w-4 h-4 mr-2" />
                Add Custom Section
              </button>
            </div>
          </div>
          
          {/* Custom Sections List */}
          {customSections.length > 0 && (
            <div className="space-y-4">
              {customSections.map((section) => {
                const headingKey = `custom_${section.id}`;
                return (
                  <div key={section.id} className="border border-gray-200 rounded-lg p-4 bg-white">
                    {/* Main Section Header */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center flex-1">
                        <input
                          type="checkbox"
                          checked={section.selected !== false}
                          onChange={() => toggleCustomSection(section.id)}
                          className="mr-3 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="font-medium text-gray-900 text-lg">{section.title}</div>
                              <div className="text-sm text-gray-500">{section.purpose}</div>
                            </div>
                            <div className="flex items-center space-x-2">
                              <button
                                onClick={() => togglePromptBox(headingKey)}
                                className="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-full transition-colors"
                                title="Add custom prompt for this custom section"
                              >
                                <PlusIcon className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => toggleSubheadingView(section.id)}
                                className="px-3 py-1 text-sm bg-blue-100 text-blue-700 hover:bg-blue-200 rounded-md transition-colors"
                                title="Manage subheadings"
                              >
                                {showSubheadings[section.id] ? 'Hide Subheadings' : 'Add Subheadings'}
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => removeCustomSection(section.id)}
                        className="text-red-600 hover:text-red-800 ml-2"
                      >
                        Remove
                      </button>
                    </div>

                    {/* Custom Prompt Box */}
                    {showPromptBox[headingKey] && (
                      <div className="mb-3">
                        <textarea
                          value={headingCustomPrompts[headingKey] || ''}
                          onChange={(e) => updateCustomPrompt(headingKey, e.target.value)}
                          placeholder={`Enter custom instructions for "${section.title}" (e.g., "Give me 10 functional requirements in bullet points")`}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                          rows="3"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          This prompt will be applied specifically to the custom "{section.title}" section
                        </p>
                      </div>
                    )}

                    {/* Subheadings Section */}
                    {showSubheadings[section.id] && (
                      <div className="border-t border-gray-200 pt-3 mt-3">
                        <h4 className="text-sm font-medium text-gray-700 mb-3">Subheadings for "{section.title}"</h4>

                        {/* Add New Subheading Form */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4 p-3 bg-gray-50 rounded-lg">
                          <div>
                            <input
                              type="text"
                              value={newSubheading[section.id]?.title || ''}
                              onChange={(e) => updateNewSubheading(section.id, 'title', e.target.value)}
                              placeholder="Subheading title"
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                            />
                          </div>
                          <div>
                            <input
                              type="text"
                              value={newSubheading[section.id]?.purpose || ''}
                              onChange={(e) => updateNewSubheading(section.id, 'purpose', e.target.value)}
                              placeholder="Subheading purpose"
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                            />
                          </div>
                          <div>
                            <button
                              onClick={() => addSubheading(section.id)}
                              className="w-full bg-blue-600 text-white px-3 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm flex items-center justify-center"
                            >
                              <PlusIcon className="w-4 h-4 mr-1" />
                              Add Subheading
                            </button>
                          </div>
                        </div>

                        {/* Existing Subheadings List */}
                        {section.subheadings && section.subheadings.length > 0 && (
                          <div className="space-y-2">
                            {section.subheadings.map((subheading) => {
                              const subheadingKey = `custom_sub_${section.id}_${subheading.id}`;
                              return (
                                <div key={subheading.id} className="space-y-2">
                                  <div className="flex items-center justify-between p-2 bg-blue-50 rounded-md">
                                    <div className="flex items-center flex-1">
                                      <input
                                        type="checkbox"
                                        checked={subheading.selected !== false}
                                        onChange={() => toggleSubheading(section.id, subheading.id)}
                                        className="mr-2 h-3 w-3 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                      />
                                      <div className="flex-1">
                                        <div className="flex items-center justify-between">
                                          <div>
                                            <div className="text-sm font-medium text-gray-800">{subheading.title}</div>
                                            <div className="text-xs text-gray-600">{subheading.purpose}</div>
                                          </div>
                                          <button
                                            onClick={() => togglePromptBox(subheadingKey)}
                                            className="ml-2 p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-100 rounded-full transition-colors"
                                            title="Add custom prompt for this subheading"
                                          >
                                            <PlusIcon className="w-3 h-3" />
                                          </button>
                                        </div>
                                      </div>
                                    </div>
                                    <button
                                      onClick={() => removeSubheading(section.id, subheading.id)}
                                      className="text-red-500 hover:text-red-700 text-sm ml-2"
                                    >
                                      Remove
                                    </button>
                                  </div>

                                  {/* Subheading Custom Prompt Box */}
                                  {showPromptBox[subheadingKey] && (
                                    <div className="ml-4">
                                      <textarea
                                        value={headingCustomPrompts[subheadingKey] || ''}
                                        onChange={(e) => updateCustomPrompt(subheadingKey, e.target.value)}
                                        placeholder={`Enter custom instructions for "${subheading.title}" (e.g., "List 5 key points in bullet format")`}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                        rows="2"
                                      />
                                      <p className="text-xs text-gray-500 mt-1">
                                        This prompt will be applied specifically to the "{subheading.title}" subheading
                                      </p>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Generate SRS Button */}
        <div className="text-center">
          <p className="text-sm text-gray-500 mb-4">
            Selected {getAllSelectedHeadings().length} headings • Generate SRS directly
          </p>
          
          <div className="mt-4">
            <button
              onClick={generateSRS}
              disabled={generatingSRS || getAllSelectedHeadings().length === 0}
              className="bg-green-600 text-white px-8 py-3 rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center mx-auto space-x-2 text-lg font-medium"
            >
              {generatingSRS ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  <span>Generating SRS...</span>
                </>
              ) : (
                <>
                  <SparklesIcon className="w-5 h-5" />
                  <span>Generate SRS Document</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Diagram Manager - Show after successful SRS generation */}
        {showDiagramManager && generatedDocumentId && (
          <div className="mt-8">
            <DiagramManager
              documentId={generatedDocumentId}
              generatedDocumentPath={`generated_docs/generated_srs_${generatedDocumentId}.docx`}
            />
          </div>
        )}


      </div>
    </div>
  );
};

export default SRSHeadingsEditor; 