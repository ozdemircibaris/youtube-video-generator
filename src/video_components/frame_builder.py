"""
Frame builder for generating individual video frames with synchronized text.
"""

import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import math
import gc
import src.config as config

class FrameBuilder:
    def __init__(self, language_code='en', is_shorts=False, width=1920, height=1080, english_subtitles=False, english_word_timings=None):
        """
        Initialize the frame builder.
        
        Args:
            language_code (str): Language code for font selection
            is_shorts (bool): Whether generating frames for YouTube Shorts
            width (int): Frame width
            height (int): Frame height
            english_subtitles (bool): Whether to add English subtitles at the bottom
            english_word_timings (list): Word timings for English subtitles
        """
        self.language_code = language_code
        self.is_shorts = is_shorts
        self.width = width
        self.height = height
        self.english_subtitles = english_subtitles
        self.english_word_timings = english_word_timings
        
        # Setup text properties
        if is_shorts:
            self.font_size = int(config.TEXT_FONT_SIZE * 0.55)  # Daha küçük font
            self.subtitle_font_size = int(config.TEXT_FONT_SIZE * 0.38)  # Daha küçük subtitle font
        else:
            self.font_size = config.TEXT_FONT_SIZE
            self.subtitle_font_size = int(config.TEXT_FONT_SIZE * 0.8)
            
        self.text_color = config.TEXT_COLOR
        self.text_outline = config.TEXT_OUTLINE_COLOR
        self.text_outline_thickness = config.TEXT_OUTLINE_THICKNESS
        self.highlight_color = config.HIGHLIGHT_COLOR
        
        # Load fonts
        self._load_font()
        self._load_subtitle_font()
        
        self._last_subtitle_text = None
        self._last_subtitle_time = None
        self._last_subtitle_segment_words = None
        self._last_subtitle_active_word = None
        
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
            
    def _load_subtitle_font(self):
        """Load the font for English subtitles."""
        try:
            # Always use default font for English subtitles
            font_path = os.path.join(config.FONT_DIR, config.DEFAULT_FONT)
            
            print(f"Attempting to load subtitle font from: {font_path}")
            
            # Check if font exists
            if not os.path.exists(font_path):
                print(f"Warning: Subtitle font file {font_path} not found. Using default font.")
                # Try to use system font
                try:
                    self.subtitle_font = ImageFont.truetype("Arial", self.subtitle_font_size)
                    print("Using system Arial font for subtitles as fallback")
                    return
                except:
                    print("System Arial font not found. Using default PIL font for subtitles.")
                    self.subtitle_font = ImageFont.load_default()
                    return
            
            # Load the font
            try:
                self.subtitle_font = ImageFont.truetype(font_path, self.subtitle_font_size)
                print(f"Successfully loaded subtitle font: {font_path}")
            except Exception as e:
                print(f"Error loading subtitle font file {font_path}: {e}")
                print("Trying to use system font instead...")
                try:
                    self.subtitle_font = ImageFont.truetype("Arial", self.subtitle_font_size)
                    print("Using system Arial font for subtitles as fallback")
                except:
                    print("System Arial font not found. Using default PIL font for subtitles.")
                    self.subtitle_font = ImageFont.load_default()
            
        except Exception as e:
            print(f"Error in subtitle font loading process: {e}")
            self.subtitle_font = ImageFont.load_default()
            print("Using default PIL font for subtitles as final fallback")
            
    def generate_frames(self, segments, word_timings, total_frames, fps, 
                       temp_frames_dir, section_start_times, section_end_times, section_images):
        """
        Generate frames for the video.
        
        Args:
            segments (list): List of text segments
            word_timings (list): List of word timing information
            total_frames (int): Total number of frames to generate
            fps (int): Frames per second
            temp_frames_dir (str): Directory to save frames
            section_start_times (dict): Start times for each section
            section_end_times (dict): End times for each section
            section_images (dict): Images for each section
            
        Returns:
            list: List of frame paths
        """
        frames = []
        
        # MEMORY OPTIMIZATION: Process frames in batches
        batch_size = 500  # Process 500 frames at a time
            
        try:
            # Process all frames in batches
            for batch_start in range(0, total_frames, batch_size):
                batch_end = min(batch_start + batch_size, total_frames)
                print(f"Processing frames {batch_start} to {batch_end-1}")
                
                # Process this batch of frames
                for frame_num in range(batch_start, batch_end):
                    time_ms = (frame_num / fps) * 1000  # Convert frame number to milliseconds
                    
                    # Find which segment should be displayed at this time
                    current_segment = None
                    for segment in segments:
                        if segment['start_time'] <= time_ms <= segment['end_time']:
                            current_segment = segment
                            break
                    
                    # Find which word is active at this time
                    active_word_info = None
                    for word_info in word_timings:
                        if word_info['start_time'] <= time_ms <= word_info['end_time']:
                            active_word_info = word_info
                            break
                    
                    # Create the frame
                    if current_segment:
                        words = current_segment['words']
                        text = ' '.join([w['word'] for w in words])
                        
                        # Create frame with text and active word
                        frame = self._create_frame(
                            text, words, active_word_info, time_ms, 
                            section_start_times, section_end_times, section_images
                        )
                    else:
                        # Create empty frame (still with potential background image)
                        frame = self._create_frame(
                            "", [], None, time_ms, 
                            section_start_times, section_end_times, section_images
                        )
                    
                    # Save frame to disk and keep only path in memory
                    frame_path = os.path.join(temp_frames_dir, f"frame_{frame_num:06d}.jpg")
                    # Convert from RGB to BGR for OpenCV
                    cv2.imwrite(frame_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                    
                    # Add frame path to list
                    frames.append(frame_path)
                    
                    # Release the frame from memory
                    del frame
                
                # Garbage collect after each batch
                gc.collect()
                print(f"Completed batch {batch_start}-{batch_end-1}")
                
            print(f"Generated all {len(frames)} frames")
            return frames
            
        except Exception as e:
            print(f"Error generating frames: {e}")
            import traceback
            traceback.print_exc()
            return []
            
    def _create_frame(self, text, segment_words, active_word_info, time_ms, 
                      section_start_times, section_end_times, section_images):
        """
        Create a single frame with text and potentially highlighted word.
        
        Args:
            text (str): Text to display
            segment_words (list): Words in the current segment
            active_word_info (dict): Info about the currently active word
            time_ms (float): Current time in milliseconds
            section_start_times (dict): Start times for each section
            section_end_times (dict): End times for each section
            section_images (dict): Images for each section
            
        Returns:
            numpy.ndarray: Frame image
        """
        # Determine which section image to use based on timing
        current_section_image = None
        active_section = None
        
        if time_ms is not None:
            # Check if we're in a section time range - use strict timing
            for section_name, start_time in section_start_times.items():
                end_time = section_end_times.get(section_name, float('inf'))
                
                # Strict time range check to ensure accuracy
                if start_time <= time_ms <= end_time:
                    active_section = section_name
                    if section_name in section_images:
                        current_section_image = section_images[section_name]
                        # Log section usage less frequently to reduce noise
                        if time_ms % 5000 < 30:  # Only log every 5 seconds
                            print(f"Using section image '{active_section}' at time {time_ms} ms (from {start_time} to {end_time} ms)")
                        break
        
        # Create frame with background image or color
        frame = self._prepare_background(current_section_image)
        
        # If no text, return the background frame
        if not text:
            return np.array(frame)
        
        # Format text into lines for display
        text_formatter = TextFormatter(self.language_code, self.is_shorts)
        text_lines = text_formatter.format_text_into_lines(text)
        
        # Add text to frame
        frame_with_text = self._add_text_to_frame(
            frame, text_lines, segment_words, active_word_info
        )
        
        # Add English subtitles if enabled, but only if main text is present
        if self.english_subtitles and self.english_word_timings:
            # Segmentin zaman aralığına denk gelen İngilizce kelimeleri bul
            segment_start = segment_words[0]['start_time'] if segment_words else time_ms
            segment_end = segment_words[-1]['end_time'] if segment_words else time_ms
            english_text, english_segment_words, _ = self._find_english_text_for_segment(segment_start, segment_end)
            container_width = int(self.width * 0.8)
            if english_text:
                english_lines = self._wrap_text_to_width(english_text, self.subtitle_font, container_width - 40)
            else:
                english_lines = [""]
            frame_with_text = self._add_english_subtitles(
                frame_with_text, english_lines, english_segment_words, None
            )
        
        return np.array(frame_with_text)
        
    def _prepare_background(self, section_image=None):
        """
        Prepare the frame background using section image or solid color.
        
        Args:
            section_image (numpy.ndarray): Optional section image
            
        Returns:
            PIL.Image: Frame with background
        """
        if section_image is not None:
            try:
                # Use section image as background
                img = Image.fromarray(section_image)
                
                # For Shorts (vertical format), we need to resize/crop the background image appropriately
                if self.is_shorts:
                    # Get original dimensions
                    orig_width, orig_height = img.size
                    
                    # Create a black background
                    new_img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
                    
                    # For shorts, maintain original aspect ratio without cropping
                    # Scale the image to fit either the width or height, whichever is smaller
                    
                    # Calculate scaling factors
                    width_scale = self.width / orig_width
                    height_scale = self.height / orig_height
                    
                    # Use the smaller scaling factor to ensure image fits within frame
                    scale = min(width_scale, height_scale)
                    
                    # Calculate new dimensions
                    new_width = int(orig_width * scale)
                    new_height = int(orig_height * scale)
                    
                    # Resize image maintaining aspect ratio
                    resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                    
                    # Calculate position to center the image
                    x_position = (self.width - new_width) // 2
                    y_position = (self.height - new_height) // 2
                    
                    # Paste the resized image onto the black background
                    new_img.paste(resized_img, (x_position, y_position))
                    img = new_img
                else:
                    # Standard format: Also use cover mode for consistency
                    orig_width, orig_height = img.size
                    target_ratio = self.width / self.height
                    orig_ratio = orig_width / orig_height
                    
                    if orig_ratio > target_ratio:
                        # Image is wider than target, resize based on height
                        new_height = self.height
                        new_width = int(orig_ratio * new_height)
                        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                        
                        # Center crop the width
                        left = (new_width - self.width) // 2
                        img = resized_img.crop((left, 0, left + self.width, new_height))
                    else:
                        # Image is taller than target, resize based on width
                        new_width = self.width
                        new_height = int(new_width / orig_ratio)
                        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                        
                        # Center crop the height
                        top = (new_height - self.height) // 2
                        img = resized_img.crop((0, top, new_width, top + self.height))
                
                return img
            except Exception as e:
                print(f"Error using section image: {e}")
                # Fall back to solid color background
                return Image.new('RGB', (self.width, self.height), config.VIDEO_BACKGROUND_COLOR)
        else:
            # Use solid background color
            background_color_rgb = tuple(config.VIDEO_BACKGROUND_COLOR)  # Make sure this is RGB
            return Image.new('RGB', (self.width, self.height), background_color_rgb)
            
    def _add_text_to_frame(self, img, text_lines, segment_words, active_word_info):
        """
        Add text to the frame with highlighted active word.
        
        Args:
            img (PIL.Image): Background image
            text_lines (list): Lines of text to display
            segment_words (list): Words in the current segment
            active_word_info (dict): Info about the currently active word
            
        Returns:
            PIL.Image: Frame with text added
        """
        draw = ImageDraw.Draw(img)
        
        # Extract active word text if available
        active_word = active_word_info['word'] if active_word_info else None
        
        # Calculate line dimensions
        line_heights = []
        line_widths = []
        for line in text_lines:
            bbox = self.font.getbbox(line)
            line_height = bbox[3]
            line_width = bbox[2]
            line_heights.append(line_height)
            line_widths.append(line_width)
        
        # Calculate total text height with spacing
        line_spacing = 20
        total_text_height = sum(line_heights) + (len(text_lines) - 1) * line_spacing
        
        # Find the maximum width of all lines for overlay sizing
        max_line_width = max(line_widths) if line_widths else 0
        
        # For Shorts, position text in the lower third of the screen
        if self.is_shorts:
            y_position = int(self.height * 0.65) - (total_text_height // 2)
        else:
            # Standard format: center vertically
            y_position = (self.height - total_text_height) // 2
        
        # Add overlay just for the text area if we have a background image
        img_with_overlay = self._add_text_overlay(img, y_position, total_text_height, max_line_width)
        draw = ImageDraw.Draw(img_with_overlay)
        
        # Find active word for highlighting
        word_positions_to_highlight = []
        if active_word_info and segment_words:
            # Find exact word instance to highlight
            for i, word_obj in enumerate(segment_words):
                if word_obj == active_word_info:
                    word_positions_to_highlight.append(i)
                    break
        
        # Pre-calculate positions for all lines and words
        line_info = self._calculate_word_positions(text_lines, y_position, word_positions_to_highlight)
        
        # Draw text with highlighting
        self._draw_text_with_highlighting(draw, line_info)
        
        return img_with_overlay
        
    def _add_text_overlay(self, img, y_position, total_text_height, max_line_width):
        """Add semi-transparent overlay behind text for better readability."""
        # Convert image to RGBA for transparency support
        overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Calculate padding for text area
        horizontal_padding = 50  # pixels of padding on each side
        vertical_padding = 30  # pixels of padding on top and bottom
        
        # Calculate overlay rectangle coordinates
        text_area_left = (self.width - max_line_width) // 2 - horizontal_padding
        text_area_right = (self.width + max_line_width) // 2 + horizontal_padding
        text_area_top = y_position - vertical_padding
        text_area_bottom = y_position + total_text_height + vertical_padding
        
        # Border radius (corners)
        border_radius = 20
        
        # Draw rounded rectangle with semi-transparent black fill
        self._draw_rounded_rectangle(
            overlay_draw,
            [(text_area_left, text_area_top), (text_area_right, text_area_bottom)],
            border_radius,
            fill=(0, 0, 0, 160)  # Black with 60% opacity
        )
        
        # Composite the overlay with the background image
        return Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        
    def _calculate_word_positions(self, text_lines, y_start, highlight_indices):
        """Calculate positions of all words for rendering."""
        lines_info = []
        word_index = 0
        y_position = y_start
        line_spacing = 20
        
        for line in text_lines:
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
                should_highlight = word_index in highlight_indices
                
                word_positions.append((word_x, word, word_width, should_highlight))
                # Use a fixed space width for stability
                space_width = self.font.getbbox(" ")[2]
                word_x += word_width + space_width
                word_index += 1
            
            lines_info.append((y_position, word_positions))
            line_height = line_bbox[3]
            y_position += line_height + line_spacing
            
        return lines_info
        
    def _draw_text_with_highlighting(self, draw, lines_info):
        """Draw text with appropriate highlighting on active words."""
        highlight_color_rgb = (config.HIGHLIGHT_COLOR[2], config.HIGHLIGHT_COLOR[1], config.HIGHLIGHT_COLOR[0])
        
        for line_y, word_positions in lines_info:
            for word_x, word, _, should_highlight in word_positions:
                # Set colors based on whether word should be highlighted
                text_color = highlight_color_rgb if should_highlight else self.text_color
                
                # Draw word outline
                for offset in range(-self.text_outline_thickness, self.text_outline_thickness + 1):
                    draw.text((word_x + offset, line_y), word, font=self.font, fill=self.text_outline)
                    draw.text((word_x, line_y + offset), word, font=self.font, fill=self.text_outline)
                
                # Draw word with appropriate color
                draw.text((word_x, line_y), word, font=self.font, fill=text_color)
                
    def _draw_rounded_rectangle(self, draw, xy, radius, fill=None, outline=None, width=0):
        """
        Draw a rounded rectangle on the given ImageDraw object.
        
        Args:
            draw: ImageDraw object
            xy: Coordinates as [(x0, y0), (x1, y1)]
            radius: Border radius
            fill: Fill color
            outline: Outline color
            width: Outline width
        """
        x0, y0 = xy[0]
        x1, y1 = xy[1]
        
        # Make sure radius is not too large
        radius = min(radius, (x1 - x0) // 2, (y1 - y0) // 2)
        
        # Draw the rectangle without corners
        draw.rectangle([(x0, y0 + radius), (x1, y1 - radius)], fill=fill, outline=outline, width=width)
        draw.rectangle([(x0 + radius, y0), (x1 - radius, y1)], fill=fill, outline=outline, width=width)
        
        # Draw the four corner rounds
        draw.ellipse([(x0, y0), (x0 + 2 * radius, y0 + 2 * radius)], fill=fill, outline=outline, width=width)
        draw.ellipse([(x1 - 2 * radius, y0), (x1, y0 + 2 * radius)], fill=fill, outline=outline, width=width)
        draw.ellipse([(x0, y1 - 2 * radius), (x0 + 2 * radius, y1)], fill=fill, outline=outline, width=width)
        draw.ellipse([(x1 - 2 * radius, y1 - 2 * radius), (x1, y1)], fill=fill, outline=outline, width=width)

    def _find_english_text_for_segment(self, segment_start, segment_end):
        """
        Verilen segment zaman aralığına denk gelen İngilizce kelimeleri toplayıp, temiz subtitle metni döndürür.
        """
        if not self.english_word_timings:
            return None, [], None
        # Segment aralığına denk gelen İngilizce kelimeleri bul
        segment_words = [w for w in self.english_word_timings if w['start_time'] >= segment_start and w['end_time'] <= segment_end]
        # Marker kelimeleri atla
        words = []
        for word_info in segment_words:
            word = word_info['word']
            if '_start' in word or '_end' in word or '__MARK_' in word:
                continue
            words.append(word)
        if not words:
            return None, [], None
        # Metni birleştir ve SSML taglerini temizle
        import re
        text = ' '.join(words)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'__MARK_[^_]+__', '', text)
        text = ' '.join(text.split())
        if not text.strip():
            return None, [], None
        return text, segment_words, None

    def _add_english_subtitles(self, img, text_lines, segment_words, active_word_info):
        """
        Add English subtitles to the bottom of the frame.
        The subtitle container stays visible and stable.
        
        Args:
            img (PIL.Image): Image with main text already added
            text_lines (list): Lines of English subtitle text
            segment_words (list): Words in the current English segment
            active_word_info (dict): Info about the currently active English word
            
        Returns:
            PIL.Image: Frame with subtitles added
        """
        draw = ImageDraw.Draw(img)
        
        # Always use fixed height for the subtitle container
        # This ensures stability in the display
        container_height = 150  # Increased height for 2 subtitle lines
        
        # Calculate line dimensions
        line_heights = []
        line_widths = []
        
        if text_lines:
            for line in text_lines:
                bbox = self.subtitle_font.getbbox(line)
                line_height = bbox[3]
                line_width = bbox[2]
                line_heights.append(line_height)
                line_widths.append(line_width)
        else:
            # Use default dimensions for empty container
            bbox = self.subtitle_font.getbbox("Sample text")
            line_height = bbox[3]
            line_width = bbox[2]
            line_heights.append(line_height)
            line_widths.append(line_width)
        
        # Calculate total text height with spacing
        line_spacing = 20  # Slightly increased spacing for 2-line subtitles
        total_text_height = sum(line_heights) + (len(line_heights) - 1) * line_spacing
        
        # Calculate dynamic container width based on the max line width
        max_line_width = max(line_widths) if line_widths else 0
        horizontal_padding = 100  # Add padding around the text for better readability
        container_width = max_line_width + horizontal_padding
        
        # Ensure the container is not too narrow or too wide
        min_width = int(self.width * 0.4)  # Minimum width: 40% of video width
        max_width = int(self.width * 0.9)  # Maximum width: 90% of video width
        container_width = max(min_width, min(container_width, max_width))
        
        # Position subtitles at the bottom of the screen with fixed margin
        bottom_margin = 50  # Margin from bottom of screen
        y_position = self.height - container_height - bottom_margin
        
        # Always add overlay for the subtitle area with fixed dimensions
        img_with_overlay = self._add_subtitle_overlay(
            img, 
            y_position, 
            container_height,  # Use fixed height
            container_width,   # Use dynamic width
            is_fixed=True      # Indicate we're using fixed dimensions
        )
        draw = ImageDraw.Draw(img_with_overlay)
        
        # Only draw text if we have text lines
        if text_lines:
            # Find active word for highlighting
            word_positions_to_highlight = []
            if active_word_info and segment_words:
                # Find exact word instance to highlight
                for i, word_obj in enumerate(segment_words):
                    if word_obj == active_word_info:
                        word_positions_to_highlight.append(i)
                        break
        
            # Pre-calculate positions for all lines and words
            line_info = self._calculate_subtitle_positions(
                text_lines, 
                y_position + (container_height - total_text_height) // 2,  # Center text in container
                word_positions_to_highlight,
                container_width  # Pass dynamic width
            )
            
            # Draw text with highlighting
            self._draw_subtitles_with_highlighting(draw, line_info)
        
        return img_with_overlay

    def _add_subtitle_overlay(self, img, y_position, height, width, is_fixed=False):
        """
        Add semi-transparent overlay behind subtitles for better readability.
        Can use either fixed dimensions or calculated dimensions.
        
        Args:
            img (PIL.Image): Background image
            y_position (int): Y position for the overlay
            height (int): Height of the overlay
            width (int): Width of the overlay
            is_fixed (bool): Whether to use fixed dimensions
        
        Returns:
            PIL.Image: Frame with overlay added
        """
        # Convert image to RGBA for transparency support
        overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Calculate overlay rectangle coordinates
        if is_fixed:
            # Use fixed dimensions
            text_area_left = (self.width - width) // 2
            text_area_right = text_area_left + width
            text_area_top = y_position
            text_area_bottom = y_position + height
        else:
            # Use calculated dimensions with padding
            horizontal_padding = 50
            vertical_padding = 20
            text_area_left = (self.width - width) // 2 - horizontal_padding
            text_area_right = (self.width + width) // 2 + horizontal_padding
            text_area_top = y_position - vertical_padding
            text_area_bottom = y_position + height + vertical_padding
        
        # Border radius (corners)
        border_radius = 15
        
        # Draw rounded rectangle with semi-transparent black fill
        self._draw_rounded_rectangle(
            overlay_draw,
            [(text_area_left, text_area_top), (text_area_right, text_area_bottom)],
            border_radius,
            fill=(0, 0, 0, 180)  # Black with 70% opacity
        )
        
        # Composite the overlay with the background image
        return Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')

    def _calculate_subtitle_positions(self, text_lines, y_start, highlight_indices, container_width):
        """
        Calculate positions of all words for subtitle rendering.
        Uses fixed container width for stability.
        
        Args:
            text_lines (list): Lines of text
            y_start (int): Starting Y position
            highlight_indices (list): Indices of words to highlight
            container_width (int): Fixed width of the container
            
        Returns:
            list: Line information with word positions
        """
        lines_info = []
        word_index = 0
        y_position = y_start
        line_spacing = 20
        
        for line in text_lines:
            line_bbox = self.subtitle_font.getbbox(line)
            line_width = line_bbox[2]
            x_position = (self.width - container_width) // 2 + (container_width - line_width) // 2
            
            # Pre-calculate word positions in this line
            words = line.split()
            word_positions = []
            word_x = x_position
            
            for word in words:
                word_bbox = self.subtitle_font.getbbox(word)
                word_width = word_bbox[2]
                
                # Determine if this specific instance should be highlighted
                should_highlight = word_index in highlight_indices
                
                word_positions.append((word_x, word, word_width, should_highlight))
                # Use a fixed space width for stability
                space_width = self.subtitle_font.getbbox(" ")[2]
                word_x += word_width + space_width
                word_index += 1
            
            lines_info.append((y_position, word_positions))
            line_height = line_bbox[3]
            y_position += line_height + line_spacing
        
        return lines_info

    def _draw_subtitles_with_highlighting(self, draw, lines_info):
        """Draw subtitles with appropriate highlighting on active words."""
        highlight_color_rgb = (config.HIGHLIGHT_COLOR[2], config.HIGHLIGHT_COLOR[1], config.HIGHLIGHT_COLOR[0])
        
        for line_y, word_positions in lines_info:
            for word_x, word, _, should_highlight in word_positions:
                # Set colors based on whether word should be highlighted
                text_color = highlight_color_rgb if should_highlight else self.text_color
                
                # Draw word outline (thinner for subtitles)
                outline_thickness = max(1, self.text_outline_thickness - 1)
                for offset in range(-outline_thickness, outline_thickness + 1):
                    draw.text((word_x + offset, line_y), word, font=self.subtitle_font, fill=self.text_outline)
                    draw.text((word_x, line_y + offset), word, font=self.subtitle_font, fill=self.text_outline)
                
                # Draw word with appropriate color
                draw.text((word_x, line_y), word, font=self.subtitle_font, fill=text_color)

    def _wrap_text_to_width(self, text, font, max_width):
        """
        Metni, verilen font ve max_width'e göre satırlara böler.
        Always try to split into two lines when possible.
        """
        words = text.split()
        
        # If we have few words, just use a single line
        if len(words) <= 3:
            return [' '.join(words)]
            
        # Try to split into two roughly equal lines
        mid_point = len(words) // 2
        
        # Create two lines
        line1 = ' '.join(words[:mid_point])
        line2 = ' '.join(words[mid_point:])
        
        # Check if either line is too wide
        width1 = font.getbbox(line1)[2]
        width2 = font.getbbox(line2)[2]
        
        # If either line is too wide, use the original algorithm
        if width1 > max_width or width2 > max_width:
            lines = []
            current_line = ""
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                width = font.getbbox(test_line)[2]
                if width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            return lines
            
        # Return the two balanced lines
        return [line1, line2]


# Helper class dependency to avoid circular imports
class TextFormatter:
    def __init__(self, language_code='en', is_shorts=False):
        """Initialize with same parameters as in the main text formatter."""
        self.is_shorts = is_shorts
        
        # Set text properties based on video type
        if is_shorts:
            self.max_words_per_line = 3  # Fewer words per line for vertical format
        else:
            self.max_words_per_line = config.MAX_WORDS_PER_LINE
            
        self.max_lines = config.MAX_LINES
        
    def format_text_into_lines(self, text):
        """Format text into lines with maximum words per line."""
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