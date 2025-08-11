#!/usr/bin/env python3
"""
Clean extraction of headings from PDF table of contents
"""

import os
import sys
import json
import re
from pathlib import Path

def clean_heading_text(text):
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

def extract_clean_headings_from_text(text):
    """
    Extract clean headings from text content
    """
    headings = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Pattern 1: Numbered headings like "1. Introduction" or "1.1. Document Purpose"
        numbered_match = re.match(r'^(\d+\.(?:\d+)*)\s+(.+?)(?:\s*\.{2,}\s*\d+)?$', line)
        if numbered_match:
            heading_text = clean_heading_text(numbered_match.group(2))
            if heading_text and len(heading_text) > 3:
                headings.append(heading_text)
            continue
        
        # Pattern 2: Section headings like "Introduction" or "System Architecture"
        section_match = re.match(r'^([A-Z][A-Za-z\s&]+?)(?:\s*\.{2,}\s*\d+)?$', line)
        if section_match:
            heading_text = clean_heading_text(section_match.group(1))
            if (heading_text and len(heading_text) > 3 and 
                not re.match(r'^Page \d+', heading_text) and
                not re.match(r'^\d+$', heading_text)):
                headings.append(heading_text)
            continue
    
    # Remove duplicates while preserving order
    seen = set()
    unique_headings = []
    for heading in headings:
        if heading.lower() not in seen:
            seen.add(heading.lower())
            unique_headings.append(heading)
    
    return unique_headings

def generate_purpose_for_heading(heading_text):
    """
    Generate purpose for heading based on content
    """
    heading_lower = heading_text.lower()
    
    # Purpose mappings based on your standard headings format
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

def create_standard_format_headings(clean_headings):
    """
    Create headings in the standard format like standard_headings.json
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
        purpose = generate_purpose_for_heading(heading)
        
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

def main():
    """
    Main function to extract and format headings
    """
    print("🎯 Clean PDF Headings Extraction")
    print("=" * 40)
    
    # Sample headings from your PDF (you can replace this with actual PDF content)
    sample_headings = [
        "1. Introduction",
        "1.1. Document Purpose",
        "1.2. Project Purpose", 
        "1.3. Project Objectives",
        "1.4. Project Stakeholders",
        "2. User Personas",
        "2.1. Student",
        "2.2. Teacher / Educator",
        "2.3. School Leadership Team",
        "2.4. Admissions & Marketing Officer",
        "2.5. School Inspector",
        "3. Scope",
        "4. Functional Requirements",
        "4.1. General",
        "4.2. Use Case 1: School Inspections",
        "4.2.1. Start New Inspection",
        "4.2.2. Upload Previous Reports / Evidence",
        "4.2.3. Generate Report Based on KHDA Framework",
        "4.2.4. Ask Questions About Generated Report",
        "4.2.5. Customize Report Format",
        "4.2.6. Export / Download Report",
        "4.2.7. Reports Library",
        "4.3. Use Case 2: Curriculum & Lesson Planning",
        "4.3.1. Curriculum Content Repository",
        "4.3.2. Curriculum Design & Lesson Plan Generator",
        "4.3.3. Personalized Learning Pathways for Students",
        "4.3.4. Collaboration & Resource Sharing for Educators",
        "4.3.5. Classroom Scheduling & Resource Allocation",
        "4.3.6. Student Progress Tracking & Analytics",
        "4.3.7. Content Recommendation Engine",
        "4.3.8. Assessment & Evaluation Tools",
        "4.3.9. Audit & Version Control for Curriculum Changes",
        "4.4. Use Case 3: Student Learning Assistant",
        "4.4.1. Student Learning Assistant",
        "4.4.2. Student Query Input & Recommendations",
        "4.4.3. Homework & Assignment Support",
        "4.4.4. Learning Persona & Goal Selector",
        "4.4.5. Upload Classroom Materials for Context",
        "4.4.6. Progress Tracker & Feedback Summary",
        "4.4.7. Student Guardrails & Prompt Moderation",
        "4.4.8. Teacher Control Console",
        "4.5. Use Case 4: Admissions & Marketing",
        "4.5.1. Admissions Process Assistant",
        "4.5.2. Applicant Profile Evaluation",
        "4.5.3. Admissions Insights Dashboard",
        "4.5.4. Enquiry Management & Follow-Up Generator",
        "4.5.5. Marketing Campaign Content Generator",
        "4.5.6. Campaign Performance Insights",
        "5. Non-Functional Requirements",
        "6. System Requirements",
        "6.1. User Interface",
        "6.2. Database",
        "6.3. Communication/Security",
        "6.4. System Integration",
        "6.5. Constraints and Limitation",
        "6.6. Legal",
        "7. System Architecture",
        "7.1. Overview",
        "7.2. AI Subsystems",
        "7.3. N-tier Architecture",
        "7.4. Microservices Architecture",
        "7.5. Method of Development",
        "7.6. High-Level Technical Design",
        "8. Hardware Requirements",
        "9. Acceptance Criteria",
        "10. Product Future",
        "11. Open Queries"
    ]
    
    # Clean the headings
    clean_headings = []
    for heading in sample_headings:
        clean_heading = clean_heading_text(heading)
        if clean_heading and len(clean_heading) > 3:
            clean_headings.append(clean_heading)
    
    print(f"📋 Cleaned {len(clean_headings)} headings")
    
    # Create standard format
    organized_headings = create_standard_format_headings(clean_headings)
    
    # Save to file
    output_file = "clean_extracted_headings.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(organized_headings, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved organized headings to: {output_file}")
    
    # Display the organized headings
    print("\n📋 Organized Headings:")
    for category, headings in organized_headings.items():
        print(f"\n{category}:")
        for heading, purpose in headings.items():
            print(f"  - {heading}: {purpose}")
    
    print(f"\n✅ Extraction completed!")
    print(f"📁 Check the generated file: {output_file}")

if __name__ == "__main__":
    main() 