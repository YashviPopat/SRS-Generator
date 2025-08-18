import React, { useState, useEffect, useRef } from 'react';
import { toast } from 'react-hot-toast';

const DiagramEditor = ({ 
  initialMermaidCode = '', 
  diagramType = 'flowchart',
  onSave,
  onClose 
}) => {
  const [mermaidCode, setMermaidCode] = useState(initialMermaidCode);
  const [isValid, setIsValid] = useState(true);
  const [validationMessage, setValidationMessage] = useState('');
  const [selectedTheme, setSelectedTheme] = useState('default');
  const [isExporting, setIsExporting] = useState(false);
  const [availableThemes, setAvailableThemes] = useState([]);
  const [showColorPanel, setShowColorPanel] = useState(false);
  const [customColors, setCustomColors] = useState({
    primary: '#0066cc',
    secondary: '#28a745',
    accent: '#ffc107',
    background: '#ffffff',
    text: '#333333'
  });
  const [autoApplyColors, setAutoApplyColors] = useState(false);

  // Text and Font customization
  const [textSettings, setTextSettings] = useState({
    fontFamily: 'Arial',
    fontSize: '14',
    fontWeight: 'normal',
    textAlign: 'center',
    lineHeight: '1.2'
  });

  // Shape and styling
  const [shapeSettings, setShapeSettings] = useState({
    borderWidth: '2',
    borderRadius: '4',
    padding: '8',
    shadowEnabled: false,
    shadowColor: '#00000020',
    shadowOffset: '2'
  });

  // Advanced customization panel states
  const [activeCustomPanel, setActiveCustomPanel] = useState('colors'); // 'colors', 'text', 'shapes', 'layout'

  // Canvas mode states
  const [canvasMode, setCanvasMode] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const diagramRef = useRef(null);
  const editorRef = useRef(null);

  // Load available themes
  useEffect(() => {
    fetchThemes();
  }, []);

  // Render diagram when code or theme changes
  useEffect(() => {
    if (mermaidCode.trim()) {
      renderDiagram();
    }
  }, [mermaidCode, selectedTheme]);

  // Auto-apply all customizations when they change
  useEffect(() => {
    if (autoApplyColors && mermaidCode) {
      const timeoutId = setTimeout(() => {
        applyAllCustomizations();
      }, 500); // Debounce to avoid too many updates

      return () => clearTimeout(timeoutId);
    }
  }, [customColors, textSettings, shapeSettings, autoApplyColors]);

  const fetchThemes = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/diagram/themes');
      const data = await response.json();
      setAvailableThemes(data.themes || []);
    } catch (error) {
      console.error('Failed to fetch themes:', error);
      setAvailableThemes([
        { id: 'default', name: 'Default', description: 'Standard theme' },
        { id: 'dark', name: 'Dark', description: 'Dark theme' },
        { id: 'forest', name: 'Forest', description: 'Forest theme' }
      ]);
    }
  };

  const renderDiagram = async () => {
    if (!diagramRef.current || !mermaidCode.trim()) return;

    try {
      // Clear previous diagram
      diagramRef.current.innerHTML = '<div class="flex items-center justify-center p-4"><div class="text-gray-500">Generating preview...</div></div>';

      // Use server-side rendering for preview
      const response = await fetch('http://localhost:8000/api/diagram/export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mermaid_code: mermaidCode,
          format: 'svg',
          theme: selectedTheme,
          width: 600,
          height: 400
        }),
      });

      const result = await response.json();

      if (result.success) {
        diagramRef.current.innerHTML = result.data;
        setIsValid(true);
        setValidationMessage('Diagram is valid');
      } else {
        throw new Error('Failed to render diagram');
      }
    } catch (error) {
      console.error('Diagram rendering error:', error);
      setIsValid(false);
      setValidationMessage(`Rendering error: ${error.message}`);
      diagramRef.current.innerHTML = `
        <div class="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          <p class="font-semibold">Diagram Error</p>
          <p class="text-sm">${error.message}</p>
        </div>
      `;
    }
  };

  const validateDiagram = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/diagram/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mermaid_code: mermaidCode,
          diagram_type: diagramType,
          theme: selectedTheme
        }),
      });

      const result = await response.json();
      setIsValid(result.valid);
      setValidationMessage(result.message);
      
      if (!result.valid) {
        toast.error(result.message);
      }
    } catch (error) {
      console.error('Validation error:', error);
      setIsValid(false);
      setValidationMessage('Validation failed');
    }
  };

  const applyCustomColors = () => {
    applyAllCustomizations();
  };

  const applyAllCustomizations = () => {
    // Apply all customizations: colors, fonts, shapes
    let customizedCode = mermaidCode;

    // Build comprehensive theme configuration
    const customThemeConfig = `%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '${customColors.primary}',
    'primaryTextColor': '${customColors.text}',
    'primaryBorderColor': '${customColors.primary}',
    'lineColor': '${customColors.secondary}',
    'secondaryColor': '${customColors.secondary}',
    'tertiaryColor': '${customColors.accent}',
    'background': '${customColors.background}',
    'mainBkg': '${customColors.background}',
    'secondaryBkg': '${customColors.secondary}20',
    'tertiaryBkg': '${customColors.accent}20',
    'fontFamily': '${textSettings.fontFamily}',
    'fontSize': '${textSettings.fontSize}px',
    'fontWeight': '${textSettings.fontWeight}',
    'textAlign': '${textSettings.textAlign}',
    'lineHeight': '${textSettings.lineHeight}',
    'primaryBorderWidth': '${shapeSettings.borderWidth}px',
    'borderRadius': '${shapeSettings.borderRadius}px'
  }
}}%%`;

    // Insert theme config at the beginning
    if (!customizedCode.includes('%%{init:')) {
      customizedCode = customThemeConfig + '\n' + customizedCode;
    } else {
      // Replace existing theme config
      customizedCode = customizedCode.replace(/%%\{init:.*?%%/s, customThemeConfig);
    }

    setMermaidCode(customizedCode);
    renderDiagram(customizedCode, 'base');
  };

  const applyTextPreset = (preset) => {
    const presets = {
      'professional': {
        fontFamily: 'Arial',
        fontSize: '14',
        fontWeight: 'bold',
        textAlign: 'center',
        lineHeight: '1.3'
      },
      'modern': {
        fontFamily: 'Helvetica',
        fontSize: '16',
        fontWeight: 'normal',
        textAlign: 'left',
        lineHeight: '1.4'
      },
      'technical': {
        fontFamily: 'Courier New',
        fontSize: '12',
        fontWeight: 'normal',
        textAlign: 'center',
        lineHeight: '1.2'
      },
      'presentation': {
        fontFamily: 'Georgia',
        fontSize: '18',
        fontWeight: 'bold',
        textAlign: 'center',
        lineHeight: '1.5'
      }
    };

    if (presets[preset]) {
      setTextSettings(presets[preset]);
    }
  };

  const resetColors = () => {
    setCustomColors({
      primary: '#0066cc',
      secondary: '#28a745',
      accent: '#ffc107',
      background: '#ffffff',
      text: '#333333'
    });
  };

  const applyColorPreset = (preset) => {
    const presets = {
      'blue': {
        primary: '#2563eb',
        secondary: '#3b82f6',
        accent: '#60a5fa',
        background: '#ffffff',
        text: '#1e40af'
      },
      'green': {
        primary: '#059669',
        secondary: '#10b981',
        accent: '#34d399',
        background: '#ffffff',
        text: '#047857'
      },
      'purple': {
        primary: '#7c3aed',
        secondary: '#8b5cf6',
        accent: '#a78bfa',
        background: '#ffffff',
        text: '#5b21b6'
      },
      'dark': {
        primary: '#6366f1',
        secondary: '#8b5cf6',
        accent: '#f59e0b',
        background: '#1f2937',
        text: '#f9fafb'
      }
    };

    if (presets[preset]) {
      setCustomColors(presets[preset]);
    }
  };

  const applyTemplate = (templateCode) => {
    setMermaidCode(templateCode);
    renderDiagram(templateCode, selectedTheme);
  };

  // Text editing helpers
  const replaceTextInDiagram = (oldText, newText) => {
    const updatedCode = mermaidCode.replace(new RegExp(oldText, 'g'), newText);
    setMermaidCode(updatedCode);
  };

  const addNodeToDiagram = (nodeText, nodeType = 'rect') => {
    const nodeId = `node_${Date.now()}`;
    let addition = '';

    if (mermaidCode.includes('flowchart') || mermaidCode.includes('graph')) {
      addition = `\n    ${nodeId}["${nodeText}"]`;
    } else if (mermaidCode.includes('sequenceDiagram')) {
      addition = `\n    participant ${nodeId} as ${nodeText}`;
    } else if (mermaidCode.includes('erDiagram')) {
      addition = `\n    ${nodeId.toUpperCase()} {\n        id INT\n        name VARCHAR\n    }`;
    }

    setMermaidCode(mermaidCode + addition);
  };

  const extractEditableElements = () => {
    // Extract text elements that can be edited
    const elements = [];
    const lines = mermaidCode.split('\n');

    lines.forEach((line, index) => {
      // Find text in quotes or brackets
      const textMatches = line.match(/["'\[](.*?)["'\]]/g);
      if (textMatches) {
        textMatches.forEach(match => {
          const text = match.slice(1, -1); // Remove quotes/brackets
          if (text.trim()) {
            elements.push({
              text,
              line: index + 1,
              original: match,
              fullLine: line
            });
          }
        });
      }
    });

    return elements;
  };

  // Canvas control functions
  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev + 0.2, 3));
  };

  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev - 0.2, 0.3));
  };

  const handleZoomReset = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  };

  const handleMouseDown = (e) => {
    if (canvasMode) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging && canvasMode) {
      setPanOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const toggleCanvasMode = () => {
    setCanvasMode(!canvasMode);
    if (!canvasMode) {
      // Reset zoom and pan when entering canvas mode
      setZoomLevel(1);
      setPanOffset({ x: 0, y: 0 });
    }
  };

  const handleWheel = (e) => {
    if (canvasMode) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      setZoomLevel(prev => Math.max(0.3, Math.min(3, prev + delta)));
    }
  };

  const exportDiagram = async (format) => {
    setIsExporting(true);
    try {
      const response = await fetch('http://localhost:8000/api/diagram/export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mermaid_code: mermaidCode,
          format: format,
          theme: selectedTheme,
          width: 800,
          height: 600
        }),
      });

      const result = await response.json();
      
      if (result.success) {
        // Create download link
        let blob;
        let url;
        
        if (format === 'png') {
          // Convert base64 to blob
          const binaryString = atob(result.data);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          blob = new Blob([bytes], { type: result.content_type });
        } else {
          // Text-based formats
          blob = new Blob([result.data], { type: result.content_type });
        }
        
        url = URL.createObjectURL(blob);
        
        // Trigger download
        const a = document.createElement('a');
        a.href = url;
        a.download = result.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        toast.success(`Diagram exported as ${format.toUpperCase()}`);
      } else {
        toast.error('Export failed');
      }
    } catch (error) {
      console.error('Export error:', error);
      toast.error('Export failed');
    } finally {
      setIsExporting(false);
    }
  };

  const insertTemplate = (template) => {
    const templates = {
      // SRS-specific templates
      'user-flow': `sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as Auth Service
    participant D as Database

    U->>F: Enter credentials
    F->>A: Validate login
    A->>D: Check user data
    D-->>A: User found
    A-->>F: Auth token
    F-->>U: Login successful`,

      'system-arch': `flowchart TB
    subgraph "Client Layer"
        UI[User Interface]
        Mobile[Mobile App]
    end

    subgraph "Application Layer"
        API[API Gateway]
        Auth[Authentication]
        BL[Business Logic]
    end

    subgraph "Data Layer"
        DB[(Database)]
        Cache[(Cache)]
    end

    UI --> API
    Mobile --> API
    API --> Auth
    API --> BL
    BL --> DB
    BL --> Cache`,

      'data-flow': `flowchart LR
    Input[User Input] --> Validation{Validate Data}
    Validation -->|Valid| Process[Process Request]
    Validation -->|Invalid| Error[Return Error]
    Process --> Store[(Store Data)]
    Store --> Response[Generate Response]
    Response --> Output[Send to User]`,

      'use-case': `flowchart TD
    User((User)) --> Login[Login]
    User --> Browse[Browse Products]
    User --> Purchase[Make Purchase]

    Admin((Admin)) --> Manage[Manage Users]
    Admin --> Reports[Generate Reports]

    Login --> Auth{Authenticate}
    Auth -->|Success| Dashboard[User Dashboard]
    Auth -->|Fail| LoginError[Login Error]`,

      // General templates
      flowchart: `flowchart TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Process]
    B -->|No| D[End]
    C --> D`,

      sequence: `sequenceDiagram
    participant A as User
    participant B as System
    A->>B: Request
    B-->>A: Response`,

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
    }`
    };

    setMermaidCode(templates[template] || templates.flowchart);
  };

  const handleSave = () => {
    if (isValid && onSave) {
      onSave({
        mermaidCode,
        theme: selectedTheme,
        diagramType
      });
      toast.success('Diagram saved successfully');
    } else {
      toast.error('Please fix diagram errors before saving');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-7xl h-5/6 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-semibold text-gray-800">
            Diagram Editor - {diagramType}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        </div>

        {/* Toolbar */}
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

          {/* Templates */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Template:</label>
            <select
              onChange={(e) => e.target.value && insertTemplate(e.target.value)}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm"
              defaultValue=""
            >
              <option value="">Select template...</option>
              <optgroup label="SRS Specific">
                <option value="user-flow">User Authentication Flow</option>
                <option value="system-arch">System Architecture</option>
                <option value="data-flow">Data Flow Diagram</option>
                <option value="use-case">Use Case Diagram</option>
              </optgroup>
              <optgroup label="General">
                <option value="flowchart">Flowchart</option>
                <option value="sequence">Sequence Diagram</option>
                <option value="er">ER Diagram</option>
                <option value="class">Class Diagram</option>
              </optgroup>
            </select>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => addNodeToDiagram('User', 'actor')}
              className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs hover:bg-blue-200"
              title="Add User Actor"
            >
              👤 User
            </button>
            <button
              onClick={() => addNodeToDiagram('System', 'system')}
              className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs hover:bg-green-200"
              title="Add System Component"
            >
              🖥️ System
            </button>
            <button
              onClick={() => addNodeToDiagram('Database', 'database')}
              className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-xs hover:bg-yellow-200"
              title="Add Database"
            >
              🗄️ DB
            </button>
          </div>

          {/* Canvas Mode Toggle */}
          <button
            onClick={toggleCanvasMode}
            className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
              canvasMode
                ? 'bg-green-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            🖼️ {canvasMode ? 'Exit Canvas' : 'Canvas View'}
          </button>

          {/* Advanced Customization Toggle */}
          {!canvasMode && (
            <button
              onClick={() => setShowColorPanel(!showColorPanel)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                showColorPanel
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              🎨 Customize
            </button>
          )}

          {/* Export Options */}
          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={() => exportDiagram('png')}
              disabled={isExporting || !isValid}
              className="px-3 py-1 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              Export PNG
            </button>
            <button
              onClick={() => exportDiagram('svg')}
              disabled={isExporting || !isValid}
              className="px-3 py-1 bg-green-600 text-white rounded-md text-sm hover:bg-green-700 disabled:opacity-50"
            >
              Export SVG
            </button>
            <button
              onClick={() => exportDiagram('mermaid')}
              disabled={isExporting}
              className="px-3 py-1 bg-purple-600 text-white rounded-md text-sm hover:bg-purple-700 disabled:opacity-50"
            >
              Export Code
            </button>
          </div>
        </div>

        {/* Canvas Controls Panel */}
        {canvasMode && (
          <div className="p-3 bg-gray-800 text-white border-b flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium">Canvas Controls:</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleZoomOut}
                  className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs"
                >
                  🔍−
                </button>
                <span className="text-xs bg-gray-700 px-2 py-1 rounded">
                  {Math.round(zoomLevel * 100)}%
                </span>
                <button
                  onClick={handleZoomIn}
                  className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs"
                >
                  🔍+
                </button>
                <button
                  onClick={handleZoomReset}
                  className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs"
                >
                  Reset
                </button>
              </div>
            </div>
            <div className="text-xs text-gray-300">
              💡 Drag to pan • Scroll to zoom • Click elements to edit
            </div>
          </div>
        )}

        {/* Advanced Customization Panel */}
        {showColorPanel && !canvasMode && (
          <div className="p-4 bg-gray-50 border-b">
            {/* Tab Navigation */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex gap-1 bg-white rounded-lg p-1 border">
                {[
                  { key: 'colors', label: '🎨 Colors', icon: '🎨' },
                  { key: 'text', label: '📝 Text & Fonts', icon: '📝' },
                  { key: 'shapes', label: '⬜ Shapes', icon: '⬜' },
                  { key: 'elements', label: '🔧 Elements', icon: '🔧' }
                ].map(tab => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveCustomPanel(tab.key)}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                      activeCustomPanel === tab.key
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {tab.icon} {tab.label.split(' ')[1]}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-3">
                {/* Auto-apply toggle */}
                <label className="flex items-center gap-1 text-xs">
                  <input
                    type="checkbox"
                    checked={autoApplyColors}
                    onChange={(e) => setAutoApplyColors(e.target.checked)}
                    className="rounded"
                  />
                  Auto-apply
                </label>

                <div className="flex gap-2">
                  <button
                    onClick={applyAllCustomizations}
                    disabled={autoApplyColors}
                    className={`px-3 py-1 rounded text-xs ${
                      autoApplyColors
                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                        : 'bg-blue-600 text-white hover:bg-blue-700'
                    }`}
                  >
                    Apply All
                  </button>
                  <button
                    onClick={resetColors}
                    className="px-3 py-1 bg-gray-500 text-white rounded text-xs hover:bg-gray-600"
                  >
                    Reset
                  </button>
                </div>
              </div>
            </div>

            {/* Tab Content */}
            <div className="min-h-48">
              {/* Colors Tab */}
              {activeCustomPanel === 'colors' && (
                <div>
                  {/* Color Presets */}
                  <div className="mb-4">
                    <label className="text-xs font-medium text-gray-600 mb-2 block">Quick Presets:</label>
                    <div className="flex gap-2 flex-wrap">
                      {[
                        { name: 'Blue', key: 'blue', colors: ['#2563eb', '#3b82f6', '#60a5fa'] },
                        { name: 'Green', key: 'green', colors: ['#059669', '#10b981', '#34d399'] },
                        { name: 'Purple', key: 'purple', colors: ['#7c3aed', '#8b5cf6', '#a78bfa'] },
                        { name: 'Dark', key: 'dark', colors: ['#6366f1', '#8b5cf6', '#f59e0b'] }
                      ].map(preset => (
                        <button
                          key={preset.key}
                          onClick={() => applyColorPreset(preset.key)}
                          className="flex items-center gap-1 px-2 py-1 text-xs border rounded hover:bg-gray-50"
                        >
                          <div className="flex">
                            {preset.colors.map((color, i) => (
                              <div
                                key={i}
                                className="w-3 h-3 rounded-full border border-white"
                                style={{ backgroundColor: color, marginLeft: i > 0 ? '-2px' : '0' }}
                              />
                            ))}
                          </div>
                          {preset.name}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-5 gap-4">
                    {Object.entries(customColors).map(([colorKey, colorValue]) => (
                      <div key={colorKey} className="flex flex-col items-center">
                        <label className="text-xs font-medium text-gray-600 mb-2 capitalize">
                          {colorKey}
                        </label>
                        <input
                          type="color"
                          value={colorValue}
                          onChange={(e) => setCustomColors(prev => ({
                            ...prev,
                            [colorKey]: e.target.value
                          }))}
                          className="w-16 h-10 rounded border border-gray-300 cursor-pointer"
                        />
                        <span className="text-xs text-gray-500 mt-1 font-mono">{colorValue}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Text & Fonts Tab */}
              {activeCustomPanel === 'text' && (
                <div>
                  {/* Font Presets */}
                  <div className="mb-4">
                    <label className="text-xs font-medium text-gray-600 mb-2 block">Font Presets:</label>
                    <div className="flex gap-2 flex-wrap">
                      {[
                        { name: 'Professional', key: 'professional' },
                        { name: 'Modern', key: 'modern' },
                        { name: 'Technical', key: 'technical' },
                        { name: 'Presentation', key: 'presentation' }
                      ].map(preset => (
                        <button
                          key={preset.key}
                          onClick={() => applyTextPreset(preset.key)}
                          className="px-3 py-1 text-xs border rounded hover:bg-gray-50"
                        >
                          {preset.name}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 block">Font Family:</label>
                      <select
                        value={textSettings.fontFamily}
                        onChange={(e) => setTextSettings(prev => ({ ...prev, fontFamily: e.target.value }))}
                        className="w-full px-2 py-1 text-xs border rounded"
                      >
                        <option value="Arial">Arial</option>
                        <option value="Helvetica">Helvetica</option>
                        <option value="Times New Roman">Times New Roman</option>
                        <option value="Georgia">Georgia</option>
                        <option value="Courier New">Courier New</option>
                        <option value="Verdana">Verdana</option>
                        <option value="Trebuchet MS">Trebuchet MS</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 block">Font Size:</label>
                      <input
                        type="range"
                        min="10"
                        max="24"
                        value={textSettings.fontSize}
                        onChange={(e) => setTextSettings(prev => ({ ...prev, fontSize: e.target.value }))}
                        className="w-full"
                      />
                      <span className="text-xs text-gray-500">{textSettings.fontSize}px</span>
                    </div>

                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 block">Font Weight:</label>
                      <select
                        value={textSettings.fontWeight}
                        onChange={(e) => setTextSettings(prev => ({ ...prev, fontWeight: e.target.value }))}
                        className="w-full px-2 py-1 text-xs border rounded"
                      >
                        <option value="normal">Normal</option>
                        <option value="bold">Bold</option>
                        <option value="lighter">Light</option>
                        <option value="bolder">Extra Bold</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 block">Text Align:</label>
                      <select
                        value={textSettings.textAlign}
                        onChange={(e) => setTextSettings(prev => ({ ...prev, textAlign: e.target.value }))}
                        className="w-full px-2 py-1 text-xs border rounded"
                      >
                        <option value="left">Left</option>
                        <option value="center">Center</option>
                        <option value="right">Right</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}

              {/* Shapes Tab */}
              {activeCustomPanel === 'shapes' && (
                <div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 block">Border Width:</label>
                      <input
                        type="range"
                        min="1"
                        max="8"
                        value={shapeSettings.borderWidth}
                        onChange={(e) => setShapeSettings(prev => ({ ...prev, borderWidth: e.target.value }))}
                        className="w-full"
                      />
                      <span className="text-xs text-gray-500">{shapeSettings.borderWidth}px</span>
                    </div>

                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 block">Border Radius:</label>
                      <input
                        type="range"
                        min="0"
                        max="20"
                        value={shapeSettings.borderRadius}
                        onChange={(e) => setShapeSettings(prev => ({ ...prev, borderRadius: e.target.value }))}
                        className="w-full"
                      />
                      <span className="text-xs text-gray-500">{shapeSettings.borderRadius}px</span>
                    </div>

                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 block">Padding:</label>
                      <input
                        type="range"
                        min="4"
                        max="20"
                        value={shapeSettings.padding}
                        onChange={(e) => setShapeSettings(prev => ({ ...prev, padding: e.target.value }))}
                        className="w-full"
                      />
                      <span className="text-xs text-gray-500">{shapeSettings.padding}px</span>
                    </div>

                    <div>
                      <label className="flex items-center gap-2 text-xs font-medium text-gray-600">
                        <input
                          type="checkbox"
                          checked={shapeSettings.shadowEnabled}
                          onChange={(e) => setShapeSettings(prev => ({ ...prev, shadowEnabled: e.target.checked }))}
                          className="rounded"
                        />
                        Enable Shadow
                      </label>
                    </div>
                  </div>
                </div>
              )}

              {/* Elements Tab */}
              {activeCustomPanel === 'elements' && (
                <div>
                  <div className="mb-4">
                    <label className="text-xs font-medium text-gray-600 mb-2 block">Editable Text Elements:</label>
                    <div className="max-h-32 overflow-y-auto border rounded p-2 bg-white">
                      {extractEditableElements().map((element, index) => (
                        <div key={index} className="flex items-center gap-2 mb-2 p-1 hover:bg-gray-50 rounded">
                          <span className="text-xs text-gray-500 w-8">L{element.line}</span>
                          <input
                            type="text"
                            value={element.text}
                            onChange={(e) => replaceTextInDiagram(element.text, e.target.value)}
                            className="flex-1 px-2 py-1 text-xs border rounded"
                            placeholder="Edit text..."
                          />
                        </div>
                      ))}
                      {extractEditableElements().length === 0 && (
                        <div className="text-xs text-gray-400 text-center py-2">
                          No editable text elements found
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => addNodeToDiagram('New Node')}
                      className="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700"
                    >
                      + Add Node
                    </button>
                    <button
                      onClick={() => addNodeToDiagram('New Process', 'process')}
                      className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
                    >
                      + Add Process
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="mt-3 text-xs text-gray-600 bg-blue-50 p-2 rounded">
              💡 <strong>Tip:</strong> Adjust colors above and click "Apply Colors" to see changes in the live preview
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Code Editor - Hidden in canvas mode */}
          {!canvasMode && (
            <div className="w-1/2 flex flex-col border-r">
              <div className="p-3 bg-gray-100 border-b">
                <h3 className="font-medium text-gray-700">Mermaid Code</h3>
                <div className={`text-sm mt-1 ${isValid ? 'text-green-600' : 'text-red-600'}`}>
                  {validationMessage}
                </div>
              </div>
              <textarea
                ref={editorRef}
                value={mermaidCode}
                onChange={(e) => setMermaidCode(e.target.value)}
                className="flex-1 p-4 font-mono text-sm resize-none focus:outline-none"
                placeholder="Enter your Mermaid diagram code here..."
                spellCheck={false}
              />
            </div>
          )}

          {/* Preview - Full width in canvas mode */}
          <div className={`${canvasMode ? 'w-full' : 'w-1/2'} flex flex-col`}>
            {!canvasMode && (
              <div className="p-3 bg-gray-100 border-b flex items-center justify-between">
                <h3 className="font-medium text-gray-700">🖼️ Live Preview</h3>
                <div className="text-xs text-gray-500">
                  Updates automatically
                </div>
              </div>
            )}

            <div
              className={`flex-1 bg-white relative overflow-hidden ${canvasMode ? '' : 'p-4'}`}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onWheel={handleWheel}
              style={{ cursor: canvasMode ? (isDragging ? 'grabbing' : 'grab') : 'default' }}
            >
              {/* Canvas-style grid background */}
              <div
                className={`absolute inset-0 ${canvasMode ? 'opacity-10' : 'opacity-5'}`}
                style={{
                  backgroundImage: `
                    linear-gradient(rgba(0,0,0,0.1) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(0,0,0,0.1) 1px, transparent 1px)
                  `,
                  backgroundSize: `${20 * zoomLevel}px ${20 * zoomLevel}px`,
                  transform: `translate(${panOffset.x}px, ${panOffset.y}px)`
                }}
              ></div>

              <div
                ref={diagramRef}
                className={`relative w-full h-full flex items-center justify-center ${
                  canvasMode
                    ? 'min-h-full'
                    : 'border-2 border-dashed border-gray-200 rounded-lg min-h-96'
                }`}
                style={{
                  transform: canvasMode
                    ? `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`
                    : 'none',
                  transformOrigin: 'center center'
                }}
              >
                {!mermaidCode.trim() && (
                  <div className="text-center text-gray-400">
                    <div className="text-4xl mb-2">🎨</div>
                    <div className="text-sm">
                      {canvasMode ? 'Canvas Mode - Full diagram view' : 'Start typing Mermaid code to see your diagram'}
                    </div>
                    <div className="text-xs mt-1 text-gray-300">
                      {canvasMode ? 'Use zoom controls and drag to navigate' : 'Use the color panel to customize appearance'}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t bg-gray-50">
          <div className="flex items-center gap-2">
            <button
              onClick={validateDiagram}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
            >
              Validate
            </button>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!isValid}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DiagramEditor;
