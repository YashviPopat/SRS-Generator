from openai import OpenAI
import os
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import re

class VectorStoreManager:
    """Manages OpenAI vector store operations for PDF storage and TOC extraction"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the vector store manager
        
        Args:
            api_key: OpenAI API key (if not provided, uses environment variable)
        """
        self.client = OpenAI(api_key=api_key)
        self.vector_store_id = None
        self.uploaded_file_ids = []
        
    def upload_pdf_files(self, pdf_paths: List[str]) -> List[str]:
        """
        Upload PDF files to OpenAI
        
        Args:
            pdf_paths: List of paths to PDF files
            
        Returns:
            List of uploaded file IDs
        """
        file_ids = []
        
        for path in pdf_paths:
            try:
                print(f"Uploading: {os.path.basename(path)}")
                
                # Check file size
                file_size = os.path.getsize(path)
                if file_size > 25 * 1024 * 1024:  # 25MB limit
                    print(f"⚠️ File {os.path.basename(path)} is too large ({file_size / 1024 / 1024:.1f}MB), skipping")
                    continue
                
                with open(path, "rb") as f:
                    uploaded = self.client.files.create(file=f, purpose="assistants")
                    file_ids.append(uploaded.id)
                    print(f"✅ Uploaded: {os.path.basename(path)} (ID: {uploaded.id})")
                    
            except Exception as e:
                print(f"❌ Failed to upload {path}: {str(e)}")
                continue
                
        self.uploaded_file_ids = file_ids
        return file_ids
    
    def create_vector_store(self, file_ids: List[str], store_name: str = "srs_store") -> str:
        """
        Create a vector store and add files to it
        
        Args:
            file_ids: List of file IDs to add to vector store
            store_name: Name for the vector store
            
        Returns:
            Vector store ID
        """
        try:
            print(f"Creating vector store: {store_name}")
            vs = self.client.vector_stores.create(name=store_name)
            self.vector_store_id = vs.id
            
            print(f"Adding {len(file_ids)} files to vector store...")
            for file_id in file_ids:
                try:
                    self.client.vector_stores.files.create(
                        vector_store_id=vs.id,
                        file_id=file_id
                    )
                    print(f"✅ Added file {file_id} to vector store")
                except Exception as e:
                    print(f"❌ Failed to add file {file_id} to vector store: {e}")
                    continue
            
            print(f"✅ Vector store created: {vs.id}")
            return vs.id
            
        except Exception as e:
            print(f"❌ Failed to create vector store: {str(e)}")
            raise
    
    def clean_heading_text(self, text: str) -> str:
        """
        Clean heading text by removing page numbers, dots, and extra whitespace
        """
        # Remove page numbers at the end (e.g., "................................ 86")
        text = re.sub(r'\s*\.{2,}\s*\d+\s*$', '', text)
        
        # Remove extra whitespace and dots
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove leading numbers and dots (e.g., "1.1. ", "13.13 ")
        text = re.sub(r'^\d+\.(?:\d+)*\s*', '', text)
        
        return text

    def generate_purpose_for_heading(self, heading_text: str) -> str:
        """
        Generate purpose for heading based on content
        """
        heading_lower = heading_text.lower()
        
        # Purpose mappings based on standard headings format
        purpose_mappings = {
            # Introduction section
            'introduction': 'Briefly describe the system and its main objectives',
            'document purpose': 'Purpose of the document itself',
            'project purpose': 'Why the project exists and its intended outcome',
            'project objectives': 'Goals the project aims to achieve',
            'project stakeholders': 'Key individuals or groups involved in or affected by the project',
            'assumptions': 'Conditions assumed to be true for the purpose of this document',
            'acronyms and abbreviations': 'Glossary of short forms used throughout the document',
            
            # Requirements section
            'requirements': 'Define the functional and non-functional requirements',
            'functional requirements': 'System-wide functional behaviors',
            'non-functional requirements': 'Performance, reliability, usability, etc',
            'system requirements': 'Technical system specifications',
            'user interface': 'Front-end behavior and layout',
            'database': 'Backend data handling specifications',
            'communication/security': 'Security protocols and communication standards',
            'system integration': 'Integration with external/internal systems',
            'constraints and limitation': 'Known system limitations',
            'legal': 'Legal and compliance requirements',
            'data protection and privacy': 'Data handling policies',
            
            # Architecture section
            'architecture': 'System architecture and component design',
            'system architecture': 'Top-level system architecture view',
            'overview': 'High-level system overview',
            'n-tier architecture': 'Multi-tier system design',
            'presentation component': 'User interface layer',
            'business logic component': 'Application logic layer',
            'data access component': 'Database access routines',
            'communication & security component': 'Handles secure communication',
            'api component': 'Exposes application interfaces',
            'microservices architecture': 'Microservices-based system design',
            'key benefits': 'Advantages of using microservices',
            'core microservices and their responsibilities': 'Individual service responsibilities',
            'communication and integration pattern': 'How services interact',
            'method of development': 'Development strategy or methodology',
            'high-level technical design': 'Technical overview and structure',
            
            # Implementation section
            'implementation': 'Implementation details and coding standards',
            'testing': 'Testing strategy and test cases',
            'deployment': 'Deployment procedures and configuration',
            'acceptance criteria': 'Conditions to meet for project sign-off',
            
            # Other sections
            'scope': 'Defines boundaries, limits, and coverage of the system',
            'hardware requirements': 'Minimum and recommended system specs',
            'product future': 'Possible improvements or additions',
            'open queries': 'Unresolved issues or pending decisions',
            
            # Canari-specific sections
            'call recording': 'Call recording and analysis features',
            'analytics': 'Data analysis and reporting capabilities',
            'campaigns': 'Marketing campaign management',
            'events': 'Event management and tracking',
            'billing': 'Billing and payment processing',
            'stripe integration': 'Payment gateway integration',
            'cms': 'Content management system',
            'infrastructure': 'System infrastructure requirements',
            
            # User personas
            'user personas': 'User types and their characteristics',
            'student': 'Student user requirements and expectations',
            'teacher': 'Teacher user requirements and expectations',
            'educator': 'Educator user requirements and expectations',
            'school leadership team': 'Leadership user requirements',
            'admissions & marketing officer': 'Admissions and marketing user requirements',
            'school inspector': 'Inspector user requirements',
            
            # Functional requirements
            'start new inspection': 'Initiate a new inspection workflow',
            'upload previous reports': 'Add historical data or documents',
            'generate report': 'Create reports using standards',
            'ask questions': 'Query insights from reports',
            'customize report': 'Change style/layout of reports',
            'export download report': 'Export generated reports',
            'reports library': 'Access and manage saved reports',
            
            # Curriculum and learning
            'curriculum content repository': 'Content storage and management',
            'curriculum design': 'Educational content design',
            'lesson plan generator': 'Automated lesson planning',
            'personalized learning': 'Individualized learning paths',
            'classroom scheduling': 'Schedule management',
            'resource allocation': 'Resource management',
            'student progress tracking': 'Progress monitoring',
            'content recommendation': 'Recommendation systems',
            'assessment evaluation': 'Assessment tools',
            'student learning assistant': 'AI learning support',
            'homework assignment support': 'Assignment assistance',
            'learning persona': 'Personalized learning profiles',
            'progress tracker': 'Progress monitoring tools',
            'student guardrails': 'Safety and moderation',
            'teacher control console': 'Teacher management interface',
            
            # Admissions and marketing
            'admissions process': 'Admission workflow management',
            'applicant profile evaluation': 'Profile assessment',
            'admissions insights': 'Admission analytics',
            'enquiry management': 'Inquiry handling',
            'marketing campaign': 'Campaign management',
            'campaign performance': 'Campaign analytics',
            'enrolment forecast': 'Enrollment predictions'
        }
        
        # Check for exact matches first
        for key, purpose in purpose_mappings.items():
            if key in heading_lower:
                return purpose
        
        # Check for partial matches
        for key, purpose in purpose_mappings.items():
            if any(word in heading_lower for word in key.split()):
                return purpose
        
        # Check for specific patterns
        if 'purpose' in heading_lower:
            return 'Purpose of this section'
        elif 'objective' in heading_lower:
            return 'Objectives and goals for this section'
        elif 'requirement' in heading_lower:
            return 'Requirements and specifications'
        elif 'design' in heading_lower:
            return 'Design and architecture details'
        elif 'implementation' in heading_lower:
            return 'Implementation approach and methodology'
        elif 'testing' in heading_lower:
            return 'Testing strategy and validation'
        elif 'integration' in heading_lower:
            return 'Integration with other systems and services'
        elif 'security' in heading_lower:
            return 'Security measures and protocols'
        elif 'performance' in heading_lower:
            return 'Performance requirements and optimization'
        elif 'scalability' in heading_lower:
            return 'Scalability considerations and strategies'
        
        # Default purpose
        return f"Describe the {heading_text.lower()} aspects of the system"

    def create_standard_format_headings(self, clean_headings: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Create headings in the standard format like clean_extracted_headings.json
        """
        # Organize headings into categories
        organized_headings = {
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
        
        for heading in clean_headings:
            heading_lower = heading.lower()
            purpose = self.generate_purpose_for_heading(heading)
            
            # Categorize headings
            if any(word in heading_lower for word in ['introduction', 'purpose', 'objective', 'stakeholder', 'assumption', 'acronym']):
                organized_headings["Introduction"][heading] = purpose
            elif any(word in heading_lower for word in ['user persona', 'student', 'teacher', 'educator', 'leadership', 'admission', 'inspector']):
                organized_headings["User Personas"][heading] = purpose
            elif any(word in heading_lower for word in ['scope', 'boundary', 'limit']):
                organized_headings["Scope"][heading] = purpose
            elif any(word in heading_lower for word in ['functional requirement', 'use case', 'start new', 'upload', 'generate', 'ask question', 'customize', 'export', 'library', 'curriculum', 'lesson', 'learning', 'student', 'teacher', 'admission', 'campaign']):
                organized_headings["Functional Requirements"][heading] = purpose
            elif any(word in heading_lower for word in ['non-functional', 'performance', 'scalability', 'reliability', 'usability', 'security', 'maintainability', 'compatibility']):
                organized_headings["Non-Functional Requirements"][heading] = purpose
            elif any(word in heading_lower for word in ['system requirement', 'user interface', 'database', 'communication', 'integration', 'constraint', 'legal']):
                organized_headings["System Requirements"][heading] = purpose
            elif any(word in heading_lower for word in ['architecture', 'overview', 'n-tier', 'microservice', 'component', 'design', 'technical']):
                organized_headings["System Architecture"][heading] = purpose
            elif any(word in heading_lower for word in ['implementation', 'development', 'coding']):
                organized_headings["Implementation"][heading] = purpose
            elif any(word in heading_lower for word in ['testing', 'test', 'validation']):
                organized_headings["Testing"][heading] = purpose
            elif any(word in heading_lower for word in ['deployment', 'delivery', 'release']):
                organized_headings["Deployment"][heading] = purpose
            else:
                organized_headings["Other"][heading] = purpose
        
        # Remove empty categories
        organized_headings = {k: v for k, v in organized_headings.items() if v}
        
        return organized_headings

    def extract_and_clean_headings(self, vector_store_id: str, output_file: str = "clean_extracted_headings.json") -> Dict[str, Dict[str, str]]:
        """
        Extract headings from vector store and save in clean_extracted_headings.json format
        
        Args:
            vector_store_id: ID of the vector store
            output_file: Path to save the cleaned headings
            
        Returns:
            Organized headings in standard format
        """
        try:
            print("🔍 Extracting and cleaning headings from vector store...")
            
            # Extract raw headings from vector store using comprehensive approach
            raw_headings = self.extract_table_of_contents_comprehensive(vector_store_id)
            
            if not raw_headings:
                print("⚠️ No headings extracted from vector store")
                return {}
            
            # Clean the headings
            clean_headings = []
            for item in raw_headings:
                heading_text = item.get('heading', '')
                if heading_text:
                    clean_heading = self.clean_heading_text(heading_text)
                    if clean_heading and len(clean_heading) > 3:
                        clean_headings.append(clean_heading)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_headings = []
            for heading in clean_headings:
                if heading.lower() not in seen:
                    seen.add(heading.lower())
                    unique_headings.append(heading)
            
            print(f"📋 Cleaned {len(unique_headings)} unique headings")
            
            # Create standard format
            organized_headings = self.create_standard_format_headings(unique_headings)
            
            # Save to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(organized_headings, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved organized headings to: {output_file}")
            
            # Display the organized headings
            print("\n📋 Organized Headings:")
            for category, headings in organized_headings.items():
                print(f"\n{category}:")
                for heading, purpose in headings.items():
                    print(f"  - {heading}: {purpose}")
            
            return organized_headings
            
        except Exception as e:
            print(f"❌ Failed to extract and clean headings: {str(e)}")
            return {}

    def extract_table_of_contents_comprehensive(self, vector_store_id: str) -> List[Dict[str, Any]]:
        """
        Comprehensive extraction of table of contents using multiple approaches
        
        Args:
            vector_store_id: ID of the vector store
            
        Returns:
            List of extracted headings with metadata
        """
        try:
            print("🔍 Comprehensive extraction of table of contents...")
            
            all_headings = []
            
            # Approach 1: Direct TOC extraction
            print("📋 Approach 1: Direct TOC extraction...")
            toc_headings = self._extract_toc_basic(vector_store_id)
            all_headings.extend(toc_headings)
            
            # Approach 2: Search for specific heading patterns
            print("📋 Approach 2: Pattern-based extraction...")
            pattern_headings = self._extract_headings_by_patterns(vector_store_id)
            all_headings.extend(pattern_headings)
            
            # Approach 3: Search for numbered sections
            print("📋 Approach 3: Numbered section extraction...")
            numbered_headings = self._extract_numbered_headings(vector_store_id)
            all_headings.extend(numbered_headings)
            
            # Approach 4: Search for document structure
            print("📋 Approach 4: Document structure extraction...")
            structure_headings = self._extract_document_structure(vector_store_id)
            all_headings.extend(structure_headings)
            
            # Approach 5: File-specific extraction
            print("📋 Approach 5: File-specific extraction...")
            file_specific_headings = self._extract_from_each_file(vector_store_id)
            all_headings.extend(file_specific_headings)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_headings = []
            for heading in all_headings:
                heading_text = heading.get('heading', '').strip()
                if heading_text and heading_text.lower() not in seen:
                    seen.add(heading_text.lower())
                    unique_headings.append(heading)
            
            print(f"✅ Comprehensive extraction completed: {len(unique_headings)} unique headings found")
            return unique_headings
            
        except Exception as e:
            print(f"❌ Failed comprehensive extraction: {str(e)}")
            return []

    def _extract_headings_by_patterns(self, vector_store_id: str) -> List[Dict[str, Any]]:
        """
        Extract headings by searching for specific patterns
        """
        try:
            pattern_prompt = """
            Search through the documents and find ALL headings that match these patterns:
            
            - Any text that starts with numbers followed by dots (1., 2., 3., 4., 5., 6., 7., 8., 9., 10., 11., 12., etc.)
            - Any text that starts with numbers and dots (1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, etc.)
            - Any text that starts with numbers and multiple dots (1.1.1, 1.1.2, 1.1.3, 1.2.1, 1.2.2, etc.)
            - Any text that appears to be a section title or heading
            - Any text that is in ALL CAPS or Title Case and appears to be a heading
            - Any text that is followed by page numbers or dots
            - Any text that looks like a chapter or section title
            - Any text that appears to be a main topic or subject heading
            
            Look for specific headings like:
            - Introduction, Document Purpose, Project Purpose, Project Objectives, Project Stakeholders
            - User Personas, Student, Teacher, Educator, School Leadership Team, Admissions & Marketing Officer, School Inspector
            - Scope, Functional Requirements, Non-Functional Requirements, System Requirements
            - User Interface, Database, Communication/Security, System Integration, Constraints and Limitation, Legal
            - System Architecture, Overview, AI Subsystems, N-tier Architecture, Microservices Architecture
            - Method of Development, High-Level Technical Design, Hardware Requirements, Acceptance Criteria
            - Product Future, Open Queries
            
            Return ONLY a JSON array of headings found. Each heading should be a JSON object with:
            - heading: the exact heading text
            - level: estimated heading level (1, 2, 3, or 4)
            - description: brief description
            - source: document name
            
            Be very thorough and find ALL headings you can locate. Do not miss any headings.
            """
            
            response = self.client.responses.create(
                model="gpt-4.1-nano",
                input=pattern_prompt,
                tools=[{
                    "type": "file_search",
                    "vector_store_ids": [vector_store_id]
                }]
            )
            
            try:
                response_text = response.output_text.strip()
                if response_text.startswith('[') and response_text.endswith(']'):
                    return json.loads(response_text)
                elif '[' in response_text and ']' in response_text:
                    start = response_text.find('[')
                    end = response_text.rfind(']') + 1
                    return json.loads(response_text[start:end])
            except:
                pass
            
            return []
            
        except Exception as e:
            print(f"⚠️ Pattern extraction failed: {e}")
            return []

    def _extract_numbered_headings(self, vector_store_id: str) -> List[Dict[str, Any]]:
        """
        Extract headings by searching for numbered sections specifically
        """
        try:
            numbered_prompt = """
            Find ALL numbered sections and headings in the documents. Look for:
            
            - Sections starting with "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.", etc.
            - Subsections like "1.1", "1.2", "1.3", "2.1", "2.2", etc.
            - Sub-subsections like "1.1.1", "1.1.2", "1.1.3", "1.2.1", "1.2.2", etc.
            - Sub-sub-subsections like "1.1.1.1", "1.1.1.2", "1.1.2.1", etc.
            - Any other numbered patterns
            
            Return ONLY a JSON array with each heading as an object containing:
            - heading: the exact heading text
            - level: heading level based on number of dots
            - description: what this section covers
            - source: document name
            
            Find EVERY numbered heading you can see.
            """
            
            response = self.client.responses.create(
                model="gpt-4.1-nano",
                input=numbered_prompt,
                tools=[{
                    "type": "file_search",
                    "vector_store_ids": [vector_store_id]
                }]
            )
            
            try:
                response_text = response.output_text.strip()
                if response_text.startswith('[') and response_text.endswith(']'):
                    return json.loads(response_text)
                elif '[' in response_text and ']' in response_text:
                    start = response_text.find('[')
                    end = response_text.rfind(']') + 1
                    return json.loads(response_text[start:end])
            except:
                pass
            
            return []
            
        except Exception as e:
            print(f"⚠️ Numbered extraction failed: {e}")
            return []

    def _extract_document_structure(self, vector_store_id: str) -> List[Dict[str, Any]]:
        """
        Extract headings by analyzing document structure
        """
        try:
            structure_prompt = """
            Analyze the document structure and find ALL section headings, titles, and topics.
            
            Look for:
            - Table of contents entries
            - Chapter titles and section titles
            - Any text that appears to be a heading or topic
            - Numbered and unnumbered sections
            - Main topics and subtopics
            - Any text that seems to organize the document content
            
            Search for these specific terms and variations:
            - Introduction, Purpose, Objectives, Stakeholders
            - User Personas, Users, Roles, Personas
            - Scope, Requirements, Functional, Non-Functional
            - System, Architecture, Design, Implementation
            - Testing, Deployment, Hardware, Acceptance
            - Future, Queries, Limitations, Constraints
            
            Return ONLY a JSON array with each heading as an object containing:
            - heading: the exact heading text
            - level: estimated heading level (1, 2, 3, or 4)
            - description: what this section covers
            - source: document name
            
            Find EVERY heading and topic you can identify in the document structure.
            """
            
            response = self.client.responses.create(
                model="gpt-4.1-nano",
                input=structure_prompt,
                tools=[{
                    "type": "file_search",
                    "vector_store_ids": [vector_store_id]
                }]
            )
            
            try:
                response_text = response.output_text.strip()
                if response_text.startswith('[') and response_text.endswith(']'):
                    return json.loads(response_text)
                elif '[' in response_text and ']' in response_text:
                    start = response_text.find('[')
                    end = response_text.rfind(']') + 1
                    return json.loads(response_text[start:end])
            except:
                pass
            
            return []
            
        except Exception as e:
            print(f"⚠️ Document structure extraction failed: {e}")
            return []

    def _extract_from_each_file(self, vector_store_id: str) -> List[Dict[str, Any]]:
        """
        Extract headings by searching each file individually
        """
        try:
            # Get list of files in the vector store
            file_prompt = """
            List all the PDF files that are available in this vector store. 
            For each file, provide the filename.
            
            Return ONLY a JSON array of filenames. Example:
            ["file1.pdf", "file2.pdf"]
            """
            
            response = self.client.responses.create(
                model="gpt-4.1-nano",
                input=file_prompt,
                tools=[{
                    "type": "file_search",
                    "vector_store_ids": [vector_store_id]
                }]
            )
            
            # Try to extract filenames from response
            filenames = []
            try:
                response_text = response.output_text.strip()
                if response_text.startswith('[') and response_text.endswith(']'):
                    filenames = json.loads(response_text)
                elif '[' in response_text and ']' in response_text:
                    start = response_text.find('[')
                    end = response_text.rfind(']') + 1
                    filenames = json.loads(response_text[start:end])
            except:
                # Fallback: use common filenames
                filenames = ["Canari Software Requirement Spec - v1.0.pdf", "MIS Consulting_SRS_v1.0.pdf"]
            
            print(f"📁 Found {len(filenames)} files: {filenames}")
            
            all_file_headings = []
            
            for filename in filenames:
                print(f"Extracting from file: {filename}")
                
                file_specific_prompt = f"""
                Extract ALL headings and section titles from the file: {filename}
                
                Look for:
                - Main sections (numbered like 1., 2., 3., 4., 5., 6., 7., 8., 9., 10., 11., 12., etc.)
                - Subsections (numbered like 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, etc.)
                - Sub-subsections (numbered like 1.1.1, 1.1.2, 1.1.3, 1.2.1, 1.2.2, etc.)
                - Any text that appears to be a heading, section title, or chapter title
                - Both numbered and unnumbered headings
                - Headings with or without page numbers
                
                IMPORTANT: Focus ONLY on the file "{filename}" and extract ALL headings from this specific file.
                
                Return ONLY a JSON array with each heading as an object containing:
                - heading: the exact heading text
                - level: heading level (1, 2, 3, or 4)
                - description: what this section covers
                - source: "{filename}"
                
                Be very thorough and find ALL headings in this specific file.
                """
                
                try:
                    file_response = self.client.responses.create(
                        model="gpt-4.1-nano",
                        input=file_specific_prompt,
                        tools=[{
                            "type": "file_search",
                            "vector_store_ids": [vector_store_id]
                        }]
                    )
                    
                    try:
                        response_text = file_response.output_text.strip()
                        if response_text.startswith('[') and response_text.endswith(']'):
                            file_headings = json.loads(response_text)
                        elif '[' in response_text and ']' in response_text:
                            start = response_text.find('[')
                            end = response_text.rfind(']') + 1
                            file_headings = json.loads(response_text[start:end])
                        else:
                            file_headings = []
                        
                        print(f"✅ Extracted {len(file_headings)} headings from {filename}")
                        all_file_headings.extend(file_headings)
                        
                    except json.JSONDecodeError:
                        print(f"⚠️ JSON parsing failed for {filename}")
                        
                except Exception as e:
                    print(f"⚠️ Failed to extract from {filename}: {e}")
            
            return all_file_headings
            
        except Exception as e:
            print(f"⚠️ File-specific extraction failed: {e}")
            return []

    def _extract_toc_basic(self, vector_store_id: str) -> List[Dict[str, Any]]:
        """
        Basic extraction of table of contents from documents in vector store
        
        Args:
            vector_store_id: ID of the vector store
            
        Returns:
            List of extracted headings with metadata
        """
        try:
            print("🔍 Extracting table of contents from vector store...")
            
            # More comprehensive prompt to extract TOC
            toc_prompt = """
            You are tasked with extracting ALL headings and section titles from the provided documents. This is a comprehensive extraction task.
            
            Please extract EVERY heading you can find, including:
            - Main sections (numbered like 1., 2., 3., 4., 5., 6., 7., 8., 9., 10., 11., 12., etc.)
            - Subsections (numbered like 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, etc.)
            - Sub-subsections (numbered like 1.1.1, 1.1.2, 1.1.3, 1.2.1, 1.2.2, etc.)
            - Sub-sub-subsections (numbered like 1.1.1.1, 1.1.1.2, 1.1.2.1, etc.)
            - Any text that appears to be a heading, section title, or chapter title
            - Both numbered and unnumbered headings
            - Headings with or without page numbers
            - Headings that might be in different formats or styles
            
            Look for patterns like:
            - "1. Introduction"
            - "1.1 Document Purpose"
            - "1.2 Project Purpose"
            - "1.3 Project Objectives"
            - "1.4 Project Stakeholders"
            - "2. User Personas"
            - "2.1 Student"
            - "2.2 Teacher / Educator"
            - "2.3 School Leadership Team"
            - "2.4 Admissions & Marketing Officer"
            - "2.5 School Inspector"
            - "3. Scope"
            - "4. Functional Requirements"
            - "4.1 General"
            - "4.2 Use Case 1: School Inspections"
            - "4.2.1 Start New Inspection"
            - "4.2.2 Upload Previous Reports / Evidence"
            - "4.2.3 Generate Report Based on KHDA Framework"
            - "4.2.4 Ask Questions About Generated Report"
            - "4.2.5 Customize Report Format"
            - "4.2.6 Export / Download Report"
            - "4.2.7 Reports Library"
            - "4.3 Use Case 2: Curriculum & Lesson Planning"
            - "4.3.1 Curriculum Content Repository"
            - "4.3.2 Curriculum Design & Lesson Plan Generator"
            - "4.3.3 Personalized Learning Pathways for Students"
            - "4.3.4 Collaboration & Resource Sharing for Educators"
            - "4.3.5 Classroom Scheduling & Resource Allocation"
            - "4.3.6 Student Progress Tracking & Analytics"
            - "4.3.7 Content Recommendation Engine"
            - "4.3.8 Assessment & Evaluation Tools"
            - "4.3.9 Audit & Version Control for Curriculum Changes"
            - "4.4 Use Case 3: Student Learning Assistant"
            - "4.4.1 Student Learning Assistant"
            - "4.4.2 Student Query Input & Recommendations"
            - "4.4.3 Homework & Assignment Support"
            - "4.4.4 Learning Persona & Goal Selector"
            - "4.4.5 Upload Classroom Materials for Context"
            - "4.4.6 Progress Tracker & Feedback Summary"
            - "4.4.7 Student Guardrails & Prompt Moderation"
            - "4.4.8 Teacher Control Console"
            - "4.5 Use Case 4: Admissions & Marketing"
            - "4.5.1 Admissions Process Assistant"
            - "4.5.2 Applicant Profile Evaluation"
            - "4.5.3 Admissions Insights Dashboard"
            - "4.5.4 Enquiry Management & Follow-Up Generator"
            - "4.5.5 Marketing Campaign Content Generator"
            - "4.5.6 Campaign Performance Insights"
            - "5. Non-Functional Requirements"
            - "6. System Requirements"
            - "6.1 User Interface"
            - "6.2 Database"
            - "6.3 Communication/Security"
            - "6.4 System Integration"
            - "6.5 Constraints and Limitation"
            - "6.6 Legal"
            - "7. System Architecture"
            - "7.1 Overview"
            - "7.2 AI Subsystems"
            - "7.3 N-tier Architecture"
            - "7.4 Microservices Architecture"
            - "7.5 Method of Development"
            - "7.6 High-Level Technical Design"
            - "8. Hardware Requirements"
            - "9. Acceptance Criteria"
            - "10. Product Future"
            - "11. Open Queries"
            - And any other headings you find
            
            For each heading found, create a JSON object with:
            - heading: the exact heading text as it appears in the document
            - level: heading level (1 for main sections, 2 for subsections, 3 for sub-subsections, 4 for sub-sub-subsections)
            - description: brief description of what this section likely covers
            - source: source document name
            
            IMPORTANT: Extract ALL headings you can find. Do not skip any. Be thorough and comprehensive. Look through the entire document content.
            
            Return ONLY a valid JSON array. Example format:
            [
                {
                    "heading": "1. Introduction",
                    "level": 1,
                    "description": "Project introduction and overview",
                    "source": "document_name.pdf"
                },
                {
                    "heading": "1.1 Document Purpose",
                    "level": 2,
                    "description": "Purpose and scope of the document",
                    "source": "document_name.pdf"
                },
                {
                    "heading": "1.2 Project Objectives",
                    "level": 2,
                    "description": "Goals and objectives of the project",
                    "source": "document_name.pdf"
                }
            ]
            
            Do not include any text before or after the JSON array. Return ONLY the JSON array.
            """
            
            # Query the vector store
            response = self.client.responses.create(
                model="gpt-4.1-nano",
                input=toc_prompt,
                tools=[{
                    "type": "file_search",
                    "vector_store_ids": [vector_store_id]
                }]
            )
            
            # Parse the response
            try:
                # Try to extract JSON from the response
                response_text = response.output_text.strip()
                
                # Look for JSON in the response
                if response_text.startswith('[') and response_text.endswith(']'):
                    toc_data = json.loads(response_text)
                elif '[' in response_text and ']' in response_text:
                    # Extract JSON part
                    start = response_text.find('[')
                    end = response_text.rfind(']') + 1
                    json_part = response_text[start:end]
                    toc_data = json.loads(json_part)
                else:
                    # Fallback: parse manually
                    toc_data = self._parse_toc_response(response_text)
                
                print(f"✅ Extracted {len(toc_data)} headings from vector store")
                return toc_data
                
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing failed, using fallback parser: {e}")
                return self._parse_toc_response(response.output_text)
                
        except Exception as e:
            print(f"❌ Failed to extract TOC: {str(e)}")
            return []
    
    def extract_table_of_contents(self, vector_store_id: str) -> List[Dict[str, Any]]:
        """
        Extract table of contents from documents in vector store (uses basic approach)
        
        Args:
            vector_store_id: ID of the vector store
            
        Returns:
            List of extracted headings with metadata
        """
        return self._extract_toc_basic(vector_store_id)
    
    def _parse_toc_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Fallback parser for TOC extraction when JSON parsing fails
        
        Args:
            response_text: Raw response text from OpenAI
            
        Returns:
            List of parsed headings
        """
        headings = []
        lines = response_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('```'):
                continue
                
            # Try to parse different formats
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    heading_text = parts[0].strip()
                    description = parts[1].strip()
                    
                    # Determine level based on formatting
                    level = 1
                    if heading_text.startswith('  '):
                        level = 2
                    elif heading_text.startswith('    '):
                        level = 3
                    
                    # Clean up heading text
                    heading_text = heading_text.strip()
                    
                    if heading_text and len(heading_text) > 2:
                        headings.append({
                            'heading': heading_text,
                            'level': level,
                            'description': description,
                            'source': 'Extracted from documents'
                        })
        
        return headings
    
    def search_documents(self, query: str, vector_store_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search documents in vector store
        
        Args:
            query: Search query
            vector_store_id: ID of the vector store
            max_results: Maximum number of results
            
        Returns:
            List of search results
        """
        try:
            response = self.client.responses.create(
                model="gpt-4.1-nano",
                input=query,
                tools=[{
                    "type": "file_search",
                    "vector_store_ids": [vector_store_id]
                }]
            )
            
            return [{
                'query': query,
                'response': response.output_text,
                'timestamp': datetime.now().isoformat()
            }]
            
        except Exception as e:
            print(f"Search failed: {str(e)}")
            return []
    
    def generate_content_for_heading(self, heading: str, vector_store_id: str, context: str = "") -> str:
        """
        Generate content for a specific heading using vector store
        
        Args:
            heading: The heading to generate content for
            vector_store_id: ID of the vector store
            context: Additional context for generation
            
        Returns:
            Generated content
        """
        try:
            prompt = f"""
            Generate comprehensive content for the following SRS section:
            
            Section: {heading}
            Context: {context}
            
            Please provide detailed, professional content that includes:
            1. Clear explanation of the section's purpose
            2. Detailed requirements or specifications
            3. Technical details where appropriate
            4. Examples or use cases if relevant
            5. Any constraints or considerations
            
            Use the information from the uploaded documents to ensure accuracy and relevance.
            Write in a professional, technical style suitable for a Software Requirements Specification document.
            """
            
            response = self.client.responses.create(
                model="gpt-4.1-nano",
                input=prompt,
                tools=[{
                    "type": "file_search",
                    "vector_store_ids": [vector_store_id]
                }]
            )
            
            return response.output_text
            
        except Exception as e:
            print(f"Content generation failed: {str(e)}")
            return f"Error generating content for {heading}: {str(e)}"
    
    def cleanup(self):
        """Clean up uploaded files and vector store"""
        try:
            # Delete uploaded files
            for file_id in self.uploaded_file_ids:
                try:
                    self.client.files.delete(file_id)
                    print(f" Deleted file: {file_id}")
                except Exception as e:
                    print(f"Failed to delete file {file_id}: {e}")
            
            # Delete vector store
            if self.vector_store_id:
                try:
                    self.client.vector_stores.delete(self.vector_store_id)
                    print(f"Deleted vector store: {self.vector_store_id}")
                except Exception as e:
                    print(f"Failed to delete vector store {self.vector_store_id}: {e}")
                    
        except Exception as e:
            print(f"Cleanup failed: {str(e)}")

# Utility functions for integration with your existing code
def create_vector_store_from_pdfs(pdf_folder_path: str, store_name: str = "srs_store") -> VectorStoreManager:
    """
    Create a vector store from PDF files in a folder
    
    Args:
        pdf_folder_path: Path to folder containing PDF files
        store_name: Name for the vector store
        
    Returns:
        VectorStoreManager instance
    """
    # Get PDF files
    pdf_files = []
    for file in os.listdir(pdf_folder_path):
        if file.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(pdf_folder_path, file))
    
    if not pdf_files:
        raise ValueError(f"No PDF files found in {pdf_folder_path}")
    
    print(f"📁 Found {len(pdf_files)} PDF files")
    
    # Create vector store manager
    vs_manager = VectorStoreManager()
    
    # Upload files
    file_ids = vs_manager.upload_pdf_files(pdf_files)
    
    # Create vector store
    vs_id = vs_manager.create_vector_store(file_ids, store_name)
    
    return vs_manager

def extract_toc_from_vector_store(vs_manager: VectorStoreManager) -> List[Dict[str, Any]]:
    """
    Extract table of contents from vector store
    
    Args:
        vs_manager: VectorStoreManager instance
        
    Returns:
        List of extracted headings
    """
    if not vs_manager.vector_store_id:
        raise ValueError("No vector store ID available")
    
    return vs_manager.extract_table_of_contents(vs_manager.vector_store_id) 

def extract_and_save_clean_headings(vs_manager: VectorStoreManager, output_file: str = "clean_extracted_headings.json") -> Dict[str, Dict[str, str]]:
    """
    Extract headings from vector store and save in clean_extracted_headings.json format
    
    Args:
        vs_manager: VectorStoreManager instance
        output_file: Path to save the cleaned headings
        
    Returns:
        Organized headings in standard format
    """
    if not vs_manager.vector_store_id:
        raise ValueError("No vector store ID available")
    
    return vs_manager.extract_and_clean_headings(vs_manager.vector_store_id, output_file)

def extract_comprehensive_headings(vs_manager: VectorStoreManager) -> List[Dict[str, Any]]:
    """
    Extract comprehensive headings from vector store using multiple approaches
    
    Args:
        vs_manager: VectorStoreManager instance
        
    Returns:
        List of all extracted headings
    """
    if not vs_manager.vector_store_id:
        raise ValueError("No vector store ID available")
    
    return vs_manager.extract_table_of_contents_comprehensive(vs_manager.vector_store_id) 