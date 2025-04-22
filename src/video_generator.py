"""
Video generator module for creating videos with synchronized text.
"""

import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import math
import os
import gc
import traceback
from moviepy.editor import AudioFileClip, ImageSequenceClip, VideoFileClip, concatenate_videoclips

from src import config


class VideoGenerator:
    def __init__(self, language_code='en', is_shorts=False):
        """
        Initialize the video generator.
        
        Args:
            language_code (str): Language code for font selection
            is_shorts (bool): Whether to generate a YouTube Shorts video
        """
        self.is_shorts = is_shorts
        
        if is_shorts:
            self.width = config.SHORTS_VIDEO_WIDTH
            self.height = config.SHORTS_VIDEO_HEIGHT
        else:
            self.width = config.VIDEO_WIDTH
            self.height = config.VIDEO_HEIGHT
            
        self.fps = config.VIDEO_FPS
        self.background_color = config.VIDEO_BACKGROUND_COLOR
        self.language_code = language_code
        
        # Bölüm görüntüleri için değişkenler
        self.section_images = {}
        self.section_start_times = {}
        self.section_end_times = {}
        
        # Setup text properties - adjust font size for Shorts if needed
        if is_shorts:
            self.font_size = int(config.TEXT_FONT_SIZE * 0.8)  # Slightly smaller for vertical format
            self.max_words_per_line = 3  # Fewer words per line for vertical format
        else:
            self.font_size = config.TEXT_FONT_SIZE
            self.max_words_per_line = config.MAX_WORDS_PER_LINE
            
        self.text_color = config.TEXT_COLOR
        self.text_outline = config.TEXT_OUTLINE_COLOR
        self.text_outline_thickness = config.TEXT_OUTLINE_THICKNESS
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
            
            # Clear any existing images first to prevent memory leaks
            if hasattr(self, 'section_images'):
                self.section_images.clear()
            else:
                self.section_images = {}
                
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
                        # Load image at a slightly reduced size for memory efficiency
                        # Use PIL to load and resize for consistent color handling
                        from PIL import Image
                        import numpy as np
                        
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
            
            # Force garbage collection after loading all images
            gc.collect()
            
            return len(self.section_images) > 0
            
        except Exception as e:
            print(f"Error loading section images: {e}")
            traceback.print_exc()
            
            # Clean up in case of exception
            if hasattr(self, 'section_images'):
                self.section_images.clear()
            
            # Force garbage collection
            gc.collect()
            
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
        # Disable MoviePy's temporary file management (handle it ourselves)
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix='youtube_generator_')
        print(f"Setting temporary directory to: {temp_dir}")
        
        print(f"Starting video creation for: {output_path}")
        
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
            
            # Initialize variables to ensure cleanup
            frames = []
            
            try:
                # Get audio duration using FFprobe directly
                import subprocess
                
                ffprobe_cmd = [
                    'ffprobe', 
                    '-v', 'error', 
                    '-show_entries', 'format=duration', 
                    '-of', 'default=noprint_wrappers=1:nokey=1', 
                    audio_path
                ]
                
                try:
                    # Get duration from ffprobe
                    result = subprocess.run(ffprobe_cmd, capture_output=True, text=True)
                    audio_duration = float(result.stdout.strip())
                    audio_duration_ms = audio_duration * 1000  # Convert to milliseconds
                    print(f"Audio duration: {audio_duration:.2f} seconds")
                except Exception as e:
                    print(f"Error getting audio duration: {e}")
                    # Fallback to estimating from word timings
                    audio_duration_ms = word_timings[-1]['end_time'] + 3000  # Add 3 seconds buffer
                    audio_duration = audio_duration_ms / 1000
                    print(f"Estimated audio duration from word timings: {audio_duration:.2f} seconds")
                
                # For Shorts, check if audio exceeds 1 minute (60 seconds)
                if self.is_shorts and audio_duration_ms > config.SHORTS_MAX_DURATION_MS:
                    print(f"Warning: Audio duration ({audio_duration:.2f}s) exceeds YouTube Shorts maximum of 60 seconds.")
                    print("Trimming audio to 60 seconds...")
                    
                    # Trim word timings to only include words within the first 60 seconds
                    trimmed_word_timings = []
                    for word_info in word_timings:
                        if word_info['start_time'] < config.SHORTS_MAX_DURATION_MS:
                            # If word ends after 60s, adjust end time to 60s
                            if word_info['end_time'] > config.SHORTS_MAX_DURATION_MS:
                                word_info['end_time'] = config.SHORTS_MAX_DURATION_MS
                            trimmed_word_timings.append(word_info)
                    
                    word_timings = trimmed_word_timings
                    audio_duration = 60.0
                    audio_duration_ms = 60000
                    print(f"Trimmed to {len(word_timings)} words within 60 second limit")
                
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
                
                # Generate frames for main content
                print(f"Generating {total_frames} frames...")
                frames, temp_frames_dir = self._generate_frames(word_timings, total_frames)
                
                # Clear section images after frame generation to reduce memory usage
                self.section_images.clear()
                gc.collect()
                
                print(f"Generated {len(frames)} frames, cleared section images from memory")
                
                # Ensure output directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # No need to save frames to temporary directory - they're already saved

                # Free frame memory - now just a list of paths
                frames_paths = frames.copy()
                frames.clear()
                gc.collect()
                print("Frame references cleared from memory")
                
                # Create a temporary output path
                temp_output = os.path.join(temp_dir, os.path.basename(output_path))
                
                # Try different approaches to create the video
                success = False
                
                # APPROACH 1: Direct FFMPEG approach using frame path pattern
                print("\nTrying direct FFMPEG approach...")
                try:
                    # Construct FFMPEG command for frame to video conversion
                    ffmpeg_frames_cmd = [
                        'ffmpeg',
                        '-y',  # Overwrite output file if it exists
                        '-r', str(self.fps),  # Frame rate
                        '-i', os.path.join(temp_frames_dir, "frame_%06d.jpg"),  # Input pattern
                        '-i', audio_path,  # Audio file
                        '-c:v', 'libx264',  # Video codec
                        '-preset', 'medium',  # Encoding speed/quality balance
                        '-crf', '23',  # Quality (lower is better)
                        '-color_trc', '1',  # BT.709 color transfer
                        '-colorspace', '1',  # BT.709 colorspace
                        '-color_primaries', '1',  # BT.709 color primaries
                        '-strict', 'experimental',  # Allow experimental codecs
                        '-c:a', 'aac',  # Audio codec
                        '-b:a', '192k',  # Audio bitrate
                        '-pix_fmt', 'yuv420p',  # Pixel format
                        '-shortest',  # End when shortest input stream ends
                        temp_output
                    ]
                    
                    print(f"Running FFMPEG command: {' '.join(ffmpeg_frames_cmd)}")
                    result = subprocess.run(ffmpeg_frames_cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print("FFMPEG video creation successful!")
                        success = True
                    else:
                        print(f"FFMPEG error: {result.stderr}")
                        print("FFMPEG approach failed, trying alternative method...")
                except Exception as e:
                    print(f"Error in FFMPEG approach: {e}")
                    print("Trying alternative method...")
                
                # APPROACH 2: OpenCV approach if FFMPEG failed
                if not success:
                    print("\nTrying OpenCV approach...")
                    try:
                        # Define the codec and create VideoWriter object
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        opencv_output = os.path.join(temp_dir, "opencv_output.mp4")
                        
                        out = cv2.VideoWriter(
                            opencv_output, 
                            fourcc, 
                            self.fps, 
                            (self.width, self.height)
                        )
                        
                        # Read frames back and write to video
                        for i in range(len(frames)):
                            frame_path = os.path.join(temp_frames_dir, f"frame_{i:06d}.jpg")
                            if os.path.exists(frame_path):
                                frame = cv2.imread(frame_path)
                                if frame is not None:
                                    out.write(frame)
                                
                                # Print progress every 1000 frames
                                if i % 1000 == 0:
                                    print(f"Processed {i}/{len(frames)} frames with OpenCV")
                        
                        # Release the VideoWriter
                        out.release()
                        
                        # Add audio to the video using FFMPEG
                        ffmpeg_audio_cmd = [
                            'ffmpeg',
                            '-y',
                            '-i', opencv_output,
                            '-i', audio_path,
                            '-c:v', 'copy',
                            '-c:a', 'aac',
                            '-shortest',
                            temp_output
                        ]
                        
                        print(f"Running FFMPEG audio merge command: {' '.join(ffmpeg_audio_cmd)}")
                        result = subprocess.run(ffmpeg_audio_cmd, capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            print("OpenCV + FFMPEG audio merge successful!")
                            success = True
                        else:
                            print(f"FFMPEG audio merge error: {result.stderr}")
                    except Exception as e:
                        print(f"Error in OpenCV approach: {e}")
                        
                # If either approach was successful, copy to final destination
                if success and os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
                    import shutil
                    shutil.copy2(temp_output, output_path)
                    print(f"Video created successfully at {output_path}")
                    return True
                else:
                    print(f"Both video creation approaches failed")
                    return False
                
            finally:
                # Ensure proper resource cleanup even if an exception occurs
                print("Cleaning up video generation resources...")
                
                # Clear all lists
                if frames:
                    frames.clear()
                
                # Clear section images to free memory
                if hasattr(self, 'section_images'):
                    self.section_images.clear()
                
                # Force garbage collection multiple times
                print("Running deep garbage collection...")
                for _ in range(3):
                    gc.collect()
                
                print("Video generation resources cleaned up")
            
            # Final cleanup - remove temporary frames directory
            if temp_frames_dir and os.path.exists(temp_frames_dir):
                import shutil
                try:
                    shutil.rmtree(temp_frames_dir)
                    print(f"Removed temporary frames directory: {temp_frames_dir}")
                except Exception as e:
                    print(f"Warning: Could not remove temporary frames directory: {e}")
            
            return success
            
        except Exception as e:
            print(f"Error creating video: {e}")
            traceback.print_exc()
            
            # Clean up temporary frames directory if it exists
            if 'temp_frames_dir' in locals() and temp_frames_dir and os.path.exists(temp_frames_dir):
                import shutil
                try:
                    shutil.rmtree(temp_frames_dir)
                    print(f"Removed temporary frames directory: {temp_frames_dir}")
                except Exception as cleanup_e:
                    print(f"Warning: Could not remove temporary frames directory: {cleanup_e}")
            
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
        
        # Determine which sections are active at which times to optimize image loading
        active_sections_by_time = {}
        all_needed_sections = set()  # Track ALL sections needed throughout the video
        
        # Map all time points to active sections
        for time_ms in range(0, int(total_frames / self.fps * 1000), 1000):  # Check every second
            for section_name, start_time in self.section_start_times.items():
                end_time = self.section_end_times.get(section_name, float('inf'))
                if start_time <= time_ms <= end_time:
                    active_sections_by_time[time_ms] = section_name
                    all_needed_sections.add(section_name)  # Add to master list
                    break
        
        print(f"All sections needed throughout video: {all_needed_sections}")
        
        # Pre-load ALL section images up front
        for section_name in all_needed_sections:
            if section_name not in self.section_images:
                # Find the image for this section
                section_image_path = os.path.join(section_images_dir, f"{section_name}_{self.language_code}.jpg")
                
                if not os.path.exists(section_image_path):
                    # Try English version as fallback
                    section_image_path = os.path.join(section_images_dir, f"{section_name}_en.jpg")
                
                if section_image_path and os.path.exists(section_image_path):
                    try:
                        # Load image with PIL to ensure proper color handling
                        pil_image = Image.open(section_image_path)
                        
                        # Resize if needed while preserving aspect ratio
                        target_width = 1920
                        target_height = 1080
                        
                        # Resize to target dimensions if needed
                        if pil_image.width != target_width or pil_image.height != target_height:
                            pil_image = pil_image.resize((target_width, target_height), Image.LANCZOS)
                        
                        # Convert to numpy array in RGB format
                        image = np.array(pil_image)
                        
                        # Store image in RGB format
                        self.section_images[section_name] = image
                        print(f"Pre-loaded section image: {section_name}")
                        
                        # Close PIL image to release memory
                        pil_image.close()
                    except Exception as e:
                        print(f"Error pre-loading section image {section_image_path}: {e}")
        
        # Create a temporary directory for storing frames
        import tempfile
        import os
        
        temp_frames_dir = tempfile.mkdtemp(prefix='video_frames_')
        print(f"Using temporary directory for frames: {temp_frames_dir}")
        
        # Map frames to segments and active words based on timing
        frame_to_segment = {}
        frame_to_active_word_info = {}
        
        # MEMORY OPTIMIZATION: Process frames in batches
        batch_size = 500  # Process 500 frames at a time
            
        try:
            # Process all frames in batches
            for batch_start in range(0, total_frames, batch_size):
                batch_end = min(batch_start + batch_size, total_frames)
                print(f"Processing frames {batch_start} to {batch_end-1}")
                
                # Clear previous batch data
                frame_to_segment.clear()
                frame_to_active_word_info.clear()
                
                # Process this batch of frames
                for frame_num in range(batch_start, batch_end):
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
                    
                    # Create and save each frame immediately instead of storing in memory
                    if (frame_num - batch_start) % 100 == 0:
                        print(f"Processing frames {frame_num} to {min(frame_num + 100 - 1, batch_end - 1)}")
                    
                    # Get segment and active word for this frame
                    segment = frame_to_segment.get(frame_num)
                    active_word_info = frame_to_active_word_info.get(frame_num)
                    
                    # Create the frame
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
                
            print(f"Generated all {len(frames)} frames for {total_frames} total frames")
            return frames, temp_frames_dir
            
        except Exception as e:
            print(f"Error generating frames: {e}")
            traceback.print_exc()
            import shutil
            shutil.rmtree(temp_frames_dir, ignore_errors=True)
            return [], None
    
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
                        # Print section usage at certain intervals (every second)
                        if time_ms % 1000 < 30:
                            print(f"Using section image for {active_section} at time {time_ms} ms")
                        break
        
        # Create the frame with background image or color
        if current_section_image is not None:
            try:
                # Use section image as background - working directly with RGB format
                # Convert directly to PIL Image (it's already in RGB format from our loading)
                img = Image.fromarray(current_section_image)
                
                # For Shorts (vertical format), we need to resize/crop the background image appropriately
                if self.is_shorts:
                    # Get original dimensions
                    orig_width, orig_height = img.size
                    
                    # Create a black background
                    new_img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
                    
                    # For shorts, maintain original aspect ratio without cropping
                    # Scale the image to fit either the width or height, whichever is smaller
                    # This ensures the whole image is visible
                    
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
            except Exception as e:
                print(f"Error using section image: {e}")
                # Fall back to solid color background
                img = Image.new('RGB', (self.width, self.height), self.background_color)
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
        
        # Add overlay just for the text area (not full width) if we have a background image
        if current_section_image is not None:
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
        
        # Convert PIL image to numpy array (RGB format)
        frame = np.array(img)
        return frame

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