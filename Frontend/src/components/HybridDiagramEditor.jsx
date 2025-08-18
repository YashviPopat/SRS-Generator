import React, { useState, useEffect, useRef } from 'react';
import { toast } from 'react-hot-toast';

const HybridDiagramEditor = ({ 
  isOpen, 
  onClose, 
  initialMermaidCode = '', 
  diagramType = 'flowchart',
  onSave 
}) => {
  const [mermaidCode, setMermaidCode] = useState(initialMermaidCode);
  const [selectedTheme, setSelectedTheme] = useState('default');
  const [isExporting, setIsExporting] = useState(false);
  const [availableThemes, setAvailableThemes] = useState([]);
  const [editMode, setEditMode] = useState('code'); // 'code', 'visual', 'hybrid'
  const [diagramData, setDiagramData] = useState(null);
  const diagramRef = useRef(null);
  const excalidrawRef = useRef(null);

  // Load available themes
  useEffect(() => {
    fetchThemes();
    if (initialMermaidCode) {
      setMermaidCode(initialMermaidCode);
      renderDiagram();
    }
  }, [initialMermaidCode]);

  useEffect(() => {
    if (mermaidCode.trim()) {
      renderDiagram();
    }
  }, [mermaidCode, selectedTheme]);

  const fetchThemes = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/diagram/themes');
      const data = await response.json();
      setAvailableThemes(data.themes || []);
    } catch (error) {
      console.error('Failed to fetch themes:', error);
      setAvailableThemes([
        { id: 'default', name: 'Default' },
        { id: 'dark', name: 'Dark' },
        { id: 'forest', name: 'Forest' }
      ]);
    }
  };

  const renderDiagram = async () => {
    if (!mermaidCode.trim() || !diagramRef.current) return;

    try {
      const response = await fetch('http://localhost:8000/api/diagram/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mermaidCode,
          theme: selectedTheme,
          format: 'svg'
        })
      });

      if (response.ok) {
        const svgContent = await response.text();
        diagramRef.current.innerHTML = svgContent;
      }
    } catch (error) {
      console.error('Render error:', error);
    }
  };

  const convertToVisualEditor = async () => {
    try {
      setIsExporting(true);
      
      // Convert Mermaid to a format suitable for visual editing
      const response = await fetch('http://localhost:8000/api/diagram/convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mermaidCode,
          targetFormat: 'excalidraw' // or 'drawio', 'cytoscape'
        })
      });

      if (response.ok) {
        const visualData = await response.json();
        setDiagramData(visualData);
        setEditMode('visual');
        toast.success('Converted to visual editor!');
      }
    } catch (error) {
      console.error('Conversion error:', error);
      toast.error('Failed to convert diagram');
    } finally {
      setIsExporting(false);
    }
  };

  const convertBackToMermaid = async () => {
    try {
      setIsExporting(true);
      
      // Convert visual editor data back to Mermaid
      const response = await fetch('http://localhost:8000/api/diagram/convert-back', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          visualData: diagramData,
          sourceFormat: 'excalidraw',
          targetFormat: 'mermaid'
        })
      });

      if (response.ok) {
        const result = await response.json();
        setMermaidCode(result.mermaidCode);
        setEditMode('code');
        toast.success('Converted back to Mermaid!');
      }
    } catch (error) {
      console.error('Conversion error:', error);
      toast.error('Failed to convert back to Mermaid');
    } finally {
      setIsExporting(false);
    }
  };

  const exportDiagram = async (format) => {
    try {
      setIsExporting(true);

      const response = await fetch('http://localhost:8000/api/diagram/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mermaidCode,
          theme: selectedTheme,
          format,
          diagramType
        })
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `diagram.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        toast.success(`Exported as ${format.toUpperCase()}`);
      }
    } catch (error) {
      console.error('Export error:', error);
      toast.error('Export failed');
    } finally {
      setIsExporting(false);
    }
  };

  // Draw.io export function removed

  const generateWithAI = async () => {
    try {
      setIsExporting(true);

      const prompt = window.prompt(
        'Describe the diagram you want to generate:',
        'Create a user authentication flow diagram'
      );

      if (!prompt) return;

      const response = await fetch('http://localhost:8000/api/diagram/generate-ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          diagramType,
          format: 'mermaid'
        })
      });

      if (response.ok) {
        const result = await response.json();
        setMermaidCode(result.mermaidCode);
        toast.success('AI diagram generated!');
      }
    } catch (error) {
      console.error('AI generation error:', error);
      toast.error('Failed to generate diagram with AI');
    } finally {
      setIsExporting(false);
    }
  };

  const handleSave = () => {
    if (onSave) {
      onSave({
        mermaidCode,
        theme: selectedTheme,
        diagramType,
        visualData: diagramData
      });
      toast.success('Diagram saved successfully');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-7xl h-5/6 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-semibold text-gray-800">
              Hybrid Diagram Editor - {diagramType}
            </h2>
            
            {/* Edit Mode Selector */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setEditMode('code')}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  editMode === 'code' 
                    ? 'bg-blue-600 text-white' 
                    : 'text-gray-600 hover:bg-gray-200'
                }`}
              >
                📝 Code
              </button>
              <button
                onClick={convertToVisualEditor}
                disabled={isExporting}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  editMode === 'visual' 
                    ? 'bg-green-600 text-white' 
                    : 'text-gray-600 hover:bg-gray-200'
                }`}
              >
                🎨 Visual
              </button>
              <button
                onClick={() => setEditMode('hybrid')}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  editMode === 'hybrid' 
                    ? 'bg-purple-600 text-white' 
                    : 'text-gray-600 hover:bg-gray-200'
                }`}
              >
                🔄 Hybrid
              </button>
            </div>
          </div>
          
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-4 p-4 border-b bg-gray-50">
          {/* Theme Selector */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Theme:</label>
            <select
              value={selectedTheme}
              onChange={(e) => setSelectedTheme(e.target.value)}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm"
            >
              {availableThemes.map(theme => (
                <option key={theme.id} value={theme.id}>
                  {theme.name}
                </option>
              ))}
            </select>
          </div>

          {/* Mode-specific controls */}
          {editMode === 'visual' && (
            <button
              onClick={convertBackToMermaid}
              disabled={isExporting}
              className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              ← Back to Code
            </button>
          )}

          {/* AI Generation */}
          <button
            onClick={generateWithAI}
            disabled={isExporting}
            className="px-3 py-1 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded text-sm hover:from-purple-700 hover:to-blue-700 disabled:opacity-50"
          >
            🤖 Generate with AI
          </button>

          {/* Export Options */}
          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={() => exportDiagram('png')}
              disabled={isExporting}
              className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              Export PNG
            </button>
            <button
              onClick={() => exportDiagram('svg')}
              disabled={isExporting}
              className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
            >
              Export SVG
            </button>
            <button
              onClick={handleSave}
              className="px-3 py-1 bg-purple-600 text-white rounded text-sm hover:bg-purple-700"
            >
              Save Changes
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Code Mode */}
          {editMode === 'code' && (
            <>
              <div className="w-1/2 flex flex-col border-r">
                <div className="p-3 bg-gray-100 border-b">
                  <h3 className="font-medium text-gray-700">Mermaid Code</h3>
                </div>
                <textarea
                  value={mermaidCode}
                  onChange={(e) => setMermaidCode(e.target.value)}
                  className="flex-1 p-4 font-mono text-sm resize-none focus:outline-none"
                  placeholder="Enter your Mermaid diagram code here..."
                  spellCheck={false}
                />
              </div>
              <div className="w-1/2 flex flex-col">
                <div className="p-3 bg-gray-100 border-b">
                  <h3 className="font-medium text-gray-700">Live Preview</h3>
                </div>
                <div className="flex-1 p-4 overflow-auto bg-white">
                  <div ref={diagramRef} className="w-full h-full flex items-center justify-center">
                    {!mermaidCode.trim() && (
                      <div className="text-gray-500 text-center">
                        <p>Enter Mermaid code to see preview</p>
                        <p className="text-sm mt-2">Click "🎨 Visual" to switch to visual editing</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Visual Mode */}
          {editMode === 'visual' && (
            <div className="w-full flex flex-col">
              <div className="p-3 bg-gray-100 border-b">
                <h3 className="font-medium text-gray-700">Visual Editor</h3>
              </div>
              <div className="flex-1 bg-white flex items-center justify-center">
                <div className="text-gray-500 text-center">
                  <p>Visual Editor</p>
                  <p className="text-sm">Coming Soon</p>
                </div>
              </div>
            </div>
          )}

          {/* Hybrid Mode */}
          {editMode === 'hybrid' && (
            <div className="w-full flex flex-col">
              <div className="p-3 bg-gray-100 border-b">
                <h3 className="font-medium text-gray-700">Hybrid View - Code + Visual</h3>
              </div>
              <div className="flex-1 flex">
                <div className="w-1/3 border-r">
                  <textarea
                    value={mermaidCode}
                    onChange={(e) => setMermaidCode(e.target.value)}
                    className="w-full h-full p-3 font-mono text-xs resize-none focus:outline-none"
                    placeholder="Mermaid code..."
                  />
                </div>
                <div className="w-1/3 border-r">
                  <div ref={diagramRef} className="w-full h-full p-2 overflow-auto"></div>
                </div>
                <div className="w-1/3 flex items-center justify-center bg-gray-50">
                  <div className="text-gray-500 text-center">
                    <p>Visual Editor</p>
                    <p className="text-sm">Coming Soon</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HybridDiagramEditor;
