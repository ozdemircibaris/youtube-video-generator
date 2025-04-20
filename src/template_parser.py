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
            
            # İyileştirilmiş bölüm görüntüleri ayrıştırma
            image_items = []
            
            # Her bölümü (section) için ayrı ayrı işle
            section_blocks = images_text.strip().split('\n- ')
            
            # İlk bloğu atla eğer boşsa
            if not section_blocks[0].strip():
                section_blocks = section_blocks[1:]
            else:
                # İlk bloktan '- ' önekini kaldır
                section_blocks[0] = section_blocks[0].lstrip('- ')
            
            for block in section_blocks:
                if not block.strip():
                    continue
                
                # Her satırı ayır
                lines = block.strip().split('\n')
                
                # Her satırdan anahtar-değer çiftlerini çıkar
                section_data = {}
                current_key = None
                
                for line in lines:
                    line = line.strip()
                    
                    # Satır "key: value" formatında mı kontrol et
                    if ': ' in line and not line.startswith('  '):
                        parts = line.split(': ', 1)
                        key = parts[0].strip()
                        value = parts[1].strip()
                        section_data[key] = value
                        current_key = key
                    elif current_key and line.startswith('  '):
                        # Önceki anahtara devam eden çok satırlı değer
                        section_data[current_key] += '\n' + line.strip()
                
                # En azından section adı varsa ekle
                if 'section' in section_data:
                    image_items.append(section_data)
            
            # Ayrıştırılan verileri kaydet
            template_data['images_scenario'] = image_items
            
            # Debug için yazdır
            print(f"Parsed {len(image_items)} section images from template")
            for item in image_items:
                print(f"  - Section: {item.get('section', 'unnamed')}")
        
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
        traceback.print_exc()
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