"""
Video generator module for creating videos with synchronized text.
"""

import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import math
import os
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
    
    def create_video(self, word_timings_path, audio_path, output_path):
        """
        Create a video with synchronized text based on word timings.
        
        Args:
            word_timings_path (str): Path to word timings JSON file
            audio_path (str): Path to audio file
            output_path (str): Path to save output video
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load word timings
            with open(word_timings_path, 'r') as f:
                word_timings = json.load(f)
            
            # Get audio duration
            audio_clip = AudioFileClip(audio_path)
            audio_duration = audio_clip.duration
            
            # Calculate total frames needed
            total_frames = math.ceil(audio_duration * self.fps)
            
            # Generate frames
            frames = self._generate_frames(word_timings, total_frames)
            
            # Create video clip from frames
            video_clip = ImageSequenceClip(frames, fps=self.fps)
            
            # Add audio to video
            video_with_audio = video_clip.set_audio(audio_clip)
            
            # Write video to file
            video_with_audio.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                fps=self.fps
            )
            
            print(f"Video created successfully at {output_path}")
            return True
            
        except Exception as e:
            print(f"Error creating video: {e}")
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
            
            if segment:
                words = segment['words']
                text = ' '.join([w['word'] for w in words])
                
                # Format text into lines
                text_lines = self._format_text_into_lines(text)
                
                # Create frame with formatted text and highlighted active word info
                frame = self._create_frame_with_text(text_lines, words, active_word_info)
            else:
                # Create empty frame if no segment is active
                frame = self._create_frame_with_text([], [], None)
                
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
    
    def _create_frame_with_text(self, text_lines, segment_words=None, active_word_info=None):
        """
        Create a frame with text and highlight the active word.
        
        Args:
            text_lines (list): List of text lines to display
            segment_words (list): List of word info dictionaries in the current segment
            active_word_info (dict): Info about currently active word (including timing)
            
        Returns:
            numpy.ndarray: Frame image
        """
        # Create a blank frame
        img = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(img)
        
        # If no text, return empty frame
        if not text_lines:
            frame = np.array(img)
            return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
        # Extract active word text if available
        active_word = active_word_info['word'] if active_word_info else None
        
        # Calculate line dimensions once
        line_heights = []
        
        for line in text_lines:
            # Get text dimensions
            bbox = self.font.getbbox(line)
            line_height = bbox[3]
            line_heights.append(line_height)
        
        # Calculate total text height with spacing
        line_spacing = 20  # Space between lines, increased for better readability
        total_text_height = sum(line_heights) + (len(text_lines) - 1) * line_spacing
        
        # Start position (center vertically)
        y_position = (self.height - total_text_height) // 2
        
        # Create a map to track which word instances should be highlighted
        word_positions_to_highlight = []
        if active_word_info and segment_words:
            # Find exact word instance to highlight - must match the exact word object from timing info
            for i, word_obj in enumerate(segment_words):
                if word_obj == active_word_info:
                    word_positions_to_highlight.append(i)
                    break
        
        # Flatten all words from text_lines to match against positions
        all_display_words = []
        for line in text_lines:
            all_display_words.extend(line.split())
        
        # Pre-calculate positions for all lines - this helps maintain stable layout
        positions = []
        word_index = 0  # Track overall word index
        
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
        
        # Now draw text using pre-calculated positions
        for line_y, word_positions in positions:
            for word_x, word, _, should_highlight in word_positions:
                # BGR vs RGB color handling
                # config.HIGHLIGHT_COLOR is already set as BGR (0, 255, 255) for yellow
                highlight_color_rgb = (config.HIGHLIGHT_COLOR[2], config.HIGHLIGHT_COLOR[1], config.HIGHLIGHT_COLOR[0])  # Convert BGR to RGB
                
                # Set colors based on whether word should be highlighted
                text_color = highlight_color_rgb if should_highlight else self.text_color
                
                # Draw word outline (same for all words to maintain consistent spacing)
                for offset in range(-self.text_outline_thickness, self.text_outline_thickness + 1):
                    draw.text((word_x + offset, line_y), word, font=self.font, fill=self.text_outline)
                    draw.text((word_x, line_y + offset), word, font=self.font, fill=self.text_outline)
                
                # Draw word with appropriate color
                draw.text((word_x, line_y), word, font=self.font, fill=text_color)
        
        # Convert PIL image to numpy array for OpenCV
        frame = np.array(img)
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # PIL uses RGB, OpenCV uses BGR