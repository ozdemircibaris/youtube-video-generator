"""
Manages section images and their timing information for video creation.
"""

import os
import re
import gc
import traceback
import numpy as np
from PIL import Image

class SectionManager:
    def __init__(self, language_code='en'):
        """
        Initialize the section manager.
        
        Args:
            language_code (str): Language code for image selection
        """
        self.language_code = language_code
        self.section_images = {}
        self.section_start_times = {}
        self.section_end_times = {}
        
    def clear_images(self):
        """Clear section images to free memory."""
        if hasattr(self, 'section_images'):
            self.section_images.clear()
        gc.collect()
        
    def load_section_images(self, word_timings, section_images_dir):
        """
        Load section images and map them to word timings based on markers.
        
        Args:
            word_timings (list): Word timing information
            section_images_dir (str): Directory containing section images
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # First, make sure the directory exists
            if not os.path.exists(section_images_dir):
                print(f"Creating section images directory: {section_images_dir}")
                os.makedirs(section_images_dir, exist_ok=True)
            
            print(f"Loading section images from: {section_images_dir}")
            
            # Clear any existing images first to prevent memory leaks
            self.clear_images()
                
            # Clear timing data to start fresh
            self.section_start_times = {}
            self.section_end_times = {}
            
            # Find all section names from images first
            section_names = set()
            for filename in os.listdir(section_images_dir):
                if filename.endswith('.jpg'):
                    # Extract section name from filename (e.g., "elephant_en.jpg" -> "elephant")
                    parts = filename.split('_')
                    if len(parts) > 0:
                        section_name = parts[0]
                        section_names.add(section_name)
            
            print(f"Found {len(section_names)} section names from images: {section_names}")
            
            # First pass: Find all marker words and their timing info
            print("First pass: Identifying all marker words...")
            markers = {}
            raw_markers = []
            
            for i, word_info in enumerate(word_timings):
                word = word_info.get('word', '')
                
                # Store raw marker words for debugging
                if '_start' in word or '_end' in word:
                    raw_markers.append(f"{word} at position {i}, time {word_info['start_time']}ms")
                
                # Check for start markers
                if '_start' in word:
                    # Extract section name by removing the _start suffix
                    marker_section = word.replace('__MARK_', '').replace('_start__', '').replace('_start', '')
                    
                    # Store information about this marker
                    if marker_section not in markers:
                        markers[marker_section] = {}
                    
                    markers[marker_section]['start_index'] = i
                    markers[marker_section]['start_time'] = word_info['start_time']
                    print(f"Found start marker for section: {marker_section} at {word_info['start_time']} ms")
                
                # Check for end markers
                elif '_end' in word:
                    # Extract section name by removing the _end suffix
                    marker_section = word.replace('__MARK_', '').replace('_end__', '').replace('_end', '')
                    
                    # Store information about this marker
                    if marker_section not in markers:
                        markers[marker_section] = {}
                    
                    markers[marker_section]['end_index'] = i
                    markers[marker_section]['end_time'] = word_info['end_time']
                    print(f"Found end marker for section: {marker_section} at {word_info['end_time']} ms")
            
            # Debug: Print all raw markers found
            print(f"Raw markers found: {len(raw_markers)}")
            for marker in raw_markers:
                print(f"  - {marker}")
                
            # Second pass: Process the markers and set section timing
            print("Second pass: Processing marker data...")
            
            # Process complete marker pairs first (sections with both start and end markers)
            complete_markers = {}
            incomplete_markers = {}
            
            for section, timing in markers.items():
                if 'start_time' in timing and 'end_time' in timing:
                    # Complete marker with both start and end
                    complete_markers[section] = timing
                    
                    # Store in our class dictionaries
                    self.section_start_times[section] = timing['start_time']
                    self.section_end_times[section] = timing['end_time']
                    
                    print(f"Complete timing for section: {section} from {timing['start_time']} to {timing['end_time']} ms")
                else:
                    # Incomplete marker with only start or end
                    incomplete_markers[section] = timing
                    print(f"Incomplete timing for section: {section} - has {'start' if 'start_time' in timing else 'end'} but no {'end' if 'start_time' in timing else 'start'}")
            
            # Handle incomplete markers - try to infer missing start/end times
            self._process_incomplete_markers(incomplete_markers, markers, word_timings)
            
            # Check if sections from images have no markers at all
            self._handle_sections_without_markers(section_names, word_timings)
            
            # Summary of final section timings
            print("\nFinal section timing summary:")
            for section_name in sorted(self.section_start_times.keys()):
                start_time = self.section_start_times[section_name]
                end_time = self.section_end_times[section_name]
                duration_sec = (end_time - start_time) / 1000
                print(f"  - {section_name}: {start_time}ms to {end_time}ms (duration: {duration_sec:.2f} seconds)")
            
            # Now load the images based on section names
            for section_name in section_names:
                self._load_section_image(section_name, section_images_dir)
            
            # Force garbage collection after loading all images
            gc.collect()
            
            return len(self.section_images) > 0
            
        except Exception as e:
            print(f"Error loading section images: {e}")
            traceback.print_exc()
            
            # Clean up in case of exception
            self.clear_images()
            
            return False
            
    def _process_incomplete_markers(self, incomplete_markers, all_markers, word_timings):
        """Process markers that have only start or end time."""
        for section, timing in incomplete_markers.items():
            if 'start_time' in timing and 'end_time' not in timing:
                # Has start but no end - use next section's start as end time
                found_end = False
                
                # Find the next marker after this one
                start_index = timing['start_index']
                min_next_index = float('inf')
                next_time = None
                
                for other_section, other_timing in all_markers.items():
                    if 'start_index' in other_timing and other_timing['start_index'] > start_index and other_timing['start_index'] < min_next_index:
                        min_next_index = other_timing['start_index']
                        next_time = other_timing['start_time']
                        found_end = True
                
                if found_end:
                    # Use the next section's start time as this section's end time
                    self.section_start_times[section] = timing['start_time']
                    self.section_end_times[section] = next_time
                    print(f"Inferred end time for section {section}: {next_time} ms (from next section)")
                else:
                    # If no next section is found, we don't use default duration anymore
                    print(f"WARNING: Section {section} has a start marker but no end marker or next section.")
                    print(f"This section will not be displayed as there's no way to determine its duration.")
                    # Remove from section_start_times if already added
                    if section in self.section_start_times:
                        del self.section_start_times[section]
            
            elif 'end_time' in timing and 'start_time' not in timing:
                # Has end but no start - use previous section's end as start time
                found_start = False
                
                # Find the previous marker before this one
                end_index = timing['end_index']
                max_prev_index = -1
                prev_time = None
                
                for other_section, other_timing in all_markers.items():
                    if 'end_index' in other_timing and other_timing['end_index'] < end_index and other_timing['end_index'] > max_prev_index:
                        max_prev_index = other_timing['end_index']
                        prev_time = other_timing['end_time']
                        found_start = True
                
                if found_start:
                    # Use the previous section's end time as this section's start time
                    self.section_start_times[section] = prev_time
                    self.section_end_times[section] = timing['end_time']
                    print(f"Inferred start time for section {section}: {prev_time} ms (from previous section)")
                else:
                    # If no previous section, we don't assume it starts at 0 anymore
                    print(f"WARNING: Section {section} has an end marker but no start marker or previous section.")
                    print(f"This section will not be displayed as there's no way to determine its start time.")
                    # Remove from section_end_times if already added
                    if section in self.section_end_times:
                        del self.section_end_times[section]
            
    def _handle_sections_without_markers(self, section_names, word_timings):
        """Handle sections that have images but no markers."""
        for section_name in section_names:
            if section_name not in self.section_start_times:
                print(f"WARNING: Section {section_name} has an image but no explicit timing markers in the SSML")
                print(f"This section will not be displayed as it requires both start and end markers in SSML content.")
                print(f"Example: <mark name=\"{section_name}_start\"/> and <mark name=\"{section_name}_end\"/>")
                
        # Final report for any remaining sections with images but no timing
        remaining_sections = section_names - set(self.section_start_times.keys())
        if remaining_sections:
            print(f"WARNING: The following sections have images but no valid timing markers and will NOT be displayed: {remaining_sections}")
            print("To fix this, add proper <mark> tags in your SSML content.")
            
    def _load_section_image(self, section_name, section_images_dir):
        """Load an image for a specific section."""
        # Check for language-specific image first, then fallback to English version
        image_path = os.path.join(section_images_dir, f"{section_name}_{self.language_code}.jpg")
        
        if not os.path.exists(image_path):
            # Try English version as fallback
            image_path = os.path.join(section_images_dir, f"{section_name}_en.jpg")
        
        if os.path.exists(image_path):
            try:
                # Load with PIL first (uses less memory and ensures proper color handling)
                pil_image = Image.open(image_path)
                
                # Check if resizing is needed to save memory
                target_width = 1600  # Reduced from 1920 to save memory
                if pil_image.width > target_width:
                    ratio = target_width / pil_image.width
                    target_height = int(pil_image.height * ratio)
                    pil_image = pil_image.resize((target_width, target_height), Image.LANCZOS)
                
                # Convert to numpy array in RGB format
                image = np.array(pil_image)
                
                # Store in our dictionary (keep in RGB format)
                self.section_images[section_name] = image
                
                # Close PIL image to release memory
                pil_image.close()
                
                print(f"Loaded section image: {section_name} from {image_path} with shape {image.shape}")
            except Exception as e:
                print(f"Error loading section image {image_path}: {e}")
        else:
            print(f"Section image not found: {image_path}") 