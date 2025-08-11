import json
import os
from typing import Dict, List, Optional, Any

def load_standard_headings(json_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads the standard SRS headings and purposes from the JSON file.
    
    Args:
        json_path: Optional path to the JSON file. If None, uses default path.
    
    Returns:
        dict: Nested dictionary of headings and purposes.
    
    Raises:
        FileNotFoundError: If the JSON file doesn't exist.
        json.JSONDecodeError: If the JSON file is malformed.
    """
    if json_path is None:
        # Default path relative to this file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base_dir, "data", "standard_headings.json")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Standard headings file not found at: {json_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in standard headings file: {e}")

def get_all_headings(headings_dict: Dict[str, Any], parent_key: str = "") -> List[Dict[str, str]]:
    """
    Flattens the nested headings dictionary into a list of heading objects.
    
    Args:
        headings_dict: The nested headings dictionary.
        parent_key: The parent heading key (for nested headings).
    
    Returns:
        List of dictionaries with 'heading' and 'purpose' keys.
    """
    flat_headings = []
    
    for key, value in headings_dict.items():
        if isinstance(value, dict):
            # If the value is a dict, it contains sub-headings
            if parent_key:
                current_heading = f"{parent_key} > {key}"
            else:
                current_heading = key
            
            # Add the main heading if it has a purpose (not just a container)
            if any(isinstance(v, str) for v in value.values()):
                flat_headings.append({
                    "heading": current_heading,
                    "purpose": value.get("purpose", f"Container for {key} related content")
                })
            
            # Recursively process sub-headings
            flat_headings.extend(get_all_headings(value, current_heading))
        else:
            # If the value is a string, it's a purpose
            if parent_key:
                current_heading = f"{parent_key} > {key}"
            else:
                current_heading = key
            
            flat_headings.append({
                "heading": current_heading,
                "purpose": value
            })
    
    return flat_headings

def get_heading_purpose(headings_dict: Dict[str, Any], heading_path: str) -> Optional[str]:
    """
    Gets the purpose of a specific heading by its path.
    
    Args:
        headings_dict: The nested headings dictionary.
        heading_path: The path to the heading (e.g., "Introduction > Document Purpose").
    
    Returns:
        The purpose string if found, None otherwise.
    """
    path_parts = heading_path.split(" > ")
    current_dict = headings_dict
    
    for part in path_parts:
        if part in current_dict:
            current_dict = current_dict[part]
        else:
            return None
    
    # If we reach here, we found the heading
    if isinstance(current_dict, str):
        return current_dict
    elif isinstance(current_dict, dict):
        # If it's a dict, it might have a "purpose" key or be a container
        return current_dict.get("purpose", f"Container for {path_parts[-1]} related content")
    
    return None

def merge_headings(standard_headings: Dict[str, Any], dynamic_headings: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Merges standard headings with dynamic headings, avoiding duplicates.
    
    Args:
        standard_headings: The standard headings dictionary.
        dynamic_headings: List of dynamic headings from analysis.
    
    Returns:
        Merged list of headings with duplicates removed.
    """
    # Get all standard headings as flat list
    standard_flat = get_all_headings(standard_headings)
    
    # Create a set of existing headings for quick lookup
    existing_headings = {item["heading"] for item in standard_flat}
    
    # Add dynamic headings that don't already exist
    merged = standard_flat.copy()
    for dynamic_heading in dynamic_headings:
        if dynamic_heading["heading"] not in existing_headings:
            merged.append(dynamic_heading)
            existing_headings.add(dynamic_heading["heading"])
    
    return merged

def validate_heading_structure(headings_dict: Dict[str, Any]) -> bool:
    """
    Validates that the headings dictionary has the correct structure.
    
    Args:
        headings_dict: The headings dictionary to validate.
    
    Returns:
        True if valid, False otherwise.
    """
    try:
        for key, value in headings_dict.items():
            if not isinstance(key, str):
                return False
            
            if isinstance(value, dict):
                # Recursively validate nested dictionaries
                if not validate_heading_structure(value):
                    return False
            elif isinstance(value, str):
                # String values are valid purposes
                continue
            else:
                # Invalid value type
                return False
        
        return True
    except Exception:
        return False

def export_headings_to_json(headings_list: List[Dict[str, str]], output_path: str) -> None:
    """
    Exports a list of headings to a JSON file.
    
    Args:
        headings_list: List of heading dictionaries.
        output_path: Path where to save the JSON file.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(headings_list, f, indent=2, ensure_ascii=False)

# Example usage and testing
if __name__ == "__main__":
    try:
        # Load standard headings
        standard_headings = load_standard_headings()
        print("✅ Standard headings loaded successfully!")
        
        # Validate structure
        if validate_heading_structure(standard_headings):
            print("✅ Heading structure is valid!")
        else:
            print("❌ Heading structure is invalid!")
        
        # Get all headings as flat list
        all_headings = get_all_headings(standard_headings)
        print(f"📋 Found {len(all_headings)} total headings")
        
        # Example: Get purpose of a specific heading
        purpose = get_heading_purpose(standard_headings, "Introduction > Document Purpose")
        print(f"📝 Purpose of 'Introduction > Document Purpose': {purpose}")
        
        # Example: Merge with some dynamic headings
        dynamic_headings = [
            {"heading": "Custom Section", "purpose": "A custom section added by user"},
            {"heading": "Introduction > Document Purpose", "purpose": "Updated purpose"}  # This should not be added as duplicate
        ]
        
        merged = merge_headings(standard_headings, dynamic_headings)
        print(f"🔄 After merging: {len(merged)} headings (added {len(merged) - len(all_headings)} new ones)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
