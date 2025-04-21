"""
Video generator module for creating videos with synchronized text.
"""

import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import math
import os
import traceback
from moviepy.editor import AudioFileClip, ImageSequenceClip

from src import config


class VideoGenerator:
    def __init__(self, language_code='en'):
        """
        Initialize the video generator.
        
        Args:
            language_code (str): Language code for font selection
        """
        self.width = config.VIDEO_WIDTH
        self.height = config.VIDEO_HEIGHT
        self.fps = config.VIDEO_FPS
        self.background_color = config.VIDEO_BACKGROUND_COLOR
        self.language_code = language_code
        
        # Bölüm görüntüleri için değişkenler
        self.section_images = {}
        self.section_start_times = {}
        self.section_end_times = {}
        
        # Setup text properties
        self.font_size = config.TEXT_FONT_SIZE
        self.text_color = config.TEXT_COLOR
        self.text_outline = config.TEXT_OUTLINE_COLOR
        self.text_outline_thickness = config.TEXT_OUTLINE_THICKNESS
        self.max_words_per_line = config.MAX_WORDS_PER_LINE
        self.max_lines = config.MAX_LINES
        
        # Load appropriate font for the language
        self._load_font()
    
    def _load_font(self):
        """Load the appropriate font for the current language."""
        try:
            # Get the font file name for the current language
            font_file = config.LANGUAGE_FONTS.get(self.language_code, config.DEFAULT_FONT)
            font_path = os.path.join(config.FONT_DIR, font_file)
            
            print(f"Attempting to load font for {self.language_code} from: {font_path}")
            
            # Check if font exists
            if not os.path.exists(font_path):
                print(f"Warning: Font file {font_path} not found. Using default font.")
                # Try to use system font
                try:
                    self.font = ImageFont.truetype("Arial", self.font_size)
                    print("Using system Arial font as fallback")
                    return
                except:
                    print("System Arial font not found. Using default PIL font.")
                    self.font = ImageFont.load_default()
                    return
            
            # Load the font
            try:
                self.font = ImageFont.truetype(font_path, self.font_size)
                print(f"Successfully loaded font: {font_path}")
            except Exception as e:
                print(f"Error loading font file {font_path}: {e}")
                print("Trying to use system font instead...")
                try:
                    self.font = ImageFont.truetype("Arial", self.font_size)
                    print("Using system Arial font as fallback")
                except:
                    print("System Arial font not found. Using default PIL font.")
                    self.font = ImageFont.load_default()
            
        except Exception as e:
            print(f"Error in font loading process: {e}")
            self.font = ImageFont.load_default()
            print("Using default PIL font as final fallback")
    
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
            
            # --------------------------------------------------------
            # IMPROVED APPROACH: Two-pass marker detection
            # --------------------------------------------------------
            
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
            
            # Clear previous timing data
            self.section_start_times = {}
            self.section_end_times = {}
            
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
            for section, timing in incomplete_markers.items():
                if 'start_time' in timing and 'end_time' not in timing:
                    # Has start but no end - use next section's start or end of audio
                    found_end = False
                    
                    # Find the next marker after this one
                    start_index = timing['start_index']
                    min_next_index = float('inf')
                    next_time = None
                    
                    for other_section, other_timing in markers.items():
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
                        # If no next section, use a reasonable duration (10 seconds)
                        self.section_start_times[section] = timing['start_time']
                        self.section_end_times[section] = timing['start_time'] + 10000
                        print(f"No next section found. Using default duration for section {section}: 10 seconds")
                
                elif 'end_time' in timing and 'start_time' not in timing:
                    # Has end but no start - use previous section's end or start of audio
                    found_start = False
                    
                    # Find the previous marker before this one
                    end_index = timing['end_index']
                    max_prev_index = -1
                    prev_time = None
                    
                    for other_section, other_timing in markers.items():
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
                        # If no previous section, use the beginning of the audio
                        self.section_start_times[section] = 0
                        self.section_end_times[section] = timing['end_time']
                        print(f"No previous section found. Using 0ms as start time for section {section}")
            
            # Check if sections from images have no markers at all
            for section_name in section_names:
                if section_name not in self.section_start_times:
                    print(f"Section {section_name} has an image but no timing markers in the SSML")
                    
                    # Try to find content related to this section name
                    related_indices = []
                    
                    for i, word_info in enumerate(word_timings):
                        if section_name.lower() in word_info.get('word', '').lower():
                            related_indices.append(i)
                    
                    if related_indices:
                        # Found mentions of this section name in the content
                        start_index = min(related_indices)
                        end_index = max(related_indices)
                        
                        # Get the start time of the first mention and end time of the last mention
                        start_time = word_timings[start_index]['start_time']
                        end_time = word_timings[end_index]['end_time']
                        
                        # Add a buffer to include context (2 seconds before and after)
                        start_time = max(0, start_time - 2000)
                        end_time = end_time + 2000
                        
                        self.section_start_times[section_name] = start_time
                        self.section_end_times[section_name] = end_time
                        
                        print(f"Inferred timing for section {section_name} based on content mentions: {start_time} to {end_time} ms")
            
            # Final fallback for any remaining sections with images but no timing
            remaining_sections = section_names - set(self.section_start_times.keys())
            if remaining_sections:
                print(f"Sections with no timing information: {remaining_sections}")
                
                # Get total duration from word timings
                if word_timings:
                    total_duration = word_timings[-1]['end_time']
                    
                    # Divide remaining duration evenly among these sections
                    section_count = len(remaining_sections)
                    if section_count > 0:
                        section_duration = total_duration / section_count
                        
                        # Assign time spans
                        for i, section_name in enumerate(sorted(remaining_sections)):
                            start_time = i * section_duration
                            end_time = (i + 1) * section_duration
                            
                            self.section_start_times[section_name] = start_time
                            self.section_end_times[section_name] = end_time
                            
                            print(f"Assigned fallback time span for section: {section_name} from {start_time} to {end_time} ms")
            
            # Summary of final section timings
            print("\nFinal section timing summary:")
            for section_name in sorted(self.section_start_times.keys()):
                start_time = self.section_start_times[section_name]
                end_time = self.section_end_times[section_name]
                duration_sec = (end_time - start_time) / 1000
                print(f"  - {section_name}: {start_time}ms to {end_time}ms (duration: {duration_sec:.2f} seconds)")
            
            # Now load the images based on section names
            for section_name in section_names:
                # Check for language-specific image first, then fallback to English version
                image_path = os.path.join(section_images_dir, f"{section_name}_{self.language_code}.jpg")
                
                if not os.path.exists(image_path):
                    # Try English version as fallback
                    image_path = os.path.join(section_images_dir, f"{section_name}_en.jpg")
                
                if os.path.exists(image_path):
                    try:
                        # Load image directly with PIL (avoids OpenCV color conversion issues)
                        pil_image = Image.open(image_path)
                        
                        # Resize if needed
                        if pil_image.width != self.width or pil_image.height != self.height:
                            pil_image = pil_image.resize((self.width, self.height), Image.LANCZOS)
                        
                        # Convert PIL image to numpy array (RGB format)
                        image = np.array(pil_image)
                        
                        self.section_images[section_name] = image
                        print(f"Loaded section image: {section_name} from {image_path} with shape {image.shape}")
                    except Exception as e:
                        print(f"Error loading section image {image_path}: {e}")
                else:
                    print(f"Section image not found: {image_path}")
            
            return len(self.section_images) > 0
            
        except Exception as e:
            print(f"Error loading section images: {e}")
            traceback.print_exc()
            return False

    def create_video(self, word_timings_path, audio_path, output_path, section_images_dir=None):
        """
        Create a video with synchronized text based on word timings.
        
        Args:
            word_timings_path (str): Path to word timings JSON file
            audio_path (str): Path to audio file
            output_path (str): Path to save output video
            section_images_dir (str): Directory containing section images
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load word timings
            if not os.path.exists(word_timings_path):
                print(f"Word timings file not found: {word_timings_path}")
                return False
                
            with open(word_timings_path, 'r') as f:
                word_timings = json.load(f)
            
            # Check if audio file exists
            if not os.path.exists(audio_path):
                print(f"Audio file not found: {audio_path}")
                return False
            
            # Get audio duration
            audio_clip = AudioFileClip(audio_path)
            audio_duration = audio_clip.duration
            
            # IMPORTANT: Check and verify section_images_dir
            if section_images_dir:
                # Ensure the directory exists
                if not os.path.exists(section_images_dir):
                    print(f"Creating section images directory: {section_images_dir}")
                    os.makedirs(section_images_dir, exist_ok=True)
                    
                # Check if the directory has any images
                image_files = [f for f in os.listdir(section_images_dir) 
                            if f.endswith(('.jpg', '.jpeg', '.png')) and os.path.isfile(os.path.join(section_images_dir, f))]
                
                if image_files:
                    print(f"Found {len(image_files)} image files in section images directory:")
                    for img in image_files[:5]:  # Show first 5 images
                        print(f"  - {img}")
                    if len(image_files) > 5:
                        print(f"  ... and {len(image_files) - 5} more")
                        
                    # Load section images
                    load_success = self.load_section_images(word_timings, section_images_dir)
                    if load_success:
                        print(f"Successfully loaded {len(self.section_images)} section images")
                    else:
                        print("Failed to load section images properly, but will continue with available images")
                else:
                    print(f"Warning: No image files found in section images directory: {section_images_dir}")
            else:
                print("No section images directory provided")
            
            # Calculate total frames needed
            total_frames = math.ceil(audio_duration * self.fps)
            
            # Generate frames
            frames = self._generate_frames(word_timings, total_frames)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create video clip from frames
            print(f"Creating video clip with {len(frames)} frames at {self.fps} FPS...")
            video_clip = ImageSequenceClip(frames, fps=self.fps)
            # video_clip = video_clip.set_fps(self.fps)
            
            # Add audio to video
            video_with_audio = video_clip.set_audio(audio_clip)
            
            # Write video to file
            print(f"Writing video to {output_path}...")
            video_with_audio.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                fps=self.fps,
                preset='medium',
                ffmpeg_params=["-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
            )
            
            print(f"Video created successfully at {output_path}")
            return True
            
        except Exception as e:
            print(f"Error creating video: {e}")
            traceback.print_exc()
            return False
    
    def _generate_frames(self, word_timings, total_frames):
        """
        Generate frames for the video.
        
        Args:
            word_timings (list): List of word timing information
            total_frames (int): Total number of frames to generate
            
        Returns:
            list: List of frame images
        """
        frames = []
        
        # Group words into sentences or logical segments
        segments = self._group_words_into_segments(word_timings)
        
        # Map frames to segments and active words based on timing
        frame_to_segment = {}
        frame_to_active_word_info = {}
        
        for frame_num in range(total_frames):
            time_ms = (frame_num / self.fps) * 1000  # Convert frame number to milliseconds
            
            # Find which segment should be displayed at this time
            current_segment = None
            for segment in segments:
                if segment['start_time'] <= time_ms <= segment['end_time']:
                    current_segment = segment
                    break
            
            # Find which word is active at this time (include full word info)
            active_word_info = None
            for word_info in word_timings:
                if word_info['start_time'] <= time_ms <= word_info['end_time']:
                    active_word_info = word_info
                    break
            
            if current_segment:
                frame_to_segment[frame_num] = current_segment
            else:
                frame_to_segment[frame_num] = None
                
            frame_to_active_word_info[frame_num] = active_word_info
        
        # Create actual frame images
        for frame_num in range(total_frames):
            segment = frame_to_segment.get(frame_num)
            active_word_info = frame_to_active_word_info.get(frame_num)
            
            # Calculate current time for section determination
            time_ms = (frame_num / self.fps) * 1000
            
            if segment:
                words = segment['words']
                text = ' '.join([w['word'] for w in words])
                
                # Format text into lines
                text_lines = self._format_text_into_lines(text)
                
                # Create frame with formatted text and highlighted active word info
                frame = self._create_frame_with_text(text_lines, words, active_word_info, time_ms)
            else:
                # Create empty frame (still with potential background image)
                frame = self._create_frame_with_text([], [], None, time_ms)
                
            frames.append(frame)
        
        return frames
    
    def _group_words_into_segments(self, word_timings):
        """
        Group words into logical segments for display.
        
        Args:
            word_timings (list): List of word timing information
            
        Returns:
            list: List of segments with start time, end time, and text
        """
        if not word_timings:
            return []
        
        segments = []
        current_segment = {
            'words': [],
            'start_time': word_timings[0]['start_time'],
            'end_time': None
        }
        
        # Track words in the current segment
        current_word_count = 0
        
        for word_info in word_timings:
            # Skip marker words
            word = word_info.get('word', '')
            if '_start' in word or '_end' in word:
                continue
                
            # Start a new segment if we've reached the max words per segment
            if current_word_count >= self.max_words_per_line * self.max_lines:
                # Finalize current segment
                if current_segment['words']:
                    last_word = current_segment['words'][-1]
                    current_segment['end_time'] = last_word['end_time']
                    segments.append(current_segment)
                
                # Start a new segment
                current_segment = {
                    'words': [word_info],
                    'start_time': word_info['start_time'],
                    'end_time': None
                }
                current_word_count = 1
            else:
                # Add to current segment
                current_segment['words'].append(word_info)
                current_word_count += 1
        
        # Add the last segment if it has any words
        if current_segment['words']:
            last_word = current_segment['words'][-1]
            current_segment['end_time'] = last_word['end_time']
            segments.append(current_segment)
        
        return segments
    
    def _format_text_into_lines(self, text):
        """
        Format text into lines with maximum words per line.
        
        Args:
            text (str): Text to format
            
        Returns:
            list: List of formatted text lines
        """
        if not text:
            return []
            
        words = text.split()
        lines = []
        
        # Format text into lines with max_words_per_line
        for i in range(0, len(words), self.max_words_per_line):
            line = ' '.join(words[i:i + self.max_words_per_line])
            lines.append(line)
        
        # Limit to max_lines
        return lines[:self.max_lines]
    
    def _create_frame_with_text(self, text_lines, segment_words=None, active_word_info=None, time_ms=None):
        """
        Create a frame with text and highlight the active word.
        
        Args:
            text_lines (list): List of text lines to display
            segment_words (list): List of word info dictionaries in the current segment
            active_word_info (dict): Info about currently active word (including timing)
            time_ms (float): Current time in milliseconds for section image selection
            
        Returns:
            numpy.ndarray: Frame image
        """
        # Determine which section image to use based on timing
        current_section_image = None
        active_section = None
        
        if time_ms is not None:
            # Check if we're in a section time range
            for section_name, start_time in self.section_start_times.items():
                end_time = self.section_end_times.get(section_name, float('inf'))
                
                if start_time <= time_ms <= end_time:
                    active_section = section_name
                    if section_name in self.section_images:
                        current_section_image = self.section_images[section_name]
                        # Sadece belirli aralıklarla yazdır (her saniyede bir)
                        if time_ms % 1000 < 30:
                            print(f"Using section image for {active_section} at time {time_ms} ms")
                        break
        
        # Create the frame with background image or color
        if current_section_image is not None:
            # Use section image as background
            img = Image.fromarray(current_section_image)
        else:
            # Use solid background color
            background_color_rgb = tuple(self.background_color)  # Make sure this is RGB
            img = Image.new('RGB', (self.width, self.height), background_color_rgb)
        
        draw = ImageDraw.Draw(img)
        
        # If no text, return the background frame
        if not text_lines:
            frame = np.array(img)
            return frame
            
        # Extract active word text if available
        active_word = active_word_info['word'] if active_word_info else None
        
        # Calculate line dimensions
        line_heights = []
        for line in text_lines:
            bbox = self.font.getbbox(line)
            line_height = bbox[3]
            line_heights.append(line_height)
        
        # Calculate total text height with spacing
        line_spacing = 20
        total_text_height = sum(line_heights) + (len(text_lines) - 1) * line_spacing
        
        # Start position (center vertically)
        y_position = (self.height - total_text_height) // 2
        
        # Add semi-transparent overlay for text readability if we have a background image
        if current_section_image is not None:
            # Convert image to RGBA for transparency support
            overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            # Calculate text area for overlay
            text_area_top = (self.height - total_text_height) // 2 - 40
            text_area_height = total_text_height + 80
            
            # Draw semi-transparent black rectangle
            overlay_draw.rectangle(
                [(0, text_area_top), (self.width, text_area_top + text_area_height)],
                fill=(0, 0, 0, 160)  # Black with 60% opacity
            )
            
            # Composite the overlay with the background image
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            draw = ImageDraw.Draw(img)
        
        # Find active word for highlighting
        word_positions_to_highlight = []
        if active_word_info and segment_words:
            # Find exact word instance to highlight
            for i, word_obj in enumerate(segment_words):
                if word_obj == active_word_info:
                    word_positions_to_highlight.append(i)
                    break
        
        # Pre-calculate positions for all lines
        all_display_words = []
        for line in text_lines:
            all_display_words.extend(line.split())
        
        # Calculate positions
        positions = []
        word_index = 0
        
        for i, line in enumerate(text_lines):
            line_bbox = self.font.getbbox(line)
            line_width = line_bbox[2]
            x_position = (self.width - line_width) // 2
            
            # Pre-calculate word positions in this line
            words = line.split()
            word_positions = []
            word_x = x_position
            
            for word in words:
                word_bbox = self.font.getbbox(word)
                word_width = word_bbox[2]
                
                # Determine if this specific instance should be highlighted
                should_highlight = word_index in word_positions_to_highlight
                
                word_positions.append((word_x, word, word_width, should_highlight))
                # Use a fixed space width for stability
                space_width = self.font.getbbox(" ")[2]
                word_x += word_width + space_width
                word_index += 1
            
            positions.append((y_position, word_positions))
            y_position += line_heights[i] + line_spacing
        
        # Draw text using pre-calculated positions
        highlight_color_rgb = (config.HIGHLIGHT_COLOR[2], config.HIGHLIGHT_COLOR[1], config.HIGHLIGHT_COLOR[0])
        
        for line_y, word_positions in positions:
            for word_x, word, _, should_highlight in word_positions:
                # Set colors based on whether word should be highlighted
                text_color = highlight_color_rgb if should_highlight else self.text_color
                
                # Draw word outline
                for offset in range(-self.text_outline_thickness, self.text_outline_thickness + 1):
                    draw.text((word_x + offset, line_y), word, font=self.font, fill=self.text_outline)
                    draw.text((word_x, line_y + offset), word, font=self.font, fill=self.text_outline)
                
                # Draw word with appropriate color
                draw.text((word_x, line_y), word, font=self.font, fill=text_color)
        
        # Convert PIL image to numpy array for OpenCV
        frame = np.array(img)
        return frame
        # return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # PIL uses RGB, OpenCV uses BGR