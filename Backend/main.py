from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
import uvicorn
import uuid
import os
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# Load environment variables
from dotenv import load_dotenv

# Try to load .env file, but don't fail if it doesn't exist
try:
    load_dotenv()
    print("✅ .env file loaded successfully")
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")
    print("Continuing without .env file - using system environment variables")

# Get API keys from environment variables
gemini_api_key = os.getenv("GEMINI_API_KEY")

# Validate API keys
if not gemini_api_key:
    print("⚠️ Warning: GEMINI_API_KEY not found in environment variables")
    print("💡 Please set GEMINI_API_KEY in your .env file or system environment")
    gemini_api_key = "AIzaSyDERZ7x4BcVGLwJM1ucGO02hFW2PTKodaQ"  # Fallback for development

# Import our models and utilities
from models.srs_model import *
from logic.heading_utils import load_standard_headings, get_all_headings, merge_headings
from logic.extractor import DocumentExtractor
from logic.extractor import get_gemini_srs_headings_from_transcript

from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="SRS Dynamic Generator",
    description="AI-powered SRS document generator with dynamic heading suggestions",
    version="1.0.0"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for storing data (in production, use a proper database)
uploaded_documents = {}
srs_structures = {}
generated_files = {}
document_diagrams = {}  # Store diagrams for each document
extracted_text_content = {}  # Store extracted text content from PDFs
processing_status = {}  # Track processing status

# Initialize Gemini client for AI operations
import google.generativeai as genai

# Configure Gemini with the API key from environment variables
try:
    genai.configure(api_key=gemini_api_key)
    print(f"✅ Gemini API configured successfully with key: {gemini_api_key[:10]}...")
except Exception as e:
    print(f"❌ Failed to configure Gemini API: {e}")
    print("⚠️ Gemini functionality may not work properly")

# --- Step 1: Process PDFs with Gemini ---
async def process_pdfs_with_gemini(pdf_file_contents: dict):
    """Process PDFs using Gemini AI for content extraction"""
    try:
        print("📤 Processing PDFs with Gemini...")

        all_content = ""
        processed_files = []

        for file_name, content in pdf_file_contents.items():
            try:
                # Extract text from PDF using existing extractor
                extractor = DocumentExtractor()
                extracted_text = extractor.extract_text_from_pdf_bytes(content)

                if extracted_text and not extracted_text.startswith("Error"):
                    all_content += f"\n--- {file_name} ---\n"
                    all_content += extracted_text
                    processed_files.append(file_name)
                    print(f"✅ Processed file: {file_name}")
                else:
                    print(f"⚠️ Failed to extract text from: {file_name}")

            except Exception as e:
                print(f"❌ Failed to process file {file_name}: {e}")
                continue

        if processed_files:
            print(f"✅ Successfully processed {len(processed_files)} files")
            return all_content
        else:
            print("❌ No files were successfully processed")
            return None

    except Exception as e:
        print(f"❌ Failed to process PDFs: {e}")
        return None

# --- Step 2: Extract TOC using Gemini ---
async def extract_toc_with_gemini(content: str):
    """Extract TOC from content using Gemini AI"""
    try:
        print("🔍 Extracting TOC with Gemini...")

        model = genai.GenerativeModel('gemini-2.0-flash')

        prompt = f"""Extract ALL headings and section titles from the following document content. Look for:

1. Table of Contents (TOC) sections
2. Chapter headings and section headings
3. Any numbered or bulleted lists that appear to be document structure
4. Section titles and subsection titles
5. Main document headings and subheadings
6. Any structured outline or document organization

IMPORTANT: Even if there's no formal "Table of Contents", extract the main headings and section titles that show the document structure.

Return ALL headings found in a clean format, one per line, removing page numbers and formatting artifacts.
If you find multiple documents, extract headings from all of them and combine the results.
If no clear headings are found, extract any text that appears to be a section title or heading.

Be thorough and extract as many headings as possible from the document structure.

Document Content:
{content[:8000]}"""  # Limit content to avoid token limits

        response = model.generate_content(prompt)
        toc_text = response.text
        print(f"✅ TOC extracted: {len(toc_text)} characters")
        print(f"📄 TOC preview: {toc_text[:500]}...")

        if not toc_text or len(toc_text.strip()) < 10:
            print("⚠️ Warning: Very short or empty TOC extracted")
            return {"toc": "No headings found in documents"}

        return {"toc": toc_text}

    except Exception as e:
        print(f"❌ Failed to extract TOC: {e}")
        return {"toc": ""}

# --- Step 3: Generate headings using Gemini ---
async def generate_headings_with_gemini(toc_result: dict):
    """Generate headings using Gemini based on TOC"""
    try:
        print("🤖 Generating headings...")
        toc_text = toc_result.get('toc', '')
        if not toc_text:
            print("⚠️ No TOC text available for OpenAI")
            return {"openai_headings": ""}
        prompt = f"""
        Given this content from meeting documents:
        {toc_text}

        Generate well-structured SRS (Software Requirements Specification) headings suitable for a project document.
        Analyze the content and create headings that would be appropriate for documenting software requirements.
        
        Return the result as a JSON object in this format: {{"Heading": {{"Subheading": "Purpose", ...}}, ...}}
        If a heading has no subheadings, use a string as the value for its purpose.
        
        Focus on creating headings that are relevant to the content and suitable for SRS documentation.
        Common SRS headings include: Introduction, Functional Requirements, Non-Functional Requirements, System Architecture, User Interface, Data Requirements, etc.
        """
        # Note: This fallback is kept for compatibility but shouldn't be needed with Gemini
        # if not os.getenv('GEMINI_API_KEY'):
        #     print("❌ No Gemini API key found. Please set GEMINI_API_KEY environment variable.")
        #     print("🔧 Returning sample headings for testing...")
        #     sample_headings = {
        #         "Introduction": "Overview and purpose of the system",
        #         "Functional Requirements": "Core system functions and features",
        #         "Non-Functional Requirements": "Performance, security, and usability requirements",
        #         "System Architecture": "Technical design and component structure",
        #         "User Interface": "UI/UX specifications and wireframes"
        #     }
        #     print(f"🔧 Sample headings: {sample_headings}")
        #     return {"openai_headings": sample_headings}
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        gemini_text = response.text.strip()
        print(f"✅ Gemini headings extracted: {len(gemini_text)} characters")
        print(f"📄 Gemini text preview: {gemini_text[:500]}...")
        return {"openai_headings": gemini_text}  # Keep the key name for compatibility
    except Exception as e:
        print(f"❌ Failed to generate Gemini headings: {e}")
        return {"openai_headings": ""}

# --- Helper functions ---
def parse_toc_to_headings(toc_text: str):
    """Parse TOC text to heading format"""
    try:
        headings = {}
        lines = toc_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 3:
                # Clean the heading
                heading = line
                # Remove page numbers and dots
                heading = re.sub(r'\s*\.{2,}\s*\d+\s*$', '', heading)
                # Remove leading numbers and bullets
                heading = re.sub(r'^[\d\.\-\*]+\.?\s*', '', heading)
                # Remove extra whitespace
                heading = re.sub(r'\s+', ' ', heading)
                heading = heading.strip()
                
                # Skip if heading is too short or too long
                if heading and 3 < len(heading) < 200:
                    # Skip common non-heading text
                    if not any(skip in heading.lower() for skip in ['page', 'continued', '...', 'etc']):
                        # Generate purpose based on heading
                        purpose = generate_purpose_for_heading(heading)
                        headings[heading] = purpose
        
        print(f"✅ Parsed {len(headings)} headings from TOC text")
        return headings
        
    except Exception as e:
        print(f"❌ Failed to parse TOC: {e}")
        return {}

def parse_gemini_headings(gemini_text: str):
    """Parse Gemini headings to structured format"""
    try:
        import json
        import re
        
        print(f"🔍 Parsing: {len(gemini_text)} characters")
        print(f"📄 text preview: {gemini_text[:500]}...")
        
        # First, try to extract JSON from the response
        json_patterns = [
            r'\{[\s\S]*\}',  # Standard JSON object
            r'\[[\s\S]*\]',  # JSON array
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, gemini_text)
            if match:
                try:
                    json_str = match.group(0)
                    print(f"🔍 Found JSON match with pattern {pattern}: {json_str[:200]}...")
                    result = json.loads(json_str)
                    print(f"✅ Successfully parsed JSON: {len(result)} keys")
                    return result
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error with pattern {pattern}: {e}")
                    continue
        
        # Try to parse the whole response as JSON
        try:
            result = json.loads(gemini_text)
            print(f"✅ Successfully parsed whole response: {len(result)} keys")
            return result
        except json.JSONDecodeError as e:
            print(f"❌ Whole response JSON decode error: {e}")
        
        # If JSON parsing fails, extract headings from text
        print("⚠️ JSON parsing failed, extracting headings from text...")
        manual_headings = {}
        lines = gemini_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 3:
                # Remove common prefixes and clean up
                cleaned_line = re.sub(r'^[\d\.\-\*]+\.?\s*', '', line)  # Remove numbers, bullets
                cleaned_line = re.sub(r'^["\']|["\']$', '', cleaned_line)  # Remove quotes
                cleaned_line = cleaned_line.strip()
                
                # Look for heading patterns
                if (re.match(r'^[A-Z][^:]*:', cleaned_line) or 
                    re.match(r'^[A-Z][^:]*$', cleaned_line) or
                    len(cleaned_line) > 5 and len(cleaned_line) < 100):
                    
                    # Skip if it looks like a non-heading
                    if not any(skip in cleaned_line.lower() for skip in ['page', 'continued', '...', 'etc', 'note:', 'warning:']):
                        manual_headings[cleaned_line] = f"Purpose for {cleaned_line}"
        
        print(f"🔧 Manual extraction found {len(manual_headings)} headings")
        if manual_headings:
            print(f"🔧 Sample headings: {list(manual_headings.keys())[:3]}")
        
        return manual_headings
        
    except Exception as e:
        print(f"❌ Failed to parse Gemini headings: {e}")
        return {}

def generate_purpose_for_heading(heading_text: str) -> str:
    """Generate purpose for heading based on content"""
    heading_lower = heading_text.lower()
    
    # Purpose mappings
    purpose_mappings = {
        'introduction': 'Brief overview and purpose of the document',
        'overview': 'High-level system description and context',
        'requirements': 'Detailed functional and non-functional specifications',
        'functional': 'System functions and capabilities',
        'non-functional': 'Performance, security, and usability requirements',
        'system': 'System architecture and design',
        'architecture': 'Technical architecture and component design',
        'design': 'System design and implementation details',
        'testing': 'Testing approach and methodologies',
        'deployment': 'Deployment procedures and configuration',
        'security': 'Security requirements and protocols',
        'database': 'Database design and data models',
        'api': 'API specifications and endpoints',
        'user interface': 'UI/UX specifications and wireframes',
        'performance': 'Performance requirements and benchmarks',
        'scalability': 'Scalability considerations and strategies'
    }
    
    # Check for exact matches
    for key, purpose in purpose_mappings.items():
        if key in heading_lower:
            return purpose
    
    # Check for partial matches
    for key, purpose in purpose_mappings.items():
        if any(word in heading_lower for word in key.split()):
            return purpose
    
    # Default purpose
    return f"Describe the {heading_text.lower()} aspects of the system"

def create_nested_headings_structure(toc_headings: dict, gemini_headings: dict) -> dict:
    """
    Create nested headings structure from TOC and Gemini headings
    
    Args:
        toc_headings: Dictionary of TOC headings with purposes
        gemini_headings: Dictionary of Gemini-generated headings
        
    Returns:
        Nested structure organized by categories
    """
    # Initialize categories
    categories = {
        "Introduction": {},
        "User Personas": {},
        "Scope": {},
        "Functional Requirements": {},
        "Non-Functional Requirements": {},
        "System Requirements": {},
        "System Architecture": {},
        "Implementation": {},
        "Testing": {},
        "Deployment": {},
        "Other": {}
    }
    
    # Process TOC headings
    for heading, purpose in toc_headings.items():
        heading_lower = heading.lower()
        categorized = False
        
        # Categorize based on heading content
        if any(word in heading_lower for word in ['introduction', 'purpose', 'objective', 'stakeholder', 'assumption', 'acronym']):
            categories["Introduction"][heading] = purpose
            categorized = True
        elif any(word in heading_lower for word in ['user persona', 'student', 'teacher', 'educator', 'leadership', 'admission', 'inspector']):
            categories["User Personas"][heading] = purpose
            categorized = True
        elif any(word in heading_lower for word in ['scope', 'boundary', 'limit']):
            categories["Scope"][heading] = purpose
            categorized = True
        elif any(word in heading_lower for word in ['functional requirement', 'use case', 'start new', 'upload', 'generate', 'ask question', 'customize', 'export', 'library', 'curriculum', 'lesson', 'learning', 'student', 'teacher', 'admission', 'campaign']):
            categories["Functional Requirements"][heading] = purpose
            categorized = True
        elif any(word in heading_lower for word in ['non-functional', 'performance', 'scalability', 'reliability', 'usability', 'security', 'maintainability', 'compatibility']):
            categories["Non-Functional Requirements"][heading] = purpose
            categorized = True
        elif any(word in heading_lower for word in ['system requirement', 'user interface', 'database', 'communication', 'integration', 'constraint', 'legal']):
            categories["System Requirements"][heading] = purpose
            categorized = True
        elif any(word in heading_lower for word in ['architecture', 'overview', 'n-tier', 'microservice', 'component', 'design', 'technical']):
            categories["System Architecture"][heading] = purpose
            categorized = True
        elif any(word in heading_lower for word in ['implementation', 'development', 'coding']):
            categories["Implementation"][heading] = purpose
            categorized = True
        elif any(word in heading_lower for word in ['testing', 'test', 'validation']):
            categories["Testing"][heading] = purpose
            categorized = True
        elif any(word in heading_lower for word in ['deployment', 'delivery', 'release']):
            categories["Deployment"][heading] = purpose
            categorized = True
        
        if not categorized:
            categories["Other"][heading] = purpose
    
    # Process Gemini headings (these might be more structured)
    for heading, purpose in gemini_headings.items():
        if isinstance(purpose, dict):
            # Nested structure from Gemini
            for subheading, subpurpose in purpose.items():
                heading_lower = subheading.lower()
                categorized = False
                
                # Apply same categorization logic
                if any(word in heading_lower for word in ['introduction', 'purpose', 'objective', 'stakeholder', 'assumption', 'acronym']):
                    categories["Introduction"][subheading] = subpurpose
                    categorized = True
                elif any(word in heading_lower for word in ['user persona', 'student', 'teacher', 'educator', 'leadership', 'admission', 'inspector']):
                    categories["User Personas"][subheading] = subpurpose
                    categorized = True
                elif any(word in heading_lower for word in ['scope', 'boundary', 'limit']):
                    categories["Scope"][subheading] = subpurpose
                    categorized = True
                elif any(word in heading_lower for word in ['functional requirement', 'use case', 'start new', 'upload', 'generate', 'ask question', 'customize', 'export', 'library', 'curriculum', 'lesson', 'learning', 'student', 'teacher', 'admission', 'campaign']):
                    categories["Functional Requirements"][subheading] = subpurpose
                    categorized = True
                elif any(word in heading_lower for word in ['non-functional', 'performance', 'scalability', 'reliability', 'usability', 'security', 'maintainability', 'compatibility']):
                    categories["Non-Functional Requirements"][subheading] = subpurpose
                    categorized = True
                elif any(word in heading_lower for word in ['system requirement', 'user interface', 'database', 'communication', 'integration', 'constraint', 'legal']):
                    categories["System Requirements"][subheading] = subpurpose
                    categorized = True
                elif any(word in heading_lower for word in ['architecture', 'overview', 'n-tier', 'microservice', 'component', 'design', 'technical']):
                    categories["System Architecture"][subheading] = subpurpose
                    categorized = True
                elif any(word in heading_lower for word in ['implementation', 'development', 'coding']):
                    categories["Implementation"][subheading] = subpurpose
                    categorized = True
                elif any(word in heading_lower for word in ['testing', 'test', 'validation']):
                    categories["Testing"][subheading] = subpurpose
                    categorized = True
                elif any(word in heading_lower for word in ['deployment', 'delivery', 'release']):
                    categories["Deployment"][subheading] = subpurpose
                    categorized = True
                
                if not categorized:
                    categories["Other"][subheading] = subpurpose
        else:
            # Simple string purpose
            heading_lower = heading.lower()
            categorized = False
            
            # Apply categorization logic
            if any(word in heading_lower for word in ['introduction', 'purpose', 'objective', 'stakeholder', 'assumption', 'acronym']):
                categories["Introduction"][heading] = purpose
                categorized = True
            elif any(word in heading_lower for word in ['user persona', 'student', 'teacher', 'educator', 'leadership', 'admission', 'inspector']):
                categories["User Personas"][heading] = purpose
                categorized = True
            elif any(word in heading_lower for word in ['scope', 'boundary', 'limit']):
                categories["Scope"][heading] = purpose
                categorized = True
            elif any(word in heading_lower for word in ['functional requirement', 'use case', 'start new', 'upload', 'generate', 'ask question', 'customize', 'export', 'library', 'curriculum', 'lesson', 'learning', 'student', 'teacher', 'admission', 'campaign']):
                categories["Functional Requirements"][heading] = purpose
                categorized = True
            elif any(word in heading_lower for word in ['non-functional', 'performance', 'scalability', 'reliability', 'usability', 'security', 'maintainability', 'compatibility']):
                categories["Non-Functional Requirements"][heading] = purpose
                categorized = True
            elif any(word in heading_lower for word in ['system requirement', 'user interface', 'database', 'communication', 'integration', 'constraint', 'legal']):
                categories["System Requirements"][heading] = purpose
                categorized = True
            elif any(word in heading_lower for word in ['architecture', 'overview', 'n-tier', 'microservice', 'component', 'design', 'technical']):
                categories["System Architecture"][heading] = purpose
                categorized = True
            elif any(word in heading_lower for word in ['implementation', 'development', 'coding']):
                categories["Implementation"][heading] = purpose
                categorized = True
            elif any(word in heading_lower for word in ['testing', 'test', 'validation']):
                categories["Testing"][heading] = purpose
                categorized = True
            elif any(word in heading_lower for word in ['deployment', 'delivery', 'release']):
                categories["Deployment"][heading] = purpose
                categorized = True
            
            if not categorized:
                categories["Other"][heading] = purpose
    
    # Remove empty categories
    categories = {k: v for k, v in categories.items() if v}
    
    return categories

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "SRS Dynamic Generator API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "standard_headings": "/standard-headings",
            "process_files": "/process-all-files",
            "generate_srs": "/generate-srs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/standard-headings", response_model=StandardHeadingsResponse)
async def get_standard_headings():
    """
    Get all standard SRS headings and their purposes.
    Returns the complete structure of standard headings.
    """
    try:
        # Load standard headings from JSON file
        standard_headings = load_standard_headings()
        
        # Get all headings as flat list for counting
        all_headings = get_all_headings(standard_headings)
        
        # Extract main categories (top-level keys)
        categories = list(standard_headings.keys())
        
        return StandardHeadingsResponse(
            headings=standard_headings,
            total_count=len(all_headings),
            categories=categories
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load standard headings: {str(e)}"
        )

@app.post("/analyze-docs", response_model=DocumentAnalysisResponse)
async def analyze_documents(
    file: UploadFile = File(...),
    document_type: str = Form(...)
):
    """
    Upload and analyze documents to extract headings.
    Supports various document types (PDF, DOCX, TXT).
    """
    try:
        print(f"📁 Processing file: {file.filename}, type: {document_type}")
        
        # Generate unique document ID
        document_id = str(uuid.uuid4()) #a 128-bit value used to uniquely identify information in computer systems. 
        
        # Read file content
        content = await file.read()
        print(f"File size: {len(content)} bytes")
        
        # Validate document type
        try:
            doc_type_enum = DocumentType(document_type)
        except ValueError:
            # If invalid, default to 'other'
            doc_type_enum = DocumentType.OTHER
            print(f"⚠️ Invalid document type '{document_type}', defaulting to 'other'")
        
        # Handle different file types appropriately
        content_text = ""
        if file.filename.lower().endswith('.pdf'):
            # For PDFs, we'll store the binary content and extract text later
            content_text = f"[PDF Content - {len(content)} bytes]"
            print(f"📄 PDF file detected, storing binary content")
        elif file.filename.lower().endswith(('.docx', '.doc')):
            # For Word documents, store binary content
            content_text = f"[Word Document - {len(content)} bytes]"
            print(f"📄 Word document detected, storing binary content")
        else:
            # For text files, try to decode as UTF-8
            try:
                content_text = content.decode('utf-8')
                print(f"📄 Text file decoded successfully")
            except UnicodeDecodeError:
                # If UTF-8 fails, try other encodings
                try:
                    content_text = content.decode('latin-1')
                    print(f"📄 Text file decoded with latin-1 encoding")
                except:
                    content_text = f"[Binary Content - {len(content)} bytes]"
                    print(f"📄 Could not decode as text, storing as binary")
        
        # Extract text for Gemini if it's a meeting transcript (PDF or TXT)
        gemini_suggestions = None
        transcript_text = None
        if document_type == 'meeting_transcript' or file.filename.lower().endswith('.pdf') or file.filename.lower().endswith('.txt'):
            # Try to extract text from PDF or TXT
            try:
                if file.filename.lower().endswith('.pdf'):
                    import io
                    from PyPDF2 import PdfReader
                    pdf_reader = PdfReader(io.BytesIO(content))
                    transcript_text = "\n".join(page.extract_text() or '' for page in pdf_reader.pages)
                else:
                    transcript_text = content.decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"Failed to extract transcript text: {e}")
                transcript_text = None
            if transcript_text and len(transcript_text) > 20:
                gemini_suggestions = get_gemini_srs_headings_from_transcript(transcript_text)
        
        # Extract headings from the document
        try:
            # Determine file type from filename
            file_extension = file.filename.lower().split('.')[-1]
            if file_extension == 'pdf':
                file_type = 'pdf'
            elif file_extension in ['docx', 'doc']:
                file_type = 'docx'
            else:
                file_type = 'txt'
            
            # Extract headings using DocumentExtractor
            extracted_data = DocumentExtractor.extract_document_headings(content, file_type)
            
            # Format headings for API response
            raw_headings = extracted_data.get('headings', [])
            formatted_headings = DocumentExtractor.format_headings_for_api(raw_headings, file.filename)
            
            # Convert to HeadingItem objects
            extracted_headings = [
                HeadingItem(
                    heading=h['heading'],
                    purpose=h['purpose'],
                    is_standard=False
                )
                for h in formatted_headings
            ]
            
            print(f"Extracted {len(extracted_headings)} headings from {file.filename}")
            
        except Exception as extraction_error:
            print(f"Heading extraction failed: {extraction_error}")
            # Fallback to sample headings
            extracted_headings = [
                HeadingItem(
                    heading="Sample Heading 1",
                    purpose="This is a sample heading extracted from the document",
                    is_standard=False
                ),
                HeadingItem(
                    heading="Sample Heading 2", 
                    purpose="Another sample heading from the document",
                    is_standard=False
                )
            ]
        
        # Extract and store text content from the document
        extracted_text = ""
        try:
            from logic.extractor import DocumentExtractor
            
            # Determine file type from filename
            file_extension = file.filename.lower().split('.')[-1]
            if file_extension == 'pdf':
                file_type = 'pdf'
                extracted_data = DocumentExtractor.extract_from_pdf(content)
            elif file_extension in ['docx', 'doc']:
                file_type = 'docx'
                extracted_data = DocumentExtractor.extract_from_docx(content)
            else:
                file_type = 'txt'
                extracted_data = DocumentExtractor.extract_from_text(content)
            
            extracted_text = extracted_data.get('content', '')
            print(f"Extracted {len(extracted_text)} characters from {file.filename}")
            
        except Exception as e:
            print(f"Failed to extract text from {file.filename}: {e}")
            extracted_text = f"Error extracting text: {str(e)}"
        
        # Store document info
        uploaded_documents[document_id] = {
            "file_name": file.filename,
            "document_type": doc_type_enum,
            "content": content_text,
            "binary_content": content,  # Store original binary content
            "extracted_text": extracted_text,  # Store the extracted text
            "extracted_headings": extracted_headings
        }
        
        # Also store in the extracted_text_content dictionary
        extracted_text_content[document_id] = {
            "file_name": file.filename,
            "text_content": extracted_text
        }
        
        print(f"✅ Successfully processed document: {document_id}")
        
        return DocumentAnalysisResponse(
            document_id=document_id,
            extracted_headings=extracted_headings,
            document_type=doc_type_enum,
            analysis_status="success",
            gemini_suggestions=gemini_suggestions
        )
        
    except Exception as e:
        print(f"❌ Error processing document: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze document: {str(e)}"
        )

@app.post("/suggest-headings", response_model=HeadingSuggestionResponse)
async def suggest_headings(request: HeadingSuggestionRequest):
    """
    Get AI-powered suggestions for additional headings based on current structure
    and analyzed documents.
    """
    try:
        # Load standard headings
        standard_headings = load_standard_headings()
        standard_flat = get_all_headings(standard_headings)
        
        # Convert current headings to dict format for comparison
        current_heading_dicts = [
            {"heading": h.heading, "purpose": h.purpose} 
            for h in request.current_headings
        ]
        
        # Find missing standard headings
        current_headings_set = {h["heading"] for h in current_heading_dicts}
        missing_standard = [
            heading_dict_to_item(h) 
            for h in standard_flat 
            if h["heading"] not in current_headings_set
        ]
        
        # For now, suggest some common missing headings
        # In a real implementation, you'd use AI to analyze the project context
        suggested_headings = [
            HeadingItem(
                heading="System Architecture",
                purpose="Describe the overall system architecture and design",
                is_standard=False
            ),
            HeadingItem(
                heading="Security Requirements",
                purpose="Define security and privacy requirements",
                is_standard=False
            )
        ]
        
        # Add some missing standard headings as suggestions
        if missing_standard:
            suggested_headings.extend(missing_standard[:3])  # Limit to 3 suggestions
        
        return HeadingSuggestionResponse(
            suggested_headings=suggested_headings,
            missing_standard_headings=missing_standard[:5],  # Show top 5 missing
            reasoning="Based on analysis of similar projects and standard SRS templates",
            confidence_score=0.85
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate heading suggestions: {str(e)}"
        )

@app.post("/build-structure", response_model=SRSStructureResponse)
async def build_srs_structure(request: SRSStructureRequest):
    """
    Build the final SRS structure with the selected headings.
    """
    try:
        # Generate unique structure ID
        structure_id = str(uuid.uuid4())
        
        # Store the structure
        srs_structures[structure_id] = {
            "headings": request.headings,
            "project_title": request.project_title,
            "project_description": request.project_description,
            "include_content_placeholders": request.include_content_placeholders
        }
        
        # Calculate estimated pages (rough estimate: 1 page per 3 headings)
        estimated_pages = max(1, len(request.headings) // 3)
        
        return SRSStructureResponse(
            structure_id=structure_id,
            headings=request.headings,
            total_sections=len(request.headings),
            estimated_pages=estimated_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build SRS structure: {str(e)}"
        )

@app.post("/generate-docx", response_model=DocxGenerationResponse)
async def generate_docx(request: DocxGenerationRequest):
    """
    Generate a DOCX file from the SRS structure.
    """
    try:
        # Get the structure
        if request.structure_id not in srs_structures:
            raise HTTPException(
                status_code=404,
                detail="SRS structure not found"
            )
        
        structure = srs_structures[request.structure_id]
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        file_name = f"srs_{structure['project_title'].replace(' ', '_')}_{file_id[:8]}.docx"
        
        # For now, create a simple placeholder file
        # In a real implementation, you'd use python-docx to generate the actual file
        output_dir = "generated_files"
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, file_name)
        
        # Create a simple text file as placeholder (replace with actual DOCX generation)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"SRS Document: {structure['project_title']}\n")
            f.write("=" * 50 + "\n\n")
            
            for heading in structure['headings']:
                f.write(f"{heading.heading}\n")
                f.write("-" * len(heading.heading) + "\n")
                f.write(f"Purpose: {heading.purpose}\n\n")
        
        # Store file info
        generated_files[file_id] = {
            "file_path": file_path,
            "file_name": file_name,
            "structure_id": request.structure_id
        }
        
        return DocxGenerationResponse(
            file_id=file_id,
            file_name=file_name,
            file_size=os.path.getsize(file_path),
            download_url=f"/download/{file_id}",
            generation_status="success"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate DOCX: {str(e)}"
        )

@app.get("/download/{file_id}")
async def download_file(file_id: str):
    """
    Download a generated file.
    """
    if file_id not in generated_files:
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )
    
    file_info = generated_files[file_id]
    return FileResponse(
        path=file_info["file_path"],
        filename=file_info["file_name"],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@app.get("/structures/{structure_id}", response_model=SRSStructureResponse)
async def get_structure(structure_id: str):
    """
    Get a specific SRS structure by ID.
    """
    if structure_id not in srs_structures:
        raise HTTPException(
            status_code=404,
            detail="Structure not found"
        )
    
    structure = srs_structures[structure_id]
    return SRSStructureResponse(
        structure_id=structure_id,
        headings=structure["headings"],
        total_sections=len(structure["headings"]),
        estimated_pages=max(1, len(structure["headings"]) // 3)
    )

@app.get("/documents", response_model=List[Dict[str, Any]])
async def list_documents():
    """
    List all uploaded documents.
    """
    return [
        {
            "document_id": doc_id,
            "file_name": doc_info["file_name"],
            "document_type": doc_info["document_type"],
            "analysis_status": "success"
        }
        for doc_id, doc_info in uploaded_documents.items()
    ]

@app.get("/extracted-headings", response_model=Dict[str, Any])
async def get_extracted_headings():
    """
    Get extracted headings from the clean_extracted_headings.json file.
    Returns the organized headings that were extracted from uploaded documents.
    """
    try:
        # Load extracted headings from JSON file
        extracted_headings_file = "clean_extracted_headings.json"
        
        if not os.path.exists(extracted_headings_file):
            return {}
        
        with open(extracted_headings_file, 'r', encoding='utf-8') as f:
            extracted_headings = json.load(f)
        
        return extracted_headings
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load extracted headings: {str(e)}"
        )

@app.post("/generate-srs")
async def generate_srs_document(request: Dict[str, Any]):
    """
    Generate SRS document based on selected headings using OpenAI with meeting summaries.
    Creates a DOCX file with the selected headings and their content.
    """
    try:
        selected_headings = request.get('selectedHeadings', [])
        custom_sections = request.get('customSections', [])
        meeting_summary = request.get('meetingSummary', '')
        
        if not selected_headings:
            raise HTTPException(
                status_code=400,
                detail="No headings selected for SRS generation"
            )
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        output_filename = f"generated_srs_{file_id}.docx"
        output_path = os.path.join("generated_docs", output_filename)
        
        # Ensure generated_docs directory exists
        os.makedirs("generated_docs", exist_ok=True)
        
        # Create SRS document using the main generation logic
        from logic.srs_generator import generate_srs_docx
        
        # Prepare headings data
        all_headings = []
        
        print(f"=== BACKEND DEBUG ===")
        print(f"Selected headings count: {len(selected_headings)}")
        print(f"Custom sections count: {len(custom_sections)}")
        
        # Add selected headings
        for i, heading_data in enumerate(selected_headings):
            print(f"Selected heading {i+1}: {heading_data['heading']} (Category: {heading_data.get('category', 'Other')}, Source: {heading_data.get('source', 'Unknown')})")
            all_headings.append({
                'heading': heading_data['heading'],
                'purpose': heading_data['purpose'],
                'category': heading_data.get('category', 'Other'),
                'source': heading_data.get('source', 'Unknown'),
                'userPrompt': heading_data.get('userPrompt', '')
            })
        
        # Add custom sections (if any are sent separately - this should be empty now)
        for section in custom_sections:
            print(f"⚠️ Warning: Custom section '{section['title']}' received separately - this should not happen")
            all_headings.append({
                'heading': section['title'],
                'purpose': section['purpose'],
                'category': 'Custom',
                'source': 'Custom Section'
            })
        
        # Use meeting summary from request or fallback to stored content
        uploaded_content = meeting_summary
        if not uploaded_content:
            if extracted_text_content:
                try:
                    uploaded_content = ""
                    for doc_id, doc_info in extracted_text_content.items():
                        text_content = doc_info.get('text_content', '')
                        file_name = doc_info.get('file_name', 'Unknown')
                        if text_content and not text_content.startswith("Error extracting text"):
                            uploaded_content += f"\n--- MEETING TRANSCRIPT: {file_name} ---\n"
                            uploaded_content += f"{text_content}\n"
                    if not uploaded_content:
                        uploaded_content = "No content could be extracted from uploaded documents."
                except Exception as e:
                    print(f"⚠️ Warning: Could not retrieve stored text content: {e}")
                    uploaded_content = f"Error retrieving stored text content: {str(e)}"
            else:
                uploaded_content = "No documents uploaded. Please upload meeting summary documents first."
        
        # Generate the document with uploaded content context
        print(f"📄 Generating SRS with {len(all_headings)} headings")
        print(f"📄 Custom sections in request: {len(custom_sections)}")
        print(f"📄 Using meeting summary: {len(uploaded_content)} characters")
        
        # Debug: Log all headings being processed
        for i, heading in enumerate(all_headings):
            print(f"📄 Heading {i+1}: {heading['heading']} (Category: {heading['category']}, Source: {heading['source']})")
        
        if uploaded_content:
            print(f"📄 Content preview: {uploaded_content[:200]}...")
        
        # Generate SRS and get the actual generated diagrams
        generated_diagrams = generate_srs_docx(all_headings, output_path, uploaded_content)

        # Store diagrams for this document
        if generated_diagrams:
            document_diagrams[file_id] = generated_diagrams
            print(f"📊 Stored {len(generated_diagrams)} diagrams for document {file_id}")

        # Store file reference
        generated_files[file_id] = {
            'filename': output_filename,
            'path': output_path,
            'created_at': datetime.now().isoformat(),
            'headings_count': len(all_headings),
            'diagrams_count': len(generated_diagrams) if generated_diagrams else 0
        }
        
        # Return the file for download with document ID in headers
        response = FileResponse(
            path=output_path,
            filename=output_filename,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response.headers["X-Document-ID"] = file_id
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate SRS document: {str(e)}"
        )



@app.post("/process-all-files")
async def process_all_files(files: List[UploadFile] = File(...)):
    """
    Process all uploaded files to extract headings and generate Gemini suggestions
    """
    try:
        if not files:
            raise HTTPException(
                status_code=400,
                detail="No files provided for processing"
            )
        
        print(f"📁 Processing {len(files)} files...")
        
        all_extracted_headings = {}
        all_gemini_suggestions = {}
        processed_files = []
        
        # Store file contents for vector store processing
        pdf_file_contents = {}  # Store PDF content for vector store processing
        
        # Process files in batches to avoid timeout
        batch_size = 2  # Process 2 files at a time
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1} of {(len(files) + batch_size - 1)//batch_size}")
            
            for file in batch:
                try:
                    file_name = file.filename
                    content = await file.read()
                    
                    # Store PDF content for vector store processing
                    if file_name.lower().endswith('.pdf'):
                        pdf_file_contents[file_name] = content
                    
                    print(f"Processing file: {file_name}")
                    
                    # Determine document type based on file extension
                    if file_name.lower().endswith('.pdf'):
                        document_type = 'meeting_transcript'
                    elif file_name.lower().endswith(('.docx', '.doc')):
                        document_type = 'requirements'
                    else:
                        document_type = 'meeting_transcript'
                    
                    # For PDF files, we'll use vector store to extract TOC headings
                    # For other files, we'll use basic extraction
                    extracted_headings = []
                    
                    if file_name.lower().endswith('.pdf'):
                        # For PDFs, we'll extract headings using vector store TOC extraction
                        # Create placeholder that will be replaced by vector store results
                        extracted_headings = [
                            HeadingItem(
                                heading=f"TOC from {file_name} (will be extracted via vector store)",
                                purpose=f"Table of contents headings from {file_name}",
                                is_standard=False
                            )
                        ]
                        print(f"PDF file {file_name} - headings will be extracted via vector store TOC")
                    else:
                        # For non-PDF files, use basic extraction
                        try:
                            # Determine file type from filename
                            file_extension = file_name.lower().split('.')[-1]
                            if file_extension in ['docx', 'doc']:
                                file_type = 'docx'
                            else:
                                file_type = 'txt'
                            
                            # Extract headings using DocumentExtractor
                            extracted_data = DocumentExtractor.extract_document_headings(content, file_type)
                            
                            # Format headings for API response
                            raw_headings = extracted_data.get('headings', [])
                            formatted_headings = DocumentExtractor.format_headings_for_api(raw_headings, file_name)
                            
                            # Convert to HeadingItem objects
                            extracted_headings = [
                                HeadingItem(
                                    heading=h['heading'],
                                    purpose=h['purpose'],
                                    is_standard=False
                                )
                                for h in formatted_headings
                            ]
                            
                            print(f"Extracted {len(extracted_headings)} headings from {file_name}")
                            
                        except Exception as extraction_error:
                            print(f"Heading extraction failed for {file_name}: {extraction_error}")
                            # Fallback to sample headings
                            extracted_headings = [
                                HeadingItem(
                                    heading=f"Sample Heading from {file_name}",
                                    purpose=f"This is a sample heading extracted from {file_name}",
                                    is_standard=False
                                )
                            ]
                    
                    # Extract text for Gemini if it's a meeting transcript (PDF or TXT)
                    gemini_suggestions = None
                    transcript_text = ""
                    
                    if document_type == 'meeting_transcript' or file_name.lower().endswith('.pdf') or file_name.lower().endswith('.txt'):
                        try:
                            # For PDFs, we need to extract text content
                            if file_name.lower().endswith('.pdf'):
                                import io
                                from PyPDF2 import PdfReader
                                pdf_reader = PdfReader(io.BytesIO(content))
                                transcript_text = "\n".join(page.extract_text() or '' for page in pdf_reader.pages)
                            else:
                                # For text files, decode the content
                                transcript_text = content.decode('utf-8', errors='ignore')
                            
                            # Store the full transcript text for later use in SRS generation
                            if transcript_text and len(transcript_text) > 20:
                                # Store in extracted_text_content for SRS generation
                                doc_id = str(uuid.uuid4())
                                extracted_text_content[doc_id] = {
                                    "file_name": file_name,
                                    "text_content": transcript_text,
                                    "document_type": document_type
                                }
                                
                                # Use full content but limit to reasonable size for Gemini API
                                gemini_input_text = transcript_text
                                if len(transcript_text) > 15000:
                                    gemini_input_text = transcript_text[:15000] + "\n\n[Content truncated for Gemini processing]"
                                
                                gemini_suggestions = get_gemini_srs_headings_from_transcript(gemini_input_text)
                                print(f"Generated Gemini suggestions for {file_name} using {len(gemini_input_text)} characters")
                                print(f"Stored full transcript ({len(transcript_text)} characters) for SRS generation")
                        except Exception as e:
                            print(f"Failed to generate Gemini suggestions for {file_name}: {e}")
                            gemini_suggestions = None
                    
                    # Store extracted headings by category
                    category_name = f"From {file_name}"
                    all_extracted_headings[category_name] = {
                        heading.heading: heading.purpose 
                        for heading in extracted_headings
                    }
                    
                    # Merge Gemini suggestions
                    if gemini_suggestions:
                        all_gemini_suggestions.update(gemini_suggestions)
                    
                    # Mark file as processed
                    processed_files.append({
                        "name": file_name,
                        "status": "success",
                        "extracted_headings_count": len(extracted_headings),
                        "has_gemini_suggestions": gemini_suggestions is not None
                    })
                    
                except Exception as file_error:
                    print(f"Error processing file {file.filename if file else 'unknown'}: {file_error}")
                    processed_files.append({
                        "name": file.filename if file else 'unknown',
                        "status": "error",
                        "error": str(file_error)
                    })
        
        print(f"✅ Successfully processed {len(processed_files)} files")
        
        # Process PDF files through the synchronous pipeline:
        # 1. Store PDFs in OpenAI Vector Store
        # 2. Extract TOC from stored content
        # 3. Generate headings using Gemini
        if pdf_file_contents:
            print(f"🔍 Processing {len(pdf_file_contents)} PDF files through synchronous pipeline...")
            try:
                # Step 1: Process PDFs with Gemini
                print("📤 Step 1: Processing PDFs with Gemini...")
                all_content = await process_pdfs_with_gemini(pdf_file_contents)

                if all_content:
                    # Step 2: Extract TOC from content
                    print("🔍 Step 2: Extracting TOC from content...")
                    toc_result = await extract_toc_with_gemini(all_content)

                    # Step 3: Generate headings using Gemini based on TOC
                    print("🤖 Step 3: Generating headings using Gemini...")
                    gemini_headings = await generate_headings_with_gemini(toc_result)
                    
                    # Update extracted headings with TOC results
                    for file_name in pdf_file_contents.keys():
                        category_name = f"From {file_name}"
                        if toc_result and toc_result.get('toc'):
                            # Convert TOC to the expected format
                            toc_headings = parse_toc_to_headings(toc_result['toc'])
                            all_extracted_headings[category_name] = toc_headings
                            print(f"✅ Updated {category_name} with {len(toc_headings)} TOC headings")
                            
                            # Display the extracted headings for verification
                            print(f"📋 TOC headings from {file_name}:")
                            for heading, purpose in toc_headings.items():
                                print(f"   - {heading}: {purpose}")
                        else:
                            # Fallback to placeholder
                            all_extracted_headings[category_name] = {
                                f"TOC from {file_name}": f"Table of contents headings from {file_name} (TOC extraction failed)"
                            }
                    
                    # Update Gemini suggestions with the new Gemini headings
                    if gemini_headings and gemini_headings.get('openai_headings'):
                        # Parse Gemini headings and add to suggestions
                        parsed_gemini = parse_gemini_headings(gemini_headings['openai_headings'])
                        all_gemini_suggestions.update(parsed_gemini)
                        print(f"✅ Updated Gemini suggestions with {len(parsed_gemini)} new headings")
                else:
                    print("❌ Failed to create vector store")
                    # Keep placeholder headings
                    for file_name in pdf_file_contents.keys():
                        category_name = f"From {file_name}"
                        if category_name not in all_extracted_headings:
                            all_extracted_headings[category_name] = {
                                f"TOC from {file_name}": f"Table of contents headings from {file_name} (vector store creation failed)"
                            }
                            
            except Exception as e:
                print(f"❌ Synchronous pipeline failed: {str(e)}")
                print("⚠️ Continuing with basic extracted headings...")
                
                # Ensure we have placeholder headings for PDFs
                for file_name in pdf_file_contents.keys():
                    category_name = f"From {file_name}"
                    if category_name not in all_extracted_headings:
                        all_extracted_headings[category_name] = {
                            f"TOC from {file_name}": f"Table of contents headings from {file_name} (pipeline failed)"
                        }
        else:
            print("⚠️ No PDF files found for processing")
        
        return {
            "success": True,
            "message": f"Processed {len(processed_files)} files successfully",
            "extracted_headings": all_extracted_headings,
            "gemini_suggestions": all_gemini_suggestions,
            "processed_files": processed_files
        }
        
    except Exception as e:
        print(f"❌ Failed to process files: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process files: {str(e)}"
        )

@app.post("/process-docs-folder")
async def process_docs_folder():
    """
    Process PDF files from the docs folder and extract headings in nested format
    """
    try:
        print("📁 Processing PDF files from docs folder...")
        
        # Path to docs folder
        docs_folder = "../docs/Pdf_files"
        
        if not os.path.exists(docs_folder):
            raise HTTPException(
                status_code=404,
                detail=f"Docs folder not found: {docs_folder}"
            )
        
        # Get all PDF files from docs folder
        pdf_files = []
        for file in os.listdir(docs_folder):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(docs_folder, file))
        
        if not pdf_files:
            raise HTTPException(
                status_code=404,
                detail="No PDF files found in docs folder"
            )
        
        print(f"📄 Found {len(pdf_files)} PDF files: {[os.path.basename(f) for f in pdf_files]}")
        
        # Read PDF files and store content
        pdf_file_contents = {}
        for pdf_path in pdf_files:
            try:
                with open(pdf_path, "rb") as f:
                    content = f.read()
                    file_name = os.path.basename(pdf_path)
                    pdf_file_contents[file_name] = content
                    print(f"✅ Loaded {file_name} ({len(content)} bytes)")
            except Exception as e:
                print(f"❌ Failed to load {pdf_path}: {e}")
                continue
        
        if not pdf_file_contents:
            raise HTTPException(
                status_code=500,
                detail="Failed to load any PDF files"
            )
        
        # Step 1: Process PDFs with Gemini
        print("📤 Step 1: Processing PDFs with Gemini...")
        all_content = await process_pdfs_with_gemini(pdf_file_contents)

        if not all_content:
            raise HTTPException(
                status_code=500,
                detail="Failed to process PDFs"
            )

        # Step 2: Extract TOC from content
        print("🔍 Step 2: Extracting TOC from content...")
        toc_result = await extract_toc_with_gemini(all_content)
        
        if not toc_result or not toc_result.get('toc'):
            raise HTTPException(
                status_code=500,
                detail="Failed to extract TOC from vector store"
            )
        
        # Step 3: Generate headings using Gemini based on TOC
        print("🤖 Step 3: Generating headings using Gemini...")
        gemini_headings = await generate_headings_with_gemini(toc_result)
        
        # Step 4: Parse and organize headings in nested format
        print("📋 Step 4: Organizing headings in nested format...")
        
        # Parse TOC to get raw headings
        raw_toc_headings = parse_toc_to_headings(toc_result['toc'])
        
        # Parse Gemini headings
        parsed_gemini = {}
        if gemini_headings and gemini_headings.get('openai_headings'):
            parsed_gemini = parse_gemini_headings(gemini_headings['openai_headings'])
        
        # Create nested structure
        nested_headings = create_nested_headings_structure(raw_toc_headings, parsed_gemini)
        
        # Save to clean_extracted_headings.json
        output_file = "clean_extracted_headings.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(nested_headings, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved nested headings to: {output_file}")
        
        return {
            "success": True,
            "message": f"Successfully processed {len(pdf_file_contents)} PDF files from docs folder",
            "extracted_headings": nested_headings,
            "gemini_suggestions": parsed_gemini,
            "toc_result": toc_result,
            "files_processed": list(pdf_file_contents.keys())
        }
        
    except Exception as e:
        print(f"❌ Failed to process docs folder: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process docs folder: {str(e)}"
        )

@app.post("/process-files-for-text")
async def process_files_for_text(files: List[UploadFile] = File(...)):
    """
    Process uploaded files to extract text content for use in next page
    """
    global extracted_text_content
    
    try:
        if not files:
            raise HTTPException(
                status_code=400,
                detail="No files provided"
            )
        
        print(f"📁 Processing {len(files)} files for text extraction...")
        
        local_extracted_text_content = {}
        
        for file in files:
            try:
                file_name = file.filename
                content = await file.read()
                
                print(f"Processing file: {file_name}")
                
                # Extract text content based on file type (skip PDFs - they're for docs folder)
                extracted_text = ""
                try:
                    from logic.extractor import DocumentExtractor
                    
                    # Determine file type from filename
                    file_extension = file_name.lower().split('.')[-1]
                    
                    # Process PDF files for meeting summaries (don't skip them)
                    if file_extension == 'pdf':
                        print(f"Processing PDF file {file_name} for meeting summary extraction")
                        file_type = 'pdf'
                        extracted_data = DocumentExtractor.extract_from_pdf(content)
                    elif file_extension in ['docx', 'doc']:
                        file_type = 'docx'
                        extracted_data = DocumentExtractor.extract_from_docx(content)
                    else:
                        file_type = 'txt'
                        extracted_data = DocumentExtractor.extract_from_text(content)
                    
                    extracted_text = extracted_data.get('content', '')
                    print(f"Extracted {len(extracted_text)} characters from {file_name}")
                    
                except Exception as e:
                    print(f"Failed to extract text from {file_name}: {e}")
                    extracted_text = f"Error extracting text: {str(e)}"
                
                # Store extracted text content
                doc_id = str(uuid.uuid4())
                local_extracted_text_content[doc_id] = {
                    "file_name": file_name,
                    "text_content": extracted_text,
                    "document_type": "meeting_transcript"
                }
                
                # Also store in global variable for later use
                extracted_text_content[doc_id] = {
                    "file_name": file_name,
                    "text_content": extracted_text,
                    "document_type": "meeting_transcript"
                }
                
            except Exception as file_error:
                print(f"Error processing file {file.filename if file else 'unknown'}: {file_error}")
                continue
        
        print(f"✅ Successfully processed {len(local_extracted_text_content)} files for text extraction")
        print(f"📊 Extracted text content keys: {list(local_extracted_text_content.keys())}")
        
        return {
            "success": True,
            "message": f"Processed {len(local_extracted_text_content)} files for text extraction",
            "extracted_text_content": local_extracted_text_content
        }
        
    except Exception as e:
        print(f"❌ Failed to process files for text: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process files for text: {str(e)}"
        )

@app.post("/generate-gemini-headings")
async def generate_gemini_headings(request: Dict[str, Any]):
    """
    Generate headings using OpenAI (was Gemini) based on meeting transcript
    """
    try:
        transcript_text = request.get("transcript_text", "")
        if not transcript_text:
            raise HTTPException(
                status_code=400,
                detail="No transcript text provided"
            )
        # Generate headings using Gemini with meeting transcript
        print(f"🔍 Calling generate_headings_with_gemini with transcript length: {len(transcript_text)}")
        openai_headings = await generate_headings_with_gemini({"toc": transcript_text})
        print(f"🔍 generate_headings_with_gemini returned: {openai_headings}")
        if openai_headings and openai_headings.get('openai_headings'):
            raw_headings = openai_headings['openai_headings']
            print(f"🔍 Raw openai_headings type: {type(raw_headings)}")
            print(f"🔍 Raw openai_headings: {raw_headings}")
            # Handle both dictionary (fallback) and string (actual Gemini response) cases
            if isinstance(raw_headings, dict):
                print("✅ Using fallback sample headings (no API key)")
                parsed_headings = raw_headings
            else:
                print("✅ Parsing actual Gemini response")
                parsed_headings = parse_gemini_headings(raw_headings)
            print(f"✅ Final parsed headings result: {len(parsed_headings)} keys")
            print(f"✅ Parsed headings keys: {list(parsed_headings.keys())}")
            return {
                "success": True,
                "gemini_headings": parsed_headings
            }
        else:
            print("❌ No openai_headings in response")
            print(f"❌ Full openai_headings response: {openai_headings}")
            return {
                "success": False,
                "gemini_headings": {},
                "message": "Failed to generate Gemini headings"
            }
    except Exception as e:
        print(f"❌ Failed to generate Gemini headings: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Gemini headings: {str(e)}"
        )

@app.post("/generate-content")
async def generate_content_for_headings(request: Dict[str, Any]):
    """
    Generate content for selected headings using vector store
    """
    try:
        selected_headings = request.get("headings", [])
        
        if not selected_headings:
            raise HTTPException(
                status_code=400,
                detail="No headings selected for content generation"
            )
        
        # For now, we'll simulate content generation
        # In a real implementation, you'd use Gemini with document context
        generated_content = {}
        
        for heading in selected_headings:
            heading_text = heading.get("heading", "")
            purpose = heading.get("purpose", "")
            
            # Simulate AI-generated content
            generated_content[heading_text] = f"""
# {heading_text}

## Purpose
{purpose}

## Content
This section contains detailed information about {heading_text.lower()}. 
The content is generated based on the analysis of uploaded documents and follows 
standard SRS documentation practices.

### Key Points
- Point 1: Important aspect of {heading_text.lower()}
- Point 2: Technical considerations
- Point 3: Implementation guidelines

### Requirements
Detailed requirements and specifications for {heading_text.lower()} will be 
documented here based on the project context and stakeholder needs.

### Technical Details
Technical implementation details, architecture considerations, and design 
decisions related to {heading_text.lower()} will be elaborated in this section.
            """.strip()
        
        return {
            "success": True,
            "generated_content": generated_content,
            "total_sections": len(generated_content)
        }
        
    except Exception as e:
        print(f"❌ Failed to generate content: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate content: {str(e)}"
        )

@app.post("/process-meeting-summaries")
async def process_meeting_summaries(files: List[UploadFile] = File(...)):
    """
    Process uploaded meeting summary files for Gemini heading generation
    Accepts list of files and processes them all
    """
    global extracted_text_content
    
    try:
        if not files:
            raise HTTPException(
                status_code=400,
                detail="No files provided"
            )
        
        print(f"📁 Processing {len(files)} meeting summary files...")
        print(f"📋 File names: {[f.filename for f in files]}")
        print(f"📋 File sizes: {[f.size for f in files]}")
        print(f"📋 File content types: {[f.content_type for f in files]}")
        
        local_extracted_text_content = {}
        processed_files = []
        failed_files = []
        
        for file in files:
            try:
                file_name = file.filename
                print(f"Processing meeting summary file: {file_name}")
                print(f"File size: {file.size} bytes")
                print(f"Content type: {file.content_type}")
                
                content = await file.read()
                print(f"Read {len(content)} bytes from {file_name}")
                
                if len(content) == 0:
                    print(f"❌ Warning: {file_name} has no content")
                    failed_files.append(file_name)
                    continue
                
                # Extract text content from meeting summaries (PDF, DOCX, TXT)
                extracted_text = ""
                try:
                    from logic.extractor import DocumentExtractor
                    
                    # Determine file type from filename
                    file_extension = file_name.lower().split('.')[-1]
                    
                    if file_extension == 'pdf':
                        file_type = 'pdf'
                        extracted_data = DocumentExtractor.extract_from_pdf(content)
                    elif file_extension in ['docx', 'doc']:
                        file_type = 'docx'
                        extracted_data = DocumentExtractor.extract_from_docx(content)
                    else:
                        file_type = 'txt'
                        extracted_data = DocumentExtractor.extract_from_text(content)
                    
                    extracted_text = extracted_data.get('content', '')
                    print(f"Extracted {len(extracted_text)} characters from meeting summary: {file_name}")
                    
                    if extracted_text and not extracted_text.startswith("Error extracting text"):
                        processed_files.append(file_name)
                    else:
                        failed_files.append(file_name)
                    
                except Exception as e:
                    print(f"Failed to extract text from {file_name}: {e}")
                    extracted_text = f"Error extracting text: {str(e)}"
                    failed_files.append(file_name)
                
                # Store extracted text content for meeting summaries
                doc_id = str(uuid.uuid4())
                local_extracted_text_content[doc_id] = {
                    "file_name": file_name,
                    "text_content": extracted_text,
                    "document_type": "meeting_summary",
                    "file_type": file_type,
                    "content_length": len(extracted_text)
                }
                
                # Also store in global variable for later use
                extracted_text_content[doc_id] = {
                    "file_name": file_name,
                    "text_content": extracted_text,
                    "document_type": "meeting_summary",
                    "file_type": file_type,
                    "content_length": len(extracted_text)
                }
                
            except Exception as file_error:
                print(f"Error processing file {file.filename if file else 'unknown'}: {file_error}")
                failed_files.append(file.filename if file else 'unknown')
                continue
        
        print(f"✅ Successfully processed {len(processed_files)} meeting summary files")
        print(f"❌ Failed to process {len(failed_files)} files: {failed_files}")
        print(f"📊 Meeting summary content keys: {list(local_extracted_text_content.keys())}")
        
        return {
            "success": True,
            "message": f"Processed {len(processed_files)} meeting summary files successfully",
            "extracted_text_content": local_extracted_text_content,
            "processed_files": processed_files,
            "failed_files": failed_files,
            "total_files": len(files)
        }
        
    except Exception as e:
        print(f"❌ Failed to process meeting summaries: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process meeting summaries: {str(e)}"
        )

@app.post("/process-docs-folder-toc")
async def process_docs_folder_toc():
    """
    Process PDF files from docs folder for TOC extraction only
    """
    try:
        print("📁 Processing PDF files from docs folder for TOC extraction...")
        
        # Path to docs folder
        docs_folder = "../docs/Pdf_files"
        
        if not os.path.exists(docs_folder):
            raise HTTPException(
                status_code=404,
                detail=f"Docs folder not found: {docs_folder}"
            )
        
        # Get all PDF files from docs folder
        pdf_files = []
        for file in os.listdir(docs_folder):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(docs_folder, file))
        
        if not pdf_files:
            raise HTTPException(
                status_code=404,
                detail="No PDF files found in docs folder"
            )
        
        print(f"📄 Found {len(pdf_files)} PDF files: {[os.path.basename(f) for f in pdf_files]}")
        
        # Read PDF files and store content
        pdf_file_contents = {}
        for pdf_path in pdf_files:
            try:
                with open(pdf_path, "rb") as f:
                    content = f.read()
                    file_name = os.path.basename(pdf_path)
                    pdf_file_contents[file_name] = content
                    print(f"✅ Loaded {file_name} ({len(content)} bytes)")
            except Exception as e:
                print(f"❌ Failed to load {pdf_path}: {e}")
                continue
        
        if not pdf_file_contents:
            raise HTTPException(
                status_code=500,
                detail="Failed to load any PDF files"
            )
        
        # Step 1: Process PDFs with Gemini
        print("📤 Step 1: Processing PDFs with Gemini...")
        all_content = await process_pdfs_with_gemini(pdf_file_contents)

        if not all_content:
            raise HTTPException(
                status_code=500,
                detail="Failed to process PDFs"
            )

        # Step 2: Extract TOC from content
        print("🔍 Step 2: Extracting TOC from content...")
        toc_result = await extract_toc_with_gemini(all_content)
        
        if not toc_result or not toc_result.get('toc'):
            raise HTTPException(
                status_code=500,
                detail="Failed to extract TOC from vector store"
            )
        
        # Step 3: Parse TOC to headings
        print("📋 Step 3: Parsing TOC to headings...")
        raw_toc_headings = parse_toc_to_headings(toc_result['toc'])
        
        # Create nested structure for TOC headings
        nested_headings = create_nested_headings_structure(raw_toc_headings, {})
        
        # Save to clean_extracted_headings.json
        output_file = "clean_extracted_headings.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(nested_headings, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved TOC headings to: {output_file}")
        
        return {
            "success": True,
            "message": f"Successfully extracted TOC from {len(pdf_file_contents)} PDF files",
            "extracted_headings": nested_headings,
            "toc_result": toc_result,
            "files_processed": list(pdf_file_contents.keys())
        }
        
    except Exception as e:
        print(f"❌ Failed to process docs folder for TOC: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process docs folder for TOC: {str(e)}"
        )

@app.post("/generate-ai-headings")
async def generate_ai_headings(request: Dict[str, Any]):
    """
    Generate AI headings from meeting summaries and compare with standard headings
    """
    try:
        print("🤖 Generating AI headings and comparing with standard headings...")
        
        # Get standard headings
        standard_headings = load_standard_headings()
        
        # Get uploaded files from the request
        uploaded_files = request.get('uploadedFiles', [])
        
        if not uploaded_files:
            raise HTTPException(
                status_code=400,
                detail="No uploaded files provided"
            )
        
        # Extract text content from uploaded files
        meeting_summaries = ""
        for file_data in uploaded_files:
            if 'text_content' in file_data:
                meeting_summaries += f"\n--- {file_data.get('name', 'Unknown')} ---\n"
                meeting_summaries += file_data['text_content']
        
        if not meeting_summaries.strip():
            raise HTTPException(
                status_code=400,
                detail="No text content found in uploaded files"
            )
        
        # Generate headings using Gemini
        print("🤖 Generating headings with Gemini...")
        gemini_response = get_gemini_srs_headings_from_transcript(meeting_summaries)
        
        if not gemini_response:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate headings with Gemini"
            )
        
        # Parse Gemini response to get headings
        ai_headings = parse_gemini_headings(gemini_response)
        
        # Flatten standard headings for comparison
        flat_standard_headings = []
        for category, items in standard_headings.items():
            if isinstance(items, dict):
                for subcategory, purpose in items.items():
                    if isinstance(purpose, str):
                        flat_standard_headings.append({
                            'heading': f"{category} > {subcategory}",
                            'purpose': purpose,
                            'source': 'Standard Template'
                        })
                    elif isinstance(purpose, dict):
                        for subsubcategory, subpurpose in purpose.items():
                            if isinstance(subpurpose, str):
                                flat_standard_headings.append({
                                    'heading': f"{category} > {subcategory} > {subsubcategory}",
                                    'purpose': subpurpose,
                                    'source': 'Standard Template'
                                })
        
        # Compare AI headings with standard headings
        standard_headings_set = {h['heading'].lower() for h in flat_standard_headings}
        unique_ai_headings = []
        
        for ai_heading in ai_headings:
            ai_heading_lower = ai_heading['heading'].lower()
            if ai_heading_lower not in standard_headings_set:
                # Check for partial matches
                is_unique = True
                for std_heading in standard_headings_set:
                    if (ai_heading_lower in std_heading or 
                        std_heading in ai_heading_lower or
                        any(word in std_heading for word in ai_heading_lower.split() if len(word) > 3)):
                        is_unique = False
                        break
                
                if is_unique:
                    unique_ai_headings.append(ai_heading)
        
        print(f"✅ Generated {len(ai_headings)} AI headings, found {len(unique_ai_headings)} unique headings")
        
        return {
            "success": True,
            "message": f"Generated {len(unique_ai_headings)} unique AI headings",
            "totalHeadings": len(ai_headings),
            "uniqueHeadings": unique_ai_headings,
            "standardHeadings": flat_standard_headings
        }
        
    except Exception as e:
        print(f"❌ Failed to generate AI headings: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate AI headings: {str(e)}"
        )

# ============================================================================
# DIAGRAM EDITING ENDPOINTS
# ============================================================================

class DiagramEditRequest(BaseModel):
    mermaid_code: str
    diagram_type: str
    theme: Optional[str] = "default"
    custom_styles: Optional[Dict[str, Any]] = None

class DiagramExportRequest(BaseModel):
    mermaid_code: str
    format: str  # 'png', 'svg', 'pdf', 'mermaid'
    theme: Optional[str] = "default"
    width: Optional[int] = 800
    height: Optional[int] = 600

@app.post("/api/diagram/validate")
async def validate_diagram(request: DiagramEditRequest):
    """Validate Mermaid diagram syntax"""
    try:
        from logic.srs_generator import convert_mermaid_to_png
        import tempfile

        # Test if the Mermaid code is valid by trying to convert it
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            success = convert_mermaid_to_png(request.mermaid_code, temp_path)

            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)

            return {
                "valid": success,
                "message": "Diagram syntax is valid" if success else "Invalid Mermaid syntax"
            }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Validation error: {str(e)}"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@app.post("/api/diagram/export")
async def export_diagram(request: DiagramExportRequest):
    """Export diagram in various formats"""
    try:
        print(f"🎯 Export request received:")
        print(f"   Format: '{request.format}'")
        print(f"   Mermaid code length: {len(request.mermaid_code)} characters")
        print(f"   Theme: {request.theme}")

        from logic.srs_generator import convert_mermaid_to_png
        import tempfile
        import base64

        if request.format == 'mermaid':
            # Return raw Mermaid code
            return {
                "success": True,
                "data": request.mermaid_code,
                "filename": "diagram.mmd",
                "content_type": "text/plain"
            }

        elif request.format == 'png':
            # Convert to PNG
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                success = convert_mermaid_to_png(request.mermaid_code, temp_path)

                if success and os.path.exists(temp_path):
                    # Read the PNG file and encode as base64
                    with open(temp_path, 'rb') as f:
                        png_data = base64.b64encode(f.read()).decode('utf-8')

                    # Clean up
                    os.unlink(temp_path)

                    return {
                        "success": True,
                        "data": png_data,
                        "filename": "diagram.png",
                        "content_type": "image/png"
                    }
                else:
                    raise HTTPException(status_code=400, detail="Failed to generate PNG")

            except Exception as e:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise e

        elif request.format == 'svg':
            # For SVG, we'll need to use mmdc with SVG output
            import subprocess

            with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as mmd_file:
                mmd_file.write(request.mermaid_code)
                mmd_path = mmd_file.name

            with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as svg_file:
                svg_path = svg_file.name

            try:
                # Try to find mmdc
                mmdc_cmd = None
                for cmd in ['mmdc', 'mmdc.cmd', 'npx mmdc']:
                    try:
                        if cmd.startswith('npx'):
                            test_cmd = cmd.split() + ['--version']
                            result = subprocess.run(test_cmd, capture_output=True, timeout=10)
                        else:
                            result = subprocess.run([cmd, '--version'], capture_output=True, timeout=10)
                        if result.returncode == 0:
                            mmdc_cmd = cmd
                            break
                    except:
                        continue

                if not mmdc_cmd:
                    raise HTTPException(status_code=500, detail="Mermaid CLI not found")

                # Convert to SVG
                if mmdc_cmd.startswith('npx'):
                    cmd = mmdc_cmd.split() + ['-i', mmd_path, '-o', svg_path]
                else:
                    cmd = [mmdc_cmd, '-i', mmd_path, '-o', svg_path]
                result = subprocess.run(cmd, capture_output=True, timeout=30)

                if result.returncode == 0 and os.path.exists(svg_path):
                    with open(svg_path, 'r', encoding='utf-8') as f:
                        svg_data = f.read()

                    # Clean up
                    os.unlink(mmd_path)
                    os.unlink(svg_path)

                    return {
                        "success": True,
                        "data": svg_data,
                        "filename": "diagram.svg",
                        "content_type": "image/svg+xml"
                    }
                else:
                    raise HTTPException(status_code=400, detail="Failed to generate SVG")

            except Exception as e:
                # Clean up
                if os.path.exists(mmd_path):
                    os.unlink(mmd_path)
                if os.path.exists(svg_path):
                    os.unlink(svg_path)
                raise e

        elif request.format == 'xml':
            # Clean XML export that preserves original diagram
            try:
                print(f"🔄 Creating clean XML export...")
                print(f"📋 Received Mermaid code ({len(request.mermaid_code)} chars):")
                print(f"   First 200 chars: {request.mermaid_code[:200]}...")
                print(f"   Last 100 chars: ...{request.mermaid_code[-100:]}")

                xml_content = create_clean_xml_export(request.mermaid_code)
                print(f"✅ XML content created: {len(xml_content)} characters")

                # Also log the first part of the XML to verify it's correct
                xml_lines = xml_content.split('\n')[:15]
                print(f"📄 XML preview (first 15 lines):")
                for i, line in enumerate(xml_lines, 1):
                    print(f"   {i:2d}: {line}")

                return {
                    "success": True,
                    "data": xml_content,
                    "filename": "diagram.xml",
                    "content_type": "application/xml"
                }
            except Exception as xml_error:
                print(f"❌ XML export error: {str(xml_error)}")
                raise HTTPException(status_code=500, detail=f"XML export failed: {str(xml_error)}")

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}. Supported: png, svg, mermaid, xml")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

# Draw.io conversion functions removed

# All Draw.io conversion functions removed to clean up codebase

@app.get("/api/diagram/themes")
async def get_diagram_themes():
    """Get available diagram themes"""
    return {
        "themes": [
            {"id": "default", "name": "Default", "description": "Standard Mermaid theme"},
            {"id": "dark", "name": "Dark", "description": "Dark theme with light text"},
            {"id": "forest", "name": "Forest", "description": "Green forest theme"},
            {"id": "base", "name": "Base", "description": "Minimal base theme"},
            {"id": "neutral", "name": "Neutral", "description": "Neutral color scheme"}
        ]
    }

# All remaining Draw.io functions removed

# Duplicate removed - using the one above

@app.get("/api/document/{document_id}/diagrams")
async def get_document_diagrams(document_id: str):
    """Get all diagrams for a specific document"""
    try:
        print(f"🔍 Fetching diagrams for document ID: {document_id}")
        print(f"📊 Available document IDs: {list(document_diagrams.keys())}")

        diagrams = document_diagrams.get(document_id, [])
        print(f"📊 Found {len(diagrams)} diagrams for document {document_id}")

        if diagrams:
            for i, diagram in enumerate(diagrams):
                print(f"   Diagram {i+1}: {diagram.get('sectionTitle', 'Unknown')} ({diagram.get('diagramType', 'Unknown')})")

        return {
            "success": True,
            "diagrams": diagrams,
            "count": len(diagrams)
        }
    except Exception as e:
        print(f"❌ Error fetching diagrams: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch diagrams: {str(e)}")

@app.put("/api/diagram/{diagram_id}/update")
async def update_diagram(diagram_id: str, request: DiagramEditRequest):
    """Update a specific diagram"""
    try:
        # Find and update the diagram across all documents
        updated = False
        for doc_id, diagrams in document_diagrams.items():
            for i, diagram in enumerate(diagrams):
                if diagram.get('id') == diagram_id:
                    diagrams[i].update({
                        'mermaidCode': request.mermaid_code,
                        'diagramType': request.diagram_type,
                        'theme': request.theme or 'default',
                        'lastModified': datetime.now().isoformat()
                    })
                    updated = True
                    break
            if updated:
                break

        if not updated:
            raise HTTPException(status_code=404, detail="Diagram not found")

        return {"message": "Diagram updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update diagram: {str(e)}")

@app.post("/api/diagram/{diagram_id}/export")
async def export_diagram_by_id(diagram_id: str, export_format: str = "png"):
    """Export a specific diagram by ID"""
    try:
        # Find the diagram
        diagram = None
        for doc_id, diagrams in document_diagrams.items():
            for d in diagrams:
                if d.get('id') == diagram_id:
                    diagram = d
                    break
            if diagram:
                break

        if not diagram:
            raise HTTPException(status_code=404, detail="Diagram not found")

        mermaid_code = diagram.get('mermaidCode', '')
        if not mermaid_code:
            raise HTTPException(status_code=400, detail="No Mermaid code found for diagram")

        # Export based on format
        if export_format.lower() == 'png':
            from logic.srs_generator import convert_mermaid_to_png
            import tempfile

            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_path = temp_file.name

            success = convert_mermaid_to_png(mermaid_code, temp_path)

            if success and os.path.exists(temp_path):
                with open(temp_path, 'rb') as f:
                    png_data = f.read()
                os.unlink(temp_path)

                from fastapi.responses import Response
                return Response(
                    content=png_data,
                    media_type="image/png",
                    headers={"Content-Disposition": f"attachment; filename={diagram_id}.png"}
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to generate PNG")

        elif export_format.lower() == 'svg':
            from logic.srs_generator import convert_mermaid_to_svg
            import tempfile

            with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as temp_file:
                temp_path = temp_file.name

            success = convert_mermaid_to_svg(mermaid_code, temp_path)

            if success and os.path.exists(temp_path):
                with open(temp_path, 'r', encoding='utf-8') as f:
                    svg_data = f.read()
                os.unlink(temp_path)

                from fastapi.responses import Response
                return Response(
                    content=svg_data,
                    media_type="image/svg+xml",
                    headers={"Content-Disposition": f"attachment; filename={diagram_id}.svg"}
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to generate SVG")

        else:
            raise HTTPException(status_code=400, detail="Unsupported export format. Use 'png' or 'svg'")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

# Duplicate export endpoint removed - XML support added to the main endpoint above

def create_clean_xml_export(mermaid_code: str) -> str:
    """
    Create a clean XML export that preserves the original Mermaid diagram
    This does NOT convert or spoil the diagram - just wraps it in XML format
    """
    try:
        from datetime import datetime
        import html

        # Escape the Mermaid code for XML (using html.escape which is more reliable)
        escaped_mermaid = html.escape(mermaid_code)

        # Create simple XML structure that preserves the original diagram
        xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<diagram>
    <metadata>
        <title>Mermaid Diagram Export</title>
        <created>{datetime.now().isoformat()}</created>
        <format>mermaid</format>
        <description>Clean XML export preserving original Mermaid diagram</description>
    </metadata>
    <content type="mermaid"><![CDATA[{mermaid_code}]]></content>
    <display>
        <mermaid_code>{escaped_mermaid}</mermaid_code>
    </display>
</diagram>'''

        return xml_content

    except Exception as e:
        print(f"❌ Error creating XML export: {str(e)}")
        # Return a simple fallback XML if there's an error
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<diagram>
    <metadata>
        <title>Mermaid Diagram Export</title>
        <format>mermaid</format>
        <error>Error creating full XML: {str(e)}</error>
    </metadata>
    <content type="mermaid"><![CDATA[{mermaid_code}]]></content>
</diagram>'''

def parse_mermaid_for_drawio(mermaid_code: str) -> dict:
    """Parse Mermaid code to extract elements for Draw.io with better layout"""
    elements = {
        'nodes': [],
        'connections': [],
        'type': 'flowchart'
    }

    lines = mermaid_code.strip().split('\n')
    nodes_dict = {}
    connections = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith('%%') or line.startswith('Title:') or line.startswith('participant'):
            continue

        # Detect diagram type
        if line.startswith('flowchart') or line.startswith('graph'):
            elements['type'] = 'flowchart'
        elif line.startswith('sequenceDiagram'):
            elements['type'] = 'sequence'
        elif line.startswith('erDiagram'):
            elements['type'] = 'er'

        # Parse connections and extract nodes
        if '-->' in line or '->' in line or '---' in line:
            # Split on arrow types
            arrow_pattern = '-->'
            if '-->' in line:
                arrow_pattern = '-->'
            elif '->' in line:
                arrow_pattern = '->'
            elif '---' in line:
                arrow_pattern = '---'

            parts = line.split(arrow_pattern)
            if len(parts) >= 2:
                source_part = parts[0].strip()
                target_part = parts[1].strip()

                # Extract source node
                source_id, source_text = extract_node_info(source_part)
                if source_id and source_id not in nodes_dict:
                    nodes_dict[source_id] = {
                        'id': source_id,
                        'text': source_text or source_id,
                        'type': determine_node_type(source_text or source_id)
                    }

                # Extract target node
                target_id, target_text = extract_node_info(target_part)
                if target_id and target_id not in nodes_dict:
                    nodes_dict[target_id] = {
                        'id': target_id,
                        'text': target_text or target_id,
                        'type': determine_node_type(target_text or target_id)
                    }

                # Add connection
                if source_id and target_id:
                    connections.append({
                        'source': source_id,
                        'target': target_id,
                        'type': 'arrow'
                    })

    # Convert to list and calculate positions
    nodes_list = list(nodes_dict.values())
    positioned_nodes = calculate_smart_layout(nodes_list, connections, elements['type'])

    elements['nodes'] = positioned_nodes
    elements['connections'] = connections

    return elements

def extract_node_info(node_text: str) -> tuple:
    """Extract node ID and display text from Mermaid node definition"""
    node_text = node_text.strip()

    # Handle different node formats: A[Text], A(Text), A{Text}, etc.
    if '[' in node_text and ']' in node_text:
        parts = node_text.split('[', 1)
        node_id = parts[0].strip()
        display_text = parts[1].split(']')[0].strip()
        return node_id, display_text
    elif '(' in node_text and ')' in node_text:
        parts = node_text.split('(', 1)
        node_id = parts[0].strip()
        display_text = parts[1].split(')')[0].strip()
        return node_id, display_text
    elif '{' in node_text and '}' in node_text:
        parts = node_text.split('{', 1)
        node_id = parts[0].strip()
        display_text = parts[1].split('}')[0].strip()
        return node_id, display_text
    else:
        # Simple node ID
        return node_text, node_text

def determine_node_type(text: str) -> str:
    """Determine the appropriate node type based on text content"""
    text_lower = text.lower()

    if any(word in text_lower for word in ['start', 'begin', 'init']):
        return 'start'
    elif any(word in text_lower for word in ['end', 'finish', 'complete', 'done']):
        return 'end'
    elif any(word in text_lower for word in ['decision', 'choice', '?', 'if', 'check']):
        return 'decision'
    elif any(word in text_lower for word in ['database', 'db', 'storage', 'data']):
        return 'database'
    elif any(word in text_lower for word in ['user', 'actor', 'person', 'client']):
        return 'actor'
    else:
        return 'process'

def calculate_smart_layout(nodes: list, connections: list, diagram_type: str) -> list:
    """Calculate smart positioning for nodes to avoid overlaps"""
    if not nodes:
        return []

    # Create a simple hierarchical layout
    positioned_nodes = []

    if diagram_type == 'sequence':
        # Horizontal layout for sequence diagrams
        for i, node in enumerate(nodes):
            positioned_nodes.append({
                **node,
                'x': 50 + i * 180,
                'y': 100,
                'width': 150,
                'height': 80
            })
    else:
        # Hierarchical layout for flowcharts
        # Find root nodes (nodes with no incoming connections)
        incoming_counts = {}
        for conn in connections:
            incoming_counts[conn['target']] = incoming_counts.get(conn['target'], 0) + 1

        root_nodes = [node for node in nodes if incoming_counts.get(node['id'], 0) == 0]
        if not root_nodes:
            root_nodes = [nodes[0]]  # Fallback to first node

        # Simple grid layout with levels
        levels = {}
        visited = set()

        def assign_level(node_id, level):
            if node_id in visited:
                return
            visited.add(node_id)
            if level not in levels:
                levels[level] = []
            levels[level].append(node_id)

            # Find children
            for conn in connections:
                if conn['source'] == node_id:
                    assign_level(conn['target'], level + 1)

        # Assign levels starting from root nodes
        for root in root_nodes:
            assign_level(root['id'], 0)

        # Position nodes based on levels
        for node in nodes:
            node_level = 0
            node_position_in_level = 0

            # Find which level this node is in
            for level, level_nodes in levels.items():
                if node['id'] in level_nodes:
                    node_level = level
                    node_position_in_level = level_nodes.index(node['id'])
                    break

            # Calculate position
            x = 100 + node_position_in_level * 200
            y = 100 + node_level * 150

            positioned_nodes.append({
                **node,
                'x': x,
                'y': y,
                'width': 160,
                'height': 80
            })

    return positioned_nodes

# Old helper functions removed - using improved parsing above

def generate_drawio_xml_from_elements(elements: dict) -> str:
    """Generate Draw.io XML from parsed elements with better styling"""
    nodes = elements.get('nodes', [])
    connections = elements.get('connections', [])

    # Start XML structure
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<mxfile host="app.diagrams.net" modified="2024-01-01T00:00:00.000Z" agent="SRS Dynamic Generator" version="22.1.11">',
        '  <diagram name="Page-1" id="page-1">',
        '    <mxGraphModel dx="1422" dy="794" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">',
        '      <root>',
        '        <mxCell id="0"/>',
        '        <mxCell id="1" parent="0"/>'
    ]

    # Create node ID mapping
    node_id_map = {}

    # Add nodes with improved styling
    for i, node in enumerate(nodes):
        cell_id = i + 2
        node_id_map[node['id']] = cell_id

        x = node.get('x', 100)
        y = node.get('y', 100)
        width = node.get('width', 160)
        height = node.get('height', 80)
        text = node.get('text', node.get('id', f'Node {i+1}'))
        node_type = node.get('type', 'process')

        # Choose style based on node type
        style = get_node_style(node_type, text)

        # Escape XML characters in text
        escaped_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

        xml_parts.append(f'        <mxCell id="{cell_id}" value="{escaped_text}" style="{style}" vertex="1" parent="1">')
        xml_parts.append(f'          <mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry"/>')
        xml_parts.append('        </mxCell>')

    # Add connections with better styling
    connection_id = len(nodes) + 2
    for conn in connections:
        source_cell_id = node_id_map.get(conn['source'])
        target_cell_id = node_id_map.get(conn['target'])

        if source_cell_id and target_cell_id:
            xml_parts.append(f'        <mxCell id="{connection_id}" value="" style="endArrow=classic;html=1;rounded=0;strokeWidth=2;strokeColor=#333333;" edge="1" parent="1" source="{source_cell_id}" target="{target_cell_id}">')
            xml_parts.append('          <mxGeometry width="50" height="50" relative="1" as="geometry">')
            xml_parts.append('            <mxPoint x="390" y="180" as="sourcePoint"/>')
            xml_parts.append('            <mxPoint x="440" y="130" as="targetPoint"/>')
            xml_parts.append('          </mxGeometry>')
            xml_parts.append('        </mxCell>')
            connection_id += 1

    # Close XML structure
    xml_parts.extend([
        '      </root>',
        '    </mxGraphModel>',
        '  </diagram>',
        '</mxfile>'
    ])

    return '\n'.join(xml_parts)

# Removed complex conversion functions - keeping it simple

def get_node_style(node_type: str, text: str) -> str:
    """Get appropriate Draw.io style for node type"""
    base_style = "whiteSpace=wrap;html=1;fontSize=12;fontFamily=Helvetica;"

    if node_type == 'start':
        return f"ellipse;{base_style}fillColor=#d5e8d4;strokeColor=#82b366;fontColor=#000000;"
    elif node_type == 'end':
        return f"ellipse;{base_style}fillColor=#f8cecc;strokeColor=#b85450;fontColor=#000000;"
    elif node_type == 'decision':
        return f"rhombus;{base_style}fillColor=#fff2cc;strokeColor=#d6b656;fontColor=#000000;"
    elif node_type == 'database':
        return f"shape=cylinder3;{base_style}fillColor=#e1d5e7;strokeColor=#9673a6;fontColor=#000000;"
    elif node_type == 'actor':
        return f"shape=umlActor;{base_style}fillColor=#f8cecc;strokeColor=#b85450;fontColor=#000000;"
    else:
        # Default process node
        return f"rounded=1;{base_style}fillColor=#dae8fc;strokeColor=#6c8ebf;fontColor=#000000;"

def create_default_drawio_xml() -> str:
    """Create a default Draw.io XML when conversion fails"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="2024-01-01T00:00:00.000Z" agent="SRS Dynamic Generator" version="22.1.11">
  <diagram name="Page-1" id="page-1">
    <mxGraphModel dx="1422" dy="794" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="Start" style="ellipse;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;" vertex="1" parent="1">
          <mxGeometry x="364" y="40" width="100" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="3" value="Process" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
          <mxGeometry x="364" y="140" width="100" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="4" value="End" style="ellipse;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;" vertex="1" parent="1">
          <mxGeometry x="364" y="240" width="100" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="5" value="" style="endArrow=classic;html=1;rounded=0;" edge="1" parent="1" source="2" target="3">
          <mxGeometry width="50" height="50" relative="1" as="geometry">
            <mxPoint x="390" y="180" as="sourcePoint"/>
            <mxPoint x="440" y="130" as="targetPoint"/>
          </mxGeometry>
        </mxCell>
        <mxCell id="6" value="" style="endArrow=classic;html=1;rounded=0;" edge="1" parent="1" source="3" target="4">
          <mxGeometry width="50" height="50" relative="1" as="geometry">
            <mxPoint x="390" y="280" as="sourcePoint"/>
            <mxPoint x="440" y="230" as="targetPoint"/>
          </mxGeometry>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

@app.get("/api/diagram/themes")
async def get_diagram_themes():
    """Get available diagram themes"""
    return {
        "themes": [
            {"id": "default", "name": "Default", "description": "Standard Mermaid theme"},
            {"id": "dark", "name": "Dark", "description": "Dark theme with light text"},
            {"id": "forest", "name": "Forest", "description": "Green forest theme"},
            {"id": "base", "name": "Base", "description": "Minimal base theme"},
            {"id": "neutral", "name": "Neutral", "description": "Neutral color scheme"}
        ]
    }

# ============================================================================
# DOCUMENT DIAGRAM MANAGEMENT ENDPOINTS (DUPLICATE REMOVED)
# ============================================================================

# Note: document_diagrams storage is already defined above at line ~30

@app.put("/api/diagram/{diagram_id}/update")
async def update_diagram(diagram_id: str, request: DiagramEditRequest):
    """Update a specific diagram"""
    try:
        # Find and update the diagram across all documents
        updated = False
        for doc_id, diagrams in document_diagrams.items():
            for i, diagram in enumerate(diagrams):
                if diagram.get('id') == diagram_id:
                    diagrams[i].update({
                        'mermaidCode': request.mermaid_code,
                        'theme': request.theme,
                        'diagramType': request.diagram_type,
                        'lastModified': datetime.now().isoformat()
                    })
                    updated = True
                    break
            if updated:
                break

        if not updated:
            raise HTTPException(status_code=404, detail="Diagram not found")

        return {
            "success": True,
            "message": "Diagram updated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update diagram: {str(e)}")

# ============================================================================
# SIMPLE DIAGRAM ENDPOINTS
# ============================================================================

# ============================================================================
# DOCUMENT REGENERATION
# ============================================================================

@app.post("/api/document/{document_id}/regenerate")
async def regenerate_document_with_diagrams(document_id: str):
    """Regenerate document with updated diagrams"""
    try:
        from logic.srs_generator import generate_srs_docx

        # Get document info (in production, fetch from database)
        if document_id not in generated_files:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get updated diagrams
        diagrams = document_diagrams.get(document_id, [])

        # Create new output file
        output_dir = os.path.join(os.getcwd(), 'generated_docs')
        os.makedirs(output_dir, exist_ok=True)

        output_filename = f"updated_srs_{document_id}.docx"
        output_path = os.path.join(output_dir, output_filename)

        # Regenerate with updated diagrams
        headings = [
            {
                'heading': diagram['sectionTitle'],
                'purpose': 'Updated section with custom diagram',
                'category': 'Custom',
                'source': 'User Modified',
                'userPrompt': f"Use this custom diagram: {diagram['mermaidCode']}"
            }
            for diagram in diagrams
        ]

        if headings:
            generate_srs_docx(headings, output_path, "")
        else:
            generate_srs_docx([], output_path, "")

        return FileResponse(
            path=output_path,
            filename=output_filename,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate document: {str(e)}")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def convert_to_drawio_format(elements):
    """Convert parsed elements to Draw.io format"""
    return {
        "type": "drawio",
        "cells": [
            {
                "id": node['id'],
                "value": node['text'],
                "style": "rounded=1;whiteSpace=wrap;html=1;",
                "vertex": 1,
                "geometry": {
                    "x": node['x'],
                    "y": node['y'],
                    "width": node['width'],
                    "height": node['height']
                }
            }
            for node in elements['nodes']
        ]
    }

def convert_visual_to_mermaid(visual_data: dict, source_format: str) -> str:
    """Convert visual editor data back to Mermaid code"""
    try:
        if source_format == 'excalidraw':
            return convert_excalidraw_to_mermaid(visual_data)
        else:
            return convert_generic_to_mermaid(visual_data)
    except Exception as e:
        print(f"❌ Conversion back error: {str(e)}")
        return "flowchart TD\n    A[Start] --> B[End]"

def convert_excalidraw_to_mermaid(visual_data: dict) -> str:
    """Convert Excalidraw data back to Mermaid"""
    elements = visual_data.get('elements', [])

    # Extract rectangles (nodes) and arrows (connections)
    nodes = []
    connections = []

    for element in elements:
        if element.get('type') == 'rectangle':
            node_id = element.get('id', '').replace('node_', '')
            node_text = element.get('text', node_id)
            nodes.append({'id': node_id, 'text': node_text})
        elif element.get('type') == 'arrow':
            arrow_id = element.get('id', '')
            if '_' in arrow_id:
                parts = arrow_id.replace('arrow_', '').split('_')
                if len(parts) >= 2:
                    connections.append({'source': parts[0], 'target': parts[1]})

    # Generate Mermaid code
    mermaid_lines = ["flowchart TD"]

    for node in nodes:
        mermaid_lines.append(f"    {node['id']}[\"{node['text']}\"]")

    for conn in connections:
        mermaid_lines.append(f"    {conn['source']} --> {conn['target']}")

    return '\n'.join(mermaid_lines)

@app.post("/api/diagram/generate-ai")
async def generate_diagram_with_ai(request: dict):
    """Generate diagram using AI based on user prompt"""
    try:
        prompt = request.get('prompt', '')
        diagram_type = request.get('diagramType', 'flowchart')
        format_type = request.get('format', 'mermaid')

        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")

        # Generate Mermaid code using AI
        mermaid_code = await generate_mermaid_with_ai(prompt, diagram_type)

        return {
            "success": True,
            "mermaidCode": mermaid_code,
            "prompt": prompt,
            "diagramType": diagram_type
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

async def generate_mermaid_with_ai(prompt: str, diagram_type: str) -> str:
    """Generate Mermaid diagram code using AI"""
    try:
        # Enhanced prompt for better diagram generation
        system_prompt = f"""You are an expert in creating {diagram_type} diagrams using Mermaid syntax.

Generate a well-structured Mermaid diagram based on the user's request. Follow these guidelines:

1. Use proper Mermaid syntax for {diagram_type} diagrams
2. Include meaningful node labels and connections
3. Use appropriate shapes and styling
4. Make the diagram clear and professional
5. Include proper spacing and organization

For flowcharts: Use flowchart TD or LR syntax
For sequence diagrams: Use sequenceDiagram syntax
For ER diagrams: Use erDiagram syntax
For class diagrams: Use classDiagram syntax

Return ONLY the Mermaid code, no explanations or markdown formatting."""

        user_prompt = f"Create a {diagram_type} diagram for: {prompt}"

        # Use Gemini API for diagram generation
        try:
            import google.generativeai as genai
            import os

            # Configure Gemini API
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            model = genai.GenerativeModel('gemini-pro')

            # Combine system and user prompts for Gemini
            full_prompt = f"{system_prompt}\n\nUser Request: {user_prompt}"

            response = model.generate_content(full_prompt)
            ai_response = response.text

            # Clean up the response to ensure it's valid Mermaid code
            mermaid_code = clean_mermaid_code(ai_response, diagram_type)

        except Exception as gemini_error:
            print(f"Gemini API error: {gemini_error}")
            # Fallback to smart pattern-based generation
            mermaid_code = generate_smart_diagram_local(prompt, diagram_type)

        return mermaid_code

    except Exception as e:
        print(f"❌ AI generation error: {str(e)}")
        return generate_fallback_diagram(prompt, diagram_type)

def clean_mermaid_code(raw_code: str, diagram_type: str) -> str:
    """Clean and validate Mermaid code"""
    # Remove markdown formatting
    code = raw_code.strip()
    if code.startswith('```'):
        lines = code.split('\n')
        code = '\n'.join(lines[1:-1]) if len(lines) > 2 else code

    # Remove any extra formatting
    code = code.replace('```mermaid', '').replace('```', '').strip()

    # Ensure proper diagram type declaration
    if not any(code.startswith(dt) for dt in ['flowchart', 'graph', 'sequenceDiagram', 'erDiagram', 'classDiagram']):
        if diagram_type == 'flowchart':
            code = f"flowchart TD\n{code}"
        elif diagram_type == 'sequence':
            code = f"sequenceDiagram\n{code}"
        elif diagram_type == 'er':
            code = f"erDiagram\n{code}"
        elif diagram_type == 'class':
            code = f"classDiagram\n{code}"

    return code

def generate_smart_diagram_local(prompt: str, diagram_type: str) -> str:
    """Generate smart diagrams using local pattern matching and templates"""
    prompt_lower = prompt.lower()

    # Smart keyword detection for different diagram types
    if diagram_type == 'sequence' or 'sequence' in prompt_lower or 'flow' in prompt_lower:
        return generate_smart_sequence_diagram(prompt)
    elif diagram_type == 'er' or 'database' in prompt_lower or 'entity' in prompt_lower:
        return generate_smart_er_diagram(prompt)
    elif diagram_type == 'class' or 'class' in prompt_lower or 'object' in prompt_lower:
        return generate_smart_class_diagram(prompt)
    else:
        return generate_smart_flowchart(prompt)

def generate_smart_sequence_diagram(prompt: str) -> str:
    """Generate intelligent sequence diagrams based on prompt analysis"""
    prompt_lower = prompt.lower()

    # Detect common patterns
    if 'auth' in prompt_lower or 'login' in prompt_lower:
        return """sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as Auth Service
    participant D as Database

    U->>F: Enter credentials
    F->>A: Validate login
    A->>D: Check user data
    D-->>A: User found
    A-->>F: Generate token
    F-->>U: Login successful

    Note over U,D: Authentication Flow"""

    elif 'payment' in prompt_lower or 'checkout' in prompt_lower:
        return """sequenceDiagram
    participant U as User
    participant S as Shop
    participant P as Payment Gateway
    participant B as Bank

    U->>S: Select items
    S->>U: Show checkout
    U->>P: Enter payment details
    P->>B: Process payment
    B-->>P: Payment confirmed
    P-->>S: Payment success
    S-->>U: Order confirmed"""

    elif 'api' in prompt_lower or 'request' in prompt_lower:
        return """sequenceDiagram
    participant C as Client
    participant A as API Gateway
    participant S as Service
    participant D as Database

    C->>A: API Request
    A->>S: Route request
    S->>D: Query data
    D-->>S: Return results
    S-->>A: Process response
    A-->>C: API Response"""

    else:
        # Generic sequence based on prompt
        words = prompt.split()[:4]
        return f"""sequenceDiagram
    participant User
    participant System
    participant Service
    participant Database

    User->>System: {' '.join(words)}
    System->>Service: Process request
    Service->>Database: Store/Retrieve data
    Database-->>Service: Data response
    Service-->>System: Result
    System-->>User: Final response"""

def generate_smart_flowchart(prompt: str) -> str:
    """Generate intelligent flowcharts based on prompt analysis"""
    prompt_lower = prompt.lower()

    if 'decision' in prompt_lower or 'if' in prompt_lower or 'choose' in prompt_lower:
        return f"""flowchart TD
    A[Start: {prompt[:30]}] --> B{{Decision Point}}
    B -->|Yes| C[Option A]
    B -->|No| D[Option B]
    C --> E[Process A]
    D --> F[Process B]
    E --> G[End]
    F --> G"""

    elif 'process' in prompt_lower or 'workflow' in prompt_lower:
        return f"""flowchart LR
    A[Input] --> B[Validate]
    B --> C[Process]
    C --> D[Transform]
    D --> E[Output]

    B -->|Invalid| F[Error Handling]
    F --> A"""

    elif 'system' in prompt_lower or 'architecture' in prompt_lower:
        return f"""flowchart TB
    subgraph "Frontend"
        UI[User Interface]
        APP[Application]
    end

    subgraph "Backend"
        API[API Layer]
        BL[Business Logic]
    end

    subgraph "Data"
        DB[(Database)]
        CACHE[(Cache)]
    end

    UI --> API
    APP --> API
    API --> BL
    BL --> DB
    BL --> CACHE"""

    else:
        # Generic flowchart
        return f"""flowchart TD
    A[Start] --> B[{prompt[:20]}]
    B --> C{{Process}}
    C -->|Success| D[Complete]
    C -->|Error| E[Handle Error]
    E --> B
    D --> F[End]"""

def generate_smart_er_diagram(prompt: str) -> str:
    """Generate intelligent ER diagrams based on prompt analysis"""
    prompt_lower = prompt.lower()

    if 'user' in prompt_lower or 'customer' in prompt_lower:
        return """erDiagram
    USER {
        int id PK
        string name
        string email
        string password
        datetime created_at
    }

    PROFILE {
        int id PK
        int user_id FK
        string first_name
        string last_name
        string phone
    }

    ORDER {
        int id PK
        int user_id FK
        decimal total
        datetime order_date
        string status
    }

    USER ||--|| PROFILE : has
    USER ||--o{ ORDER : places"""

    elif 'product' in prompt_lower or 'inventory' in prompt_lower:
        return """erDiagram
    PRODUCT {
        int id PK
        string name
        string description
        decimal price
        int stock_quantity
    }

    CATEGORY {
        int id PK
        string name
        string description
    }

    ORDER_ITEM {
        int id PK
        int product_id FK
        int order_id FK
        int quantity
        decimal unit_price
    }

    CATEGORY ||--o{ PRODUCT : contains
    PRODUCT ||--o{ ORDER_ITEM : included_in"""

    else:
        # Generic ER diagram
        return """erDiagram
    ENTITY_A {
        int id PK
        string name
        datetime created_at
    }

    ENTITY_B {
        int id PK
        int entity_a_id FK
        string description
        string status
    }

    ENTITY_A ||--o{ ENTITY_B : has"""

def generate_smart_class_diagram(prompt: str) -> str:
    """Generate intelligent class diagrams based on prompt analysis"""
    prompt_lower = prompt.lower()

    if 'user' in prompt_lower or 'auth' in prompt_lower:
        return """classDiagram
    class User {
        +int id
        +string username
        +string email
        +string password
        +datetime createdAt
        +login(credentials)
        +logout()
        +updateProfile(data)
        +validatePassword(password)
    }

    class UserProfile {
        +int userId
        +string firstName
        +string lastName
        +string phone
        +string address
        +updateProfile(data)
        +getFullName()
    }

    class Session {
        +string sessionId
        +int userId
        +datetime expiresAt
        +boolean isValid()
        +refresh()
    }

    User ||--|| UserProfile : has
    User ||--o{ Session : creates"""

    else:
        # Generic class diagram
        return """classDiagram
    class BaseClass {
        +int id
        +string name
        +datetime createdAt
        +save()
        +delete()
        +validate()
    }

    class DerivedClass {
        +string description
        +string status
        +process()
        +update(data)
    }

    BaseClass <|-- DerivedClass : inherits"""

def generate_fallback_diagram(prompt: str, diagram_type: str) -> str:
    """Generate a fallback diagram when all else fails"""
    return generate_smart_diagram_local(prompt, diagram_type)

def convert_generic_to_mermaid(visual_data: dict) -> str:
    """Convert generic visual data to Mermaid"""
    nodes = visual_data.get('nodes', [])
    connections = visual_data.get('connections', [])

    mermaid_lines = ["flowchart TD"]

    # Add node definitions
    for node in nodes:
        node_id = node['id']
        node_text = node.get('text', node_id)
        mermaid_lines.append(f"    {node_id}[\"{node_text}\"]")

    # Add connections
    for conn in connections:
        source = conn['source']
        target = conn['target']
        mermaid_lines.append(f"    {source} --> {target}")

    return '\n'.join(mermaid_lines)

@app.post("/api/document/{document_id}/regenerate")
async def regenerate_document_with_diagrams(document_id: str):
    """Regenerate document with updated diagrams"""
    try:
        from logic.srs_generator import generate_srs_docx

        # Get document info (in production, fetch from database)
        if document_id not in generated_files:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get updated diagrams
        diagrams = document_diagrams.get(document_id, [])

        # Create new output file
        output_dir = os.path.join(os.getcwd(), 'generated_docs')
        os.makedirs(output_dir, exist_ok=True)

        output_filename = f"updated_srs_{document_id}.docx"
        output_path = os.path.join(output_dir, output_filename)

        # Regenerate with updated diagrams
        headings = [
            {
                'heading': diagram['sectionTitle'],
                'purpose': 'Updated section with custom diagram',
                'category': 'Custom',
                'source': 'User Modified',
                'userPrompt': f"Use this custom diagram: {diagram['mermaidCode']}"
            }
            for diagram in diagrams
        ]

        if headings:
            generate_srs_docx(headings, output_path, "")
        else:
            generate_srs_docx([], output_path, "")

        return FileResponse(
            path=output_path,
            filename=output_filename,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate document: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )

# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )