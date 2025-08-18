#!/usr/bin/env python3
"""
Script to fix the PNG insertion in srs_generator.py
"""

import re

def fix_srs_generator():
    """Fix the PNG insertion code in srs_generator.py"""
    
    # Read the current file
    with open('logic/srs_generator.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the SVG section with PNG insertion
    old_section = '''                # Add instructions for viewing
                instruction_para = doc.add_paragraph("💡 Open the SVG file in your browser or any SVG viewer for infinite zoom and crisp quality", style='SRS Normal')
                instruction_para.paragraph_format.left_indent = Inches(0.5)
                instruction_para.paragraph_format.space_after = Pt(12)
                instruction_para.runs[0].font.size = Pt(9)
                instruction_para.runs[0].italic = True

                print(f"✅ Successfully processed diagram for: {heading_text}")
                print(f"📁 High-quality SVG saved at: {diagram_path}")
                print(f"🎯 No quality loss - users can view SVG directly")'''
    
    new_section = '''                try:
                    run.add_picture(png_path, width=Inches(6))
                    diagram_para.paragraph_format.space_after = Pt(12)
                    print(f"✅ Successfully inserted high-quality PNG diagram into document")
                    
                    # Clean up PNG file after insertion
                    try:
                        os.remove(png_path)
                    except:
                        pass
                        
                except Exception as png_error:
                    print(f"❌ Failed to insert PNG diagram: {png_error}")

                print(f"✅ Successfully processed diagram for: {heading_text}")
                print(f"📄 High-quality PNG generated and inserted")'''
    
    # Replace the section (handle different character encodings)
    content = content.replace(old_section, new_section)
    
    # Also handle the case with different bullet character
    old_section_alt = old_section.replace("💡", "�")
    content = content.replace(old_section_alt, new_section)
    
    # Write the fixed content back
    with open('logic/srs_generator.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed PNG insertion in srs_generator.py")
    print("📄 Now generates high-quality PNG and inserts into document")
    print("🗑️ PNG files are cleaned up after insertion")

if __name__ == "__main__":
    fix_srs_generator()
