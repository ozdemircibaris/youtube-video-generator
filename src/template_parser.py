"""
Template parser for YouTube video generator.
This module reads and parses the template file.
"""

import re


def parse_template_file(file_path):
    """
    Parse the template file and extract sections.
    
    Args:
        file_path (str): Path to the template file
        
    Returns:
        dict: Dictionary containing all parsed sections
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Initialize dictionary to store all data
        template_data = {}
        
        # Extract metadata (lines starting with #)
        metadata_pattern = r'^#([a-zA-Z_]+):\s*(.+)$'
        metadata_matches = re.finditer(metadata_pattern, content, re.MULTILINE)
        
        for match in metadata_matches:
            key = match.group(1)
            value = match.group(2).strip()
            template_data[key] = value
        
        # Extract content section
        content_pattern = r'#content:(.*?)(?=^#|\Z)'
        content_match = re.search(content_pattern, content, re.DOTALL | re.MULTILINE)
        if content_match:
            template_data['content'] = content_match.group(1).strip()
        
        # Extract images_scenario
        images_scenario_pattern = r'#images_scenario:(.*?)(?=^#|\Z)'
        images_match = re.search(images_scenario_pattern, content, re.DOTALL | re.MULTILINE)
        if images_match:
            images_text = images_match.group(1)
            
            # Parse individual image scenarios
            image_items = []
            section_pattern = r'- section: (.+?)\n  prompt: (.+?)\n  description: (.+?)(?=\n-|\Z)'
            section_matches = re.finditer(section_pattern, images_text, re.DOTALL)
            
            for section_match in section_matches:
                section = section_match.group(1).strip()
                prompt = section_match.group(2).strip()
                description = section_match.group(3).strip()
                
                image_items.append({
                    'section': section,
                    'prompt': prompt,
                    'description': description
                })
            
            template_data['images_scenario'] = image_items
        
        # First check if ssml_content is directly provided in the template
        if 'ssml_content' in template_data:
            print(f"SSML content found directly in metadata: {template_data['ssml_content'][:50]}...")
            # Make sure it starts with <speak> tag
            if not template_data['ssml_content'].startswith('<speak>'):
                template_data['ssml_content'] = f"<speak>{template_data['ssml_content']}</speak>"
        else:
            # Extract SSML content from the content field
            ssml_pattern = r'(<speak>.*?</speak>)'
            ssml_match = re.search(ssml_pattern, template_data.get('content', ''), re.DOTALL)
            if ssml_match:
                template_data['ssml_content'] = ssml_match.group(1)
                print(f"SSML content found in content section: {template_data['ssml_content'][:50]}...")
            else:
                print("No SSML content found in template content. Content:", template_data.get('content', '')[:100])
                
                # As a fallback, look for partial SSML content
                speak_start = template_data.get('content', '').find('<speak>')
                if speak_start != -1:
                    # Try to extract everything from <speak> to the end
                    partial_ssml = template_data.get('content', '')[speak_start:]
                    # Add closing tag if missing
                    if '</speak>' not in partial_ssml:
                        partial_ssml += '</speak>'
                    template_data['ssml_content'] = partial_ssml
                    print(f"Partial SSML content found and fixed: {partial_ssml[:50]}...")
        
        return template_data
        
    except Exception as e:
        print(f"Error parsing template file: {e}")
        return None


def extract_plain_text(ssml_content):
    """
    Extract plain text from SSML content by removing tags.
    
    Args:
        ssml_content (str): SSML content
        
    Returns:
        str: Plain text without SSML tags
    """
    # Remove all XML tags
    plain_text = re.sub(r'<[^>]+>', '', ssml_content)
    return plain_text


def get_text_segments(ssml_content):
    """
    Break the SSML content into sentences and small segments.
    
    Args:
        ssml_content (str): SSML content
        
    Returns:
        list: List of text segments
    """
    # Remove SSML tags first
    plain_text = extract_plain_text(ssml_content)
    
    # Split by sentences (simple approach)
    sentences = re.split(r'(?<=[.!?])\s+', plain_text)
    
    # Further split long sentences
    segments = []
    for sentence in sentences:
        if len(sentence.split()) > 12:  # If sentence has more than 12 words
            # Split into smaller chunks, roughly by commas
            chunks = re.split(r'(?<=,)\s+', sentence)
            segments.extend(chunks)
        else:
            segments.append(sentence)
    
    return [segment.strip() for segment in segments if segment.strip()]


def extract_markers(ssml_content):
    """
    Extract mark tags and their positions from SSML content.
    
    Args:
        ssml_content (str): SSML content
        
    Returns:
        dict: Dictionary with marker names and their positions
    """
    markers = {}
    mark_pattern = r'<mark name="([^"]+)"/>'
    
    # Find all mark tags
    for match in re.finditer(mark_pattern, ssml_content):
        marker_name = match.group(1)
        position = match.start()
        markers[marker_name] = position
    
    return markers