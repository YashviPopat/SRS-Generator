import React, { createContext, useContext, useState } from 'react';

const DocumentDataContext = createContext();

export const DocumentDataProvider = ({ children }) => {
  const [documentData, setDocumentData] = useState({
    documentId: null,
    standardHeadings: {},
    geminiSuggestions: {},
    uploadedFiles: [],
    extractedTextContent: {},
    projectTitle: '',
    projectDescription: '',
    // Selection state for headings
    selectedAiHeadings: {},
    selectedStandardHeadings: {},
    customSections: [],
    aiGeneratedHeadings: {},
  });

  return (
    <DocumentDataContext.Provider value={{ documentData, setDocumentData }}>
      {children}
    </DocumentDataContext.Provider>
  );
};

export const useDocumentData = () => useContext(DocumentDataContext); 