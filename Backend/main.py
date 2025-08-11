from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import uuid
import os
import json
import re
from datetime import datetime
from typing import List, Dict, Any

# Load environment variables
from dotenv import load_dotenv
google_api_key = os.getenv("GOOGLE_API_KEY")
import os

# Try to load .env file, but don't fail if it doesn't exist
try:
    load_dotenv()
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")
    print("Continuing without .env file - using system environment variables")

# Import our models and utilities
from models.srs_model import *
from logic.heading_utils import load_standard_headings, get_all_headings, merge_headings
from logic.extractor import DocumentExtractor
from logic.extractor import get_gemini_srs_headings_from_transcript
from logic.vector_store import VectorStoreManager
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
extracted_text_content = {}  # Store extracted text content from PDFs
processing_status = {}  # Track processing status

# Initialize OpenAI client for vector store operations
from openai import OpenAI
import os
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Step 1: Store PDFs in OpenAI Vector Store ---
async def store_pdfs_in_vector_store(pdf_file_contents: dict):
    """Store PDFs in OpenAI Vector Store using responses API"""
    try:
        print("📤 Creating vector store...")
        vector_store = openai_client.vector_stores.create(name="srs_documents")
        
        print("📤 Uploading PDF files...")
        file_objects = []
        temp_paths = []
        
        for file_name, content in pdf_file_contents.items():
            try:
                # Create temporary file
                temp_path = f"temp_{file_name.replace(' ', '_').replace('/', '_')}"
                with open(temp_path, "wb") as f:
                    f.write(content)
                temp_paths.append(temp_path)
                
                # Open file for upload
                file_obj = open(temp_path, "rb")
                file_objects.append(file_obj)
                print(f"✅ Prepared {file_name} for upload")
                
            except Exception as e:
                print(f"❌ Failed to prepare {file_name}: {e}")
                continue
        
        if file_objects:
            print("📤 Uploading files to vector store...")
            # First upload files to OpenAI
            uploaded_file_ids = []
            for file_obj in file_objects:
                try:
                    uploaded_file = openai_client.files.create(file=file_obj, purpose="assistants")
                    uploaded_file_ids.append(uploaded_file.id)
                    print(f"✅ Uploaded file: {uploaded_file.id}")
                except Exception as e:
                    print(f"❌ Failed to upload file: {e}")
                    continue
            
            # Then add files to vector store using the correct API
            if uploaded_file_ids:
                for file_id in uploaded_file_ids:
                    try:
                        openai_client.vector_stores.files.create(
                            vector_store_id=vector_store.id,
                            file_id=file_id
                        )
                        print(f"✅ Added file {file_id} to vector store")
                    except Exception as e:
                        print(f"❌ Failed to add file {file_id} to vector store: {e}")
                        continue
                
                print(f"✅ Added {len(uploaded_file_ids)} files to vector store")
            else:
                print("❌ No files were successfully uploaded")
            
            # Clean up temporary files
            for temp_path in temp_paths:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except:
                    pass
            
            # Close file objects
            for file_obj in file_objects:
                try:
                    file_obj.close()
                except:
                    pass
            
            print(f"✅ Vector store created: {vector_store.id}")
            return vector_store.id
        else:
            print("❌ No files prepared for upload")
            return None
            
    except Exception as e:
        print(f"❌ Failed to store PDFs in vector store: {e}")
        return None

# --- Step 2: Extract TOC from stored content ---
async def extract_toc_from_vector_store(vector_store_id: str):
    """Extract TOC from stored content using OpenAI responses API"""
    try:
        print("🔍 Extracting TOC from vector store...")
        
        # Use the correct API structure for responses with vector stores
        response = openai_client.responses.create(
            model="gpt-4.1-nano",
            input="""Extract ALL headings and section titles from these documents. Look for:

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

Be thorough and extract as many headings as possible from the document structure.""",
            tools=[{
                "type": "file_search",
                "vector_store_ids": [vector_store_id]
            }]
        )
        
        toc_text = response.output_text
        print(f"✅ TOC extracted: {len(toc_text)} characters")
        print(f"📄 TOC preview: {toc_text[:500]}...")
        
        if not toc_text or len(toc_text.strip()) < 10:
            print("⚠️ Warning: Very short or empty TOC extracted")
            return {"toc": "No headings found in documents"}
        
        return {"toc": toc_text}
        
    except Exception as e:
        print(f"❌ Failed to extract TOC: {e}")
        return {"toc": ""}

# --- Step 3: Generate headings using OpenAI (replaces Gemini) ---
async def generate_headings_with_openai(toc_result: dict):
    """Generate headings using OpenAI based on TOC"""
    try:
        print("🤖 Generating headings with OpenAI...")
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
        if not os.getenv('OPENAI_API_KEY'):
            print("❌ No OpenAI API key found. Please set OPENAI_API_KEY environment variable.")
            print("🔧 Returning sample headings for testing...")
            sample_headings = {
                "Introduction": "Overview and purpose of the system",
                "Functional Requirements": "Core system functions and features",
                "Non-Functional Requirements": "Performance, security, and usability requirements",
                "System Architecture": "Technical design and component structure",
                "User Interface": "UI/UX specifications and wireframes"
            }
            print(f"🔧 Sample headings: {sample_headings}")
            return {"openai_headings": sample_headings}
        from openai import OpenAI
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are an expert software requirements analyst. Generate SRS headings in JSON format as described."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        openai_text = response.choices[0].message.content.strip()
        print(f"✅ OpenAI headings extracted: {len(openai_text)} characters")
        print(f"📄 OpenAI text preview: {openai_text[:500]}...")
        return {"openai_headings": openai_text}
    except Exception as e:
        print(f"❌ Failed to generate OpenAI headings: {e}")
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
        
        # Create SRS document using the existing generation logic
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
        
        generate_srs_docx(all_headings, output_path, uploaded_content)
        
        # Store file reference
        generated_files[file_id] = {
            'filename': output_filename,
            'path': output_path,
            'created_at': datetime.now().isoformat(),
            'headings_count': len(all_headings)
        }
        
        # Return the file for download
        return FileResponse(
            path=output_path,
            filename=output_filename,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate SRS document: {str(e)}"
        )

@app.post("/create-vector-store")
async def create_vector_store():
    """
    Create vector store from uploaded documents and extract TOC
    """
    global vector_store_manager
    
    try:
        # Get all uploaded documents
        if not uploaded_documents:
            raise HTTPException(
                status_code=400,
                detail="No documents uploaded. Please upload documents first."
            )
        
        # Create vector store manager
        vector_store_manager = VectorStoreManager()
        
        # Extract headings from all uploaded documents
        all_extracted_headings = []
        
        for doc_id, doc_info in uploaded_documents.items():
            if "binary_content" in doc_info and doc_info["binary_content"]:
                try:
                    # Determine file type
                    file_extension = doc_info["file_name"].lower().split('.')[-1]
                    if file_extension == 'pdf':
                        file_type = 'pdf'
                    elif file_extension in ['docx', 'doc']:
                        file_type = 'docx'
                    else:
                        file_type = 'txt'
                    
                    # Extract headings using DocumentExtractor
                    extracted_data = DocumentExtractor.extract_document_headings(
                        doc_info["binary_content"], 
                        file_type
                    )
                    
                    # Format headings
                    raw_headings = extracted_data.get('headings', [])
                    formatted_headings = DocumentExtractor.format_headings_for_api(
                        raw_headings, 
                        doc_info["file_name"]
                    )
                    
                    all_extracted_headings.extend(formatted_headings)
                    
                except Exception as e:
                    print(f"⚠️ Failed to extract headings from {doc_info['file_name']}: {e}")
        
        # Save uploaded PDF files temporarily and create vector store
        temp_pdf_paths = []
        
        for doc_id, doc_info in uploaded_documents.items():
            if "binary_content" in doc_info and doc_info["binary_content"]:
                # Save binary content to temporary file
                temp_file_path = f"temp_{doc_info['file_name']}"
                with open(temp_file_path, "wb") as f:
                    f.write(doc_info["binary_content"])
                temp_pdf_paths.append(temp_file_path)
        
        if temp_pdf_paths:
            # Create vector store from PDF files
            vector_store_manager = VectorStoreManager()
            
            # Upload PDF files to OpenAI
            uploaded_file_ids = vector_store_manager.upload_pdf_files(temp_pdf_paths)
            
            # Create vector store
            vector_store_id = vector_store_manager.create_vector_store(
                uploaded_file_ids, 
                "srs_documents_store"
            )
            
            # Extract and clean headings
            clean_headings = vector_store_manager.extract_and_clean_headings(
                vector_store_id, 
                "clean_extracted_headings.json"
            )
            
            # Clean up temporary files
            for temp_path in temp_pdf_paths:
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            return {
                "success": True,
                "message": f"Vector store created successfully with {len(clean_headings)} headings",
                "extracted_headings": clean_headings,
                "vector_store_id": vector_store_id
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="No valid PDF files found in uploaded documents."
            )
        
    except Exception as e:
        print(f"❌ Failed to create vector store: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create vector store: {str(e)}"
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
                # Step 1: Store PDFs in OpenAI Vector Store
                print("📤 Step 1: Storing PDFs in OpenAI Vector Store...")
                vector_store_id = await store_pdfs_in_vector_store(pdf_file_contents)
                
                if vector_store_id:
                    # Step 2: Extract TOC from stored content
                    print("🔍 Step 2: Extracting TOC from stored content...")
                    toc_result = await extract_toc_from_vector_store(vector_store_id)
                    
                    # Step 3: Generate headings using Gemini based on TOC
                    print("🤖 Step 3: Generating headings using Gemini...")
                    gemini_headings = await generate_headings_with_openai(toc_result)
                    
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
        
        # Step 1: Store PDFs in OpenAI Vector Store
        print("📤 Step 1: Storing PDFs in OpenAI Vector Store...")
        vector_store_id = await store_pdfs_in_vector_store(pdf_file_contents)
        
        if not vector_store_id:
            raise HTTPException(
                status_code=500,
                detail="Failed to create vector store"
            )
        
        # Step 2: Extract TOC from stored content
        print("🔍 Step 2: Extracting TOC from stored content...")
        toc_result = await extract_toc_from_vector_store(vector_store_id)
        
        if not toc_result or not toc_result.get('toc'):
            raise HTTPException(
                status_code=500,
                detail="Failed to extract TOC from vector store"
            )
        
        # Step 3: Generate headings using Gemini based on TOC
        print("🤖 Step 3: Generating headings using Gemini...")
        gemini_headings = await generate_headings_with_openai(toc_result)
        
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
            "vector_store_id": vector_store_id,
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
        # Generate headings using OpenAI with meeting transcript
        print(f"🔍 Calling generate_headings_with_openai with transcript length: {len(transcript_text)}")
        openai_headings = await generate_headings_with_openai({"toc": transcript_text})
        print(f"🔍 generate_headings_with_openai returned: {openai_headings}")
        if openai_headings and openai_headings.get('openai_headings'):
            raw_headings = openai_headings['openai_headings']
            print(f"🔍 Raw openai_headings type: {type(raw_headings)}")
            print(f"🔍 Raw openai_headings: {raw_headings}")
            # Handle both dictionary (fallback) and string (actual OpenAI response) cases
            if isinstance(raw_headings, dict):
                print("✅ Using fallback sample headings (no API key)")
                parsed_headings = raw_headings
            else:
                print("✅ Parsing actual OpenAI response")
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
                "message": "Failed to generate OpenAI headings"
            }
    except Exception as e:
        print(f"❌ Failed to generate OpenAI headings: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate OpenAI headings: {str(e)}"
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
        # In a real implementation, you'd use OpenAI with vector store
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
        
        # Step 1: Store PDFs in OpenAI Vector Store
        print("📤 Step 1: Storing PDFs in OpenAI Vector Store...")
        vector_store_id = await store_pdfs_in_vector_store(pdf_file_contents)
        
        if not vector_store_id:
            raise HTTPException(
                status_code=500,
                detail="Failed to create vector store"
            )
        
        # Step 2: Extract TOC from stored content
        print("🔍 Step 2: Extracting TOC from stored content...")
        toc_result = await extract_toc_from_vector_store(vector_store_id)
        
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
            "vector_store_id": vector_store_id,
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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )