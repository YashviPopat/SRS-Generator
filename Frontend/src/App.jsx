import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Home from './pages/Home';
import DocumentUpload from './pages/DocumentUpload';
import SRSHeadingsEditor from './pages/SRSHeadingsEditor';
import Editor from './pages/Editor';
import Comparison from './pages/Comparison';
import SRSGenerator from './pages/SRSGenerator';
import './App.css';
import { DocumentDataProvider } from './DocumentDataContext';

function App() {
  return (
    <Router>
      <DocumentDataProvider>
        <div className="min-h-screen bg-gray-50">
          {/* Toast notifications */}
          <Toaster 
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                duration: 3000,
                iconTheme: {
                  primary: '#10b981',
                  secondary: '#fff',
                },
              },
              error: {
                duration: 5000,
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#fff',
                },
              },
            }}
          />
          {/* Main content */}
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/upload" element={<DocumentUpload />} />
            <Route path="/headings-editor" element={<SRSHeadingsEditor />} />
            <Route path="/editor" element={<Editor />} />
            <Route path="/comparison" element={<Comparison />} />
            <Route path="/srs-generator" element={<SRSGenerator />} />
          </Routes>
        </div>
      </DocumentDataProvider>
    </Router>
  );
}

export default App; 