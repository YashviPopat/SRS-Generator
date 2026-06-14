<<<<<<< HEAD
# SRS Dynamic Generator

A comprehensive Software Requirements Specification (SRS) document generator with AI-powered content generation, interactive diagram editing, and multiple export formats.

## 🚀 Features

- **AI-Powered Content Generation**: Uses Google Gemini AI to generate comprehensive SRS content
- **Interactive Diagram Generation**: Automatically creates Mermaid diagrams for system architecture, sequence flows, and database schemas
- **Custom Section Prompts**: Add custom instructions for each SRS section with + buttons
- **Multiple Export Formats**: Export diagrams as PNG, SVG, XML, or Mermaid code
- **Document Upload Support**: Upload meeting summaries and documents for context
- **Real-time Diagram Editing**: Edit and update diagrams with immediate preview
- **Professional Document Output**: Generate high-quality DOCX documents with embedded diagrams

## 📁 Project Structure

```
SRS_Dynamic_final/
├── Backend/                    # Python FastAPI backend
│   ├── logic/                  # Content generation and diagram utilities
│   │   └── srs_generator.py    # Core SRS + diagram generation logic
│   ├── main.py                 # FastAPI app with REST endpoints
│   ├── requirements.txt        # Python dependencies
│   ├── generated_docs/         # Generated DOCX files (when running backend)
│   └── temp_diagrams/          # Temporary diagram images
├── Frontend/                   # React (CRA) frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── SRSHeadingsEditor.jsx
│   │   │   └── Editor.jsx      # Diagram/content editor
│   │   └── App.jsx             # Main React application
│   ├── package.json            # Node.js dependencies (proxy -> backend)
│   └── public/                 # Static assets
├── docs/                       # Sample PDFs for testing
├── start_app.py                # Helper to install deps and run both servers
├── install_dependencies.sh     # Unix setup helper (optional)
└── README.md                   # This file
```

## 🛠️ Setup Instructions

### Prerequisites

1. **Node.js** (v16 or higher)
2. **Python** (v3.8 or higher)
3. **Mermaid CLI** for diagram generation (⚠️ **REQUIRED** for PNG/SVG export)
4. **Google Gemini API Key**

### Quick Setup (Recommended)

For all platforms (recommended):
```bash
# One command to install deps and start both servers
python start_app.py
```
This script installs Python and Node dependencies, checks your environment, and starts the backend and frontend.

Prefer manual setup? See the Backend Setup and Frontend Setup sections below.

For Linux/Mac users, you can also run the helper script to install dependencies:
```bash
chmod +x install_dependencies.sh
./install_dependencies.sh
```

### 1. Install Mermaid CLI

```bash
npm install -g @mermaid-js/mermaid-cli
```

Verify installation:
```bash
mmdc --version
```

### 2. Backend Setup

1. **Navigate to Backend directory:**
```bash
cd Backend
```

2. **Create virtual environment (recommended):**
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure API Keys:**
Create a `.env` file in the Backend directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

5. **Start the backend server:**
```bash
# Option A (recommended): start via script
python main.py

# Option B: run uvicorn directly
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The backend will be available at `http://localhost:8000`

### 3. Frontend Setup

1. **Navigate to Frontend directory:**
```bash
cd Frontend
```

2. **Install Node.js dependencies:**
```bash
npm install
```

3. **Start the development server:**
```bash
npm start
```

The frontend will be available at `http://localhost:3000`

## 🎯 Usage Guide

### Basic Workflow

1. **Upload Documents** (Optional)
   - Upload meeting summaries or requirement documents for context
   - Supports PDF and text files

2. **Select SRS Sections**
   - Choose from predefined SRS sections
   - Generate AI-suggested sections using the "🤖 Generate Smart AI Headings" button

3. **Add Custom Prompts**
   - Click the **+** button next to any section heading
   - Add specific instructions for that section (e.g., "Include 10 functional requirements")

4. **Generate SRS Document**
   - Click "Generate SRS Document"
   - AI will generate content for all selected sections
   - Diagrams are automatically created for relevant sections

5. **Edit Diagrams** (Optional)
   - View generated diagrams in the "Generated Diagrams" section
   - Edit Mermaid code directly or export to different formats
   - Regenerate document with updated diagrams

### Diagram Generation

The system automatically generates diagrams for sections with these titles:
- **Sequence Diagram**: Creates sequence diagrams showing system interactions
- **System Architecture**: Creates flowchart diagrams of system components
- **Database Schema**: Creates ER diagrams or flowcharts of database structure

## 🔧 Technical Details

### AI Integration

- **Primary AI**: Google Gemini 2.0 Flash for content and diagram generation
- **Fallback System**: Multiple retry mechanisms for diagram syntax errors
- **Context Awareness**: Uses full document context for coherent content generation

### Diagram Processing

- **Mermaid Code Generation**: AI generates Mermaid syntax
- **Syntax Correction**: Automatic fixes for common AI-generated syntax errors
- **Multiple Formats**: PNG (high-quality), SVG (scalable), XML (editable), Mermaid (code)
- **Error Recovery**: Gemini self-correction system for syntax errors

### Document Generation

- **Format**: Microsoft Word DOCX with professional styling
- **Embedded Diagrams**: High-quality PNG images embedded directly
- **Table of Contents**: Automatically generated with proper formatting
- **Custom Styles**: Professional SRS document styling

## 📋 Dependencies

### Backend Dependencies (requirements.txt)
```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.6.0
python-multipart==0.0.6
python-docx==1.1.0
PyPDF2==3.0.1
docx2txt==0.8
google-generativeai>=0.8.3
python-dotenv==1.0.0
requests>=2.31.0
pytest>=7.4.3
pytest-asyncio>=0.21.1
httpx>=0.25.2
```

### Frontend Dependencies (see Frontend/package.json)
```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "react-router-dom": "^6.8.0",
  "axios": "^1.6.0",
  "@heroicons/react": "^2.2.0",
  "lucide-react": "^0.294.0",
  "clsx": "^2.0.0",
  "react-beautiful-dnd": "^13.1.1",
  "react-dropzone": "^14.2.3",
  "react-hot-toast": "^2.4.1",
  "tailwind-merge": "^2.0.0"
}
```

### System Dependencies
- **Mermaid CLI**: `@mermaid-js/mermaid-cli` (installed globally)
- **Puppeteer**: Automatically installed with Mermaid CLI

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the Backend directory:

```env
# Required: Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here
```
The backend automatically loads environment variables from a .env file in the Backend directory.

### API Key Setup

1. **Get Google Gemini API Key:**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Copy the key to your `.env` file

2. **Verify API Access:**
   - The system will validate the API key on startup
   - Check backend logs for "✅ Gemini API configured successfully"

## 🚨 Troubleshooting

### Common Issues

1. **Diagram Generation Fails (Most Common)**
   ```
   Error: mmdc command not found
   Warning: First attempt failed: mmdc command not found
   ```
   **Solution**:
   - Install Mermaid CLI globally: `npm install -g @mermaid-js/mermaid-cli`
   - Verify installation: `mmdc --version` (or use `npx mmdc --version`)
   - Restart your terminal so PATH updates take effect
   - On Linux/Mac you can also run: `./install_dependencies.sh`

2. **Mermaid CLI Not Found**
   ```
   Error: mmdc command not found
   ```
   **Solution**: Install Mermaid CLI globally: `npm install -g @mermaid-js/mermaid-cli`

2. **Diagram Generation Fails**
   ```
   Error: Parse error on line X
   ```
   **Solution**: The system includes automatic syntax correction and Gemini self-correction

3. **API Key Issues**
   ```
   Error: Failed to configure Gemini API
   ```
   **Solution**: Verify your GEMINI_API_KEY in the `.env` file

4. **Port Already in Use**
   ```
   Error: Port 8000 is already in use
   ```
   **Solution**: Kill existing processes or change port in uvicorn command

### Debug Mode

Enable detailed logging by setting `DEBUG=True` in your `.env` file. This will show:
- AI prompt details
- Diagram generation steps
- Syntax correction attempts
- File processing information

## 🎨 Diagram Features

### Supported Diagram Types

1. **Sequence Diagrams**
   - Automatic participant detection
   - Message flow visualization
   - Activation boxes and lifelines

2. **System Architecture**
   - Component relationships
   - Data flow visualization
   - Subgraph organization

3. **Database Schema**
   - Entity relationships
   - Table structures
   - Foreign key connections

### Export Formats

- **PNG**: High-quality images for documents (300 DPI)
- **SVG**: Scalable vector graphics for web use
- **XML**: Draw.io compatible format for visual editing
- **Mermaid**: Raw code for manual editing

## 🔄 Recent Improvements

### Mermaid Syntax Fixes
- Enhanced AI prompts with strict syntax rules
- Bulletproof post-processing for syntax errors
- Gemini self-correction system for failed diagrams
- Support for complex subgraph structures

### UI Enhancements
- Added + buttons to AI-generated headings for custom prompts
- Improved diagram editor with multiple export options
- Real-time diagram preview and editing
- Better error handling and user feedback

### Performance Optimizations
- Two-pass content generation for better context
- Efficient diagram storage and retrieval
- Optimized PNG generation with fallback strategies
- Reduced API calls through content caching

## 🧪 Testing

### Manual Testing

1. **Test Diagram Generation APIs:**
```bash
# Validate a simple flowchart
curl -X POST http://localhost:8000/api/diagram/validate \
  -H "Content-Type: application/json" \
  -d '{
    "mermaid_code": "flowchart TD; A[Start] --> B[End]",
    "diagram_type": "flowchart"
  }'

# Export a simple PNG
curl -X POST http://localhost:8000/api/diagram/export \
  -H "Content-Type: application/json" \
  -d '{
    "mermaid_code": "flowchart TD; A[Start] --> B[End]",
    "format": "png"
  }'
```

2. **Test API Endpoints:**
```bash
# Test document generation
curl -X POST http://localhost:8000/generate-srs \
  -H "Content-Type: application/json" \
  -d '{"selectedHeadings": [], "customSections": []}'

# Test diagram export
curl -X POST http://localhost:8000/api/diagram/export \
  -H "Content-Type: application/json" \
  -d '{"mermaid_code": "flowchart TD\n    A[Start] --> B[End]", "format": "png"}'
```

### Automated Testing

The system includes built-in error recovery and validation:
- Automatic syntax correction for AI-generated diagrams
- Fallback strategies for failed diagram generation
- Input validation for all API endpoints
- Comprehensive error logging

## 📚 API Documentation

### Key Endpoints

- `POST /generate-srs`: Generate complete SRS document
- `POST /upload-documents`: Upload context documents
- `GET /api/document/{id}/diagrams`: Retrieve document diagrams
- `POST /api/diagram/export`: Export diagrams in various formats
- `PUT /api/diagram/{id}/update`: Update existing diagrams

### Interactive API Docs

When the backend is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🤝 Contributing

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Make changes and test thoroughly**
4. **Commit with descriptive messages**
5. **Submit a pull request**

### Code Style

- **Backend**: Follow PEP 8 Python style guidelines
- **Frontend**: Use ESLint and Prettier for consistent formatting
- **Comments**: Document complex logic and AI integration points

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Getting Help

1. **Run the connection diagnostic**: `python diagnose_connection.py`
2. **Check the troubleshooting section** above
3. **Review backend logs** for detailed error information
4. **Test with minimal examples** to isolate issues
5. **Verify all dependencies** are properly installed

### Known Limitations

- **Diagram Complexity**: Very complex diagrams may require manual editing
- **API Rate Limits**: Gemini API has usage quotas
- **File Size**: Large documents may take longer to process
- **Browser Compatibility**: Tested on Chrome, Firefox, and Edge

## 🔮 Future Enhancements

- **Database Integration**: Replace in-memory storage with persistent database
- **User Authentication**: Add user accounts and document management
- **Template System**: Predefined SRS templates for different industries
- **Collaborative Editing**: Real-time collaboration on SRS documents
- **Advanced Diagrams**: Support for more diagram types (Gantt, mindmaps, etc.)
- **Export Options**: PDF export with embedded diagrams
- **Version Control**: Track document changes and revisions

---

**Built with ❤️ using React, FastAPI, and Google Gemini AI**
=======
# SRS-Generator
>>>>>>> c85e9c03c0b929a3d10dd28695b9dee9d86d0929
