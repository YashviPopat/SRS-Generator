from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class DocumentType(str, Enum):
    """Types of documents that can be processed"""
    SRS = "srs"
    REQUIREMENTS = "requirements"
    TECHNICAL_SPEC = "technical_spec"
    MEETING_TRANSCRIPT = "meeting_transcript"
    OTHER = "other"

class HeadingItem(BaseModel):
    """Individual heading with its purpose"""
    heading: str = Field(..., description="The heading text")
    purpose: str = Field(..., description="Purpose or description of this heading")
    is_standard: bool = Field(default=True, description="Whether this is a standard heading or custom")
    parent_heading: Optional[str] = Field(default=None, description="Parent heading if nested")

class DocumentUploadRequest(BaseModel):
    """Request model for uploading documents"""
    document_type: DocumentType = Field(..., description="Type of document being uploaded")
    file_name: str = Field(..., description="Name of the uploaded file")
    content: Optional[str] = Field(default=None, description="Document content if provided directly")
    url: Optional[str] = Field(default=None, description="URL to document if available")

class DocumentAnalysisResponse(BaseModel):
    """Response model for document analysis"""
    document_id: str = Field(..., description="Unique identifier for the uploaded document")
    extracted_headings: List[HeadingItem] = Field(..., description="Headings extracted from the document")
    document_type: DocumentType = Field(..., description="Type of document analyzed")
    analysis_status: str = Field(..., description="Status of the analysis (success, partial, failed)")
    gemini_suggestions: Optional[Dict[str, Any]] = Field(default=None, description="Gemini API suggested SRS headings and subheadings (nested, with purposes)")

class HeadingSuggestionRequest(BaseModel):
    """Request model for getting heading suggestions"""
    current_headings: List[HeadingItem] = Field(..., description="Current headings in the SRS")
    project_context: Optional[str] = Field(default=None, description="Project context or description")
    document_ids: Optional[List[str]] = Field(default=None, description="IDs of analyzed documents to consider")

class HeadingSuggestionResponse(BaseModel):
    """Response model for heading suggestions"""
    suggested_headings: List[HeadingItem] = Field(..., description="Suggested headings to add")
    missing_standard_headings: List[HeadingItem] = Field(..., description="Standard headings that are missing")
    reasoning: str = Field(..., description="Explanation for the suggestions")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in the suggestions")

class SRSStructureRequest(BaseModel):
    """Request model for building final SRS structure"""
    headings: List[HeadingItem] = Field(..., description="Final list of headings to include")
    project_title: str = Field(..., description="Title of the project")
    project_description: Optional[str] = Field(default=None, description="Brief project description")
    include_content_placeholders: bool = Field(default=True, description="Whether to include content placeholders")

class SRSStructureResponse(BaseModel):
    """Response model for SRS structure"""
    structure_id: str = Field(..., description="Unique identifier for the SRS structure")
    headings: List[HeadingItem] = Field(..., description="Final headings structure")
    total_sections: int = Field(..., description="Total number of sections")
    estimated_pages: int = Field(..., description="Estimated number of pages")

class DocxGenerationRequest(BaseModel):
    """Request model for generating DOCX file"""
    structure_id: str = Field(..., description="ID of the SRS structure to use")
    include_placeholders: bool = Field(default=True, description="Include content placeholders")
    custom_styling: Optional[Dict[str, Any]] = Field(default=None, description="Custom styling options")

class DocxGenerationResponse(BaseModel):
    """Response model for DOCX generation"""
    file_id: str = Field(..., description="Unique identifier for the generated file")
    file_name: str = Field(..., description="Name of the generated file")
    file_size: int = Field(..., description="Size of the file in bytes")
    download_url: str = Field(..., description="URL to download the generated file")
    generation_status: str = Field(..., description="Status of generation (success, processing, failed)")

class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code for programmatic handling")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")

class StandardHeadingsResponse(BaseModel):
    """Response model for getting standard headings"""
    headings: Dict[str, Any] = Field(..., description="Standard headings structure")
    total_count: int = Field(..., description="Total number of headings")
    categories: List[str] = Field(..., description="Main categories of headings")

class HeadingComparisonRequest(BaseModel):
    """Request model for comparing headings"""
    source_headings: List[HeadingItem] = Field(..., description="Source headings to compare")
    target_headings: List[HeadingItem] = Field(..., description="Target headings to compare against")
    comparison_type: str = Field(default="similarity", description="Type of comparison (similarity, differences, etc.)")

class HeadingComparisonResponse(BaseModel):
    """Response model for heading comparison"""
    similar_headings: List[Dict[str, Any]] = Field(..., description="Similar headings with similarity scores")
    unique_source_headings: List[HeadingItem] = Field(..., description="Headings unique to source")
    unique_target_headings: List[HeadingItem] = Field(..., description="Headings unique to target")
    overall_similarity: float = Field(..., ge=0.0, le=1.0, description="Overall similarity score")

# Utility functions for model conversion
def heading_dict_to_item(heading_dict: Dict[str, str]) -> HeadingItem:
    """Convert a heading dictionary to HeadingItem"""
    return HeadingItem(
        heading=heading_dict["heading"],
        purpose=heading_dict["purpose"],
        is_standard=True
    )

def heading_item_to_dict(heading_item: HeadingItem) -> Dict[str, str]:
    """Convert a HeadingItem to dictionary"""
    return {
        "heading": heading_item.heading,
        "purpose": heading_item.purpose
    } 