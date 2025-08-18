import { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { ArrowDownTrayIcon } from '@heroicons/react/24/outline';

const DiagramManager = ({ documentId }) => {
  const [diagrams, setDiagrams] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGeneratedDiagrams();
  }, [documentId]);

  const fetchGeneratedDiagrams = async () => {
    try {
      setLoading(true);
      console.log(`🔍 Fetching diagrams for document ID: ${documentId}`);

      const response = await fetch(`http://localhost:8000/api/document/${documentId}/diagrams`);
      console.log(`📡 Response status: ${response.status}`);

      const data = await response.json();
      console.log(`📊 Response data:`, data);

      if (data.success) {
        setDiagrams(data.diagrams || []);
        console.log(`✅ Set ${data.diagrams?.length || 0} diagrams`);
      } else {
        console.log(`⚠️ API returned success: false`);
      }
    } catch (error) {
      console.error('Failed to fetch diagrams:', error);
    } finally {
      setLoading(false);
    }
  };

  // Test download function
  const testDownload = () => {
    const testXml = `<?xml version="1.0" encoding="UTF-8"?>
<test>
  <message>This is a test XML file</message>
  <timestamp>${new Date().toISOString()}</timestamp>
</test>`;

    const blob = new Blob([testXml], { type: 'application/xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'test.xml';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success('Test XML file downloaded!');
  };

  // Removed diagram editing functions



  const downloadDiagram = async (diagram, format) => {
    try {
      console.log(`🎨 Downloading diagram as ${format}:`, diagram.sectionTitle);
      console.log(`📋 Mermaid code length: ${diagram.mermaidCode?.length || 0} characters`);
      console.log(`📋 Mermaid code preview: ${diagram.mermaidCode?.substring(0, 100)}...`);

      if (!diagram.mermaidCode) {
        toast.error('No Mermaid code available for this diagram');
        return;
      }

      const requestBody = {
        mermaid_code: diagram.mermaidCode,
        format: format,
        theme: diagram.theme || 'default',
        width: 800,
        height: 600
      };

      console.log(`📤 Request body:`, requestBody);

      const response = await fetch('http://localhost:8000/api/diagram/export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      console.log(`📡 Response status: ${response.status}`);
      console.log(`📡 Response headers:`, Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`❌ HTTP error: ${response.status}`, errorText);
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      console.log(`📋 Response result keys:`, Object.keys(result));
      console.log(`📋 Response success:`, result.success);
      console.log(`📋 Response filename:`, result.filename);
      console.log(`📋 Response content_type:`, result.content_type);
      console.log(`📋 Response data length:`, result.data?.length || 0);

      if (result.success) {
        console.log(`💾 Creating download for ${format} format...`);
        console.log(`📊 Data length: ${result.data?.length || 0} characters`);
        console.log(`📄 Content type: ${result.content_type}`);

        // Create download
        let blob;
        if (format === 'png') {
          const binaryString = atob(result.data);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          blob = new Blob([bytes], { type: result.content_type });
        } else {
          // For text-based formats (SVG, XML, Mermaid)
          blob = new Blob([result.data], { type: result.content_type });
        }

        console.log(`🎯 Created blob:`, blob);

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        // Set appropriate file extension
        let fileExtension = format;
        if (format === 'mermaid') {
          fileExtension = 'mmd';
        }

        const filename = `${diagram.sectionTitle.replace(/[^a-zA-Z0-9]/g, '_')}_diagram.${fileExtension}`;
        a.download = filename;

        console.log(`📁 Download filename: ${filename}`);
        console.log(`🔗 Download URL: ${url}`);

        // Trigger download with additional attributes
        a.style.display = 'none';
        a.target = '_blank';
        document.body.appendChild(a);

        // Force download for XML and text files
        if (format === 'xml' || format === 'mermaid') {
          a.setAttribute('download', filename);
        }

        console.log(`🖱️ Clicking download link...`);
        a.click();

        // Clean up after a short delay
        setTimeout(() => {
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          console.log(`🧹 Cleaned up download resources`);
        }, 100);

        console.log(`✅ Download triggered successfully!`);

        // Show success message
        let formatName = format.toUpperCase();
        if (format === 'drawio') {
          formatName = 'Draw.io XML';
        }

        toast.success(`Diagram downloaded as ${formatName}`);
      } else {
        console.error(`❌ Export failed:`, result);
        toast.error('Export failed: ' + (result.message || 'Unknown error'));
      }
    } catch (error) {
      console.error('Download error:', error);
      toast.error('Failed to download diagram');
    }
  };

  const regenerateDocument = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/document/${documentId}/regenerate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'updated-srs.docx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        toast.success('Document regenerated with updated diagrams!');
      }
    } catch (error) {
      console.error('Regeneration error:', error);
      toast.error('Failed to regenerate document');
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-800">
          Generated Diagrams ({diagrams.length})
        </h3>
        <div className="flex gap-2">
          <button
            onClick={testDownload}
            className="px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm"
            title="Test XML download functionality"
          >
            🧪 Test XML
          </button>
          {diagrams.length > 0 && (
            <button
              onClick={regenerateDocument}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
            >
              Regenerate Document
            </button>
          )}
        </div>
      </div>

      {diagrams.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No diagrams were generated in this document.</p>
          <p className="text-sm mt-2">Add custom sections with diagram requests to see diagrams here.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {diagrams.map((diagram, index) => (
            <div key={diagram.id || index} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h4 className="font-medium text-gray-900">{diagram.sectionTitle}</h4>
                  <p className="text-sm text-gray-500">
                    {diagram.diagramType} • Last modified: {new Date(diagram.lastModified).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {/* Download Dropdown */}
                  <div className="relative group">
                    <button className="p-2 text-green-600 hover:text-green-800 hover:bg-green-50 rounded-full">
                      <ArrowDownTrayIcon className="w-4 h-4" />
                    </button>
                    <div className="absolute right-0 mt-2 w-32 bg-white border border-gray-200 rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
                      <button
                        onClick={() => downloadDiagram(diagram, 'png')}
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                      >
                        PNG Image
                      </button>
                      <button
                        onClick={() => downloadDiagram(diagram, 'svg')}
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                      >
                        SVG Vector
                      </button>
                      <button
                        onClick={() => downloadDiagram(diagram, 'xml')}
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                      >
                        📄 XML Format
                      </button>
                      <button
                        onClick={() => downloadDiagram(diagram, 'mermaid')}
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 border-t"
                      >
                        📝 Mermaid Code
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Diagram Preview */}
              <div className="bg-gray-50 rounded-md p-3 text-sm">
                <div className="text-gray-600 mb-2">Mermaid Code Preview:</div>
                <pre className="text-xs text-gray-800 overflow-x-auto">
                  {diagram.mermaidCode?.substring(0, 200)}
                  {diagram.mermaidCode?.length > 200 && '...'}
                </pre>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DiagramManager;
