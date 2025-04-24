"""
Main VideoGenerator class that coordinates the video generation process.
"""

import json
import os
import gc
import traceback
import tempfile
import subprocess
import shutil

from src import config
from src.video_components.frame_builder import FrameBuilder
from src.video_components.section_manager import SectionManager
from src.video_components.text_formatter import TextFormatter
from src.video_components.shorts_creator import ShortsCreator
from src.video_components.intro_outro_handler import IntroOutroHandler

class VideoGenerator:
    def __init__(self, language_code='en', is_shorts=False, reuse_content=False):
        """
        Initialize the video generator.
        
        Args:
            language_code (str): Language code for font selection
            is_shorts (bool): Whether to generate a YouTube Shorts video
            reuse_content (bool): Whether to reuse existing content (for efficient shorts generation)
        """
        self.is_shorts = is_shorts
        self.reuse_content = reuse_content
        self.language_code = language_code
        
        # Initialize dimensions based on video type
        if is_shorts:
            self.width = config.SHORTS_VIDEO_WIDTH
            self.height = config.SHORTS_VIDEO_HEIGHT
        else:
            self.width = config.VIDEO_WIDTH
            self.height = config.VIDEO_HEIGHT
            
        self.fps = config.VIDEO_FPS
        self.background_color = config.VIDEO_BACKGROUND_COLOR
        
        # Initialize component classes
        self.section_manager = SectionManager(language_code)
        self.text_formatter = TextFormatter(language_code, is_shorts)
        self.frame_builder = FrameBuilder(language_code, is_shorts, self.width, self.height)
        self.shorts_creator = ShortsCreator(self.fps, self.width, self.height)
        self.intro_outro_handler = IntroOutroHandler()
        
    def load_section_images(self, word_timings, section_images_dir):
        """
        Load section images and map them to word timings based on markers.
        
        Args:
            word_timings (list): Word timing information
            section_images_dir (str): Directory containing section images
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.section_manager.load_section_images(word_timings, section_images_dir)
        
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
                audio_duration_ms = self._get_audio_duration(audio_path) * 1000
                
                # For Shorts, check if audio exceeds 1 minute (60 seconds)
                if self.is_shorts and audio_duration_ms > config.SHORTS_MAX_DURATION_MS:
                    print(f"Warning: Audio duration ({audio_duration_ms/1000:.2f}s) exceeds YouTube Shorts maximum of 60 seconds.")
                    print("Trimming audio to 60 seconds...")
                    
                    # Trim word timings to only include words within the first 60 seconds
                    word_timings = self._trim_word_timings_for_shorts(word_timings)
                    audio_duration_ms = 60000
                
                # Load section images if provided
                if section_images_dir:
                    self._process_section_images(section_images_dir, word_timings)
                
                # Calculate total frames needed
                total_frames = int((audio_duration_ms / 1000) * self.fps)
                
                # Generate frames for main content
                print(f"Generating {total_frames} frames...")
                frames, temp_frames_dir = self._generate_frames(word_timings, total_frames)
                
                # Ensure output directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Free frame memory - now just a list of paths
                frames_paths = frames.copy()
                frames.clear()
                gc.collect()
                print("Frame references cleared from memory")
                
                # Create a temporary output path
                temp_output = os.path.join(temp_dir, os.path.basename(output_path))
                
                # Try different approaches to create the video
                success = self._create_video_from_frames(frames_paths, audio_path, temp_frames_dir, temp_output)
                
                # If successful, copy to final destination
                if success and os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
                    shutil.copy2(temp_output, output_path)
                    print(f"Video created successfully at {output_path}")
                    return True
                else:
                    print(f"Video creation failed")
                    return False
                
            finally:
                # Ensure proper resource cleanup even if an exception occurs
                self._cleanup_resources()
            
            # Final cleanup - remove temporary frames directory
            if temp_frames_dir and os.path.exists(temp_frames_dir):
                try:
                    shutil.rmtree(temp_frames_dir)
                    print(f"Removed temporary frames directory: {temp_frames_dir}")
                except Exception as e:
                    print(f"Warning: Could not remove temporary frames directory: {e}")
            
            return success
            
        except Exception as e:
            print(f"Error creating video: {e}")
            traceback.print_exc()
            return False
            
    def _get_audio_duration(self, audio_path):
        """Get audio duration using FFprobe."""
        try:
            ffprobe_cmd = [
                'ffprobe', 
                '-v', 'error', 
                '-show_entries', 'format=duration', 
                '-of', 'default=noprint_wrappers=1:nokey=1', 
                audio_path
            ]
            
            result = subprocess.run(ffprobe_cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except Exception as e:
            print(f"Error getting audio duration: {e}")
            return 0
            
    def _trim_word_timings_for_shorts(self, word_timings):
        """Trim word timings to fit within 60 seconds for YouTube Shorts."""
        trimmed_word_timings = []
        for word_info in word_timings:
            if word_info['start_time'] < config.SHORTS_MAX_DURATION_MS:
                # If word ends after 60s, adjust end time to 60s
                if word_info['end_time'] > config.SHORTS_MAX_DURATION_MS:
                    word_info['end_time'] = config.SHORTS_MAX_DURATION_MS
                trimmed_word_timings.append(word_info)
        
        print(f"Trimmed to {len(trimmed_word_timings)} words within 60 second limit")
        return trimmed_word_timings
        
    def _process_section_images(self, section_images_dir, word_timings):
        """Process section images for the video."""
        # Ensure the directory exists
        if not os.path.exists(section_images_dir):
            print(f"Creating section images directory: {section_images_dir}")
            os.makedirs(section_images_dir, exist_ok=True)
            
        # Check if the directory has any images
        image_files = [f for f in os.listdir(section_images_dir) 
                    if f.endswith(('.jpg', '.jpeg', '.png')) and os.path.isfile(os.path.join(section_images_dir, f))]
        
        if image_files:
            print(f"Found {len(image_files)} image files in section images directory.")
            
            # Load section images
            self.section_manager.load_section_images(word_timings, section_images_dir)
        else:
            print(f"Warning: No image files found in section images directory: {section_images_dir}")
            
    def _generate_frames(self, word_timings, total_frames):
        """
        Generate frames for the video.
        
        Args:
            word_timings (list): List of word timing information
            total_frames (int): Total number of frames to generate
            
        Returns:
            tuple: List of frame paths and temporary directory path
        """
        # Group words into sentences or logical segments
        segments = self.text_formatter.group_words_into_segments(word_timings)
        
        # Create a temporary directory for storing frames
        temp_frames_dir = tempfile.mkdtemp(prefix='video_frames_')
        
        # Use the frame builder to generate all frames
        frames = self.frame_builder.generate_frames(
            segments, 
            word_timings, 
            total_frames, 
            self.fps, 
            temp_frames_dir,
            self.section_manager.section_start_times,
            self.section_manager.section_end_times,
            self.section_manager.section_images
        )
        
        return frames, temp_frames_dir
        
    def _create_video_from_frames(self, frames, audio_path, temp_frames_dir, output_path):
        """Create video from frames using FFmpeg or OpenCV."""
        # Try FFmpeg approach first
        try:
            print("\nTrying direct FFMPEG approach...")
            
            # Generate a temporary path for the content video
            content_video = os.path.join(os.path.dirname(output_path), "content_video.mp4")
            
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
                content_video
            ]
            
            print(f"Running FFMPEG command: {' '.join(ffmpeg_frames_cmd)}")
            result = subprocess.run(ffmpeg_frames_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("FFMPEG content video creation successful!")
                
                # Now add intro, outro, and background music
                success = self.intro_outro_handler.add_intro_outro_music(content_video, audio_path, output_path)
                
                if success:
                    print("Successfully added intro, outro, and background music!")
                else:
                    print("Failed to add intro/outro, falling back to content-only video")
                    # Copy content video to output as fallback
                    shutil.copy2(content_video, output_path)
                
                return True
            else:
                print(f"FFMPEG error: {result.stderr}")
                print("FFMPEG approach failed, trying alternative method...")
                return self._create_video_with_opencv(frames, audio_path, temp_frames_dir, output_path)
                
        except Exception as e:
            print(f"Error in FFMPEG approach: {e}")
            print("Trying alternative method...")
            return self._create_video_with_opencv(frames, audio_path, temp_frames_dir, output_path)
            
    def _create_video_with_opencv(self, frames, audio_path, temp_frames_dir, output_path):
        """Create video using OpenCV as fallback."""
        import cv2
        
        try:
            print("\nTrying OpenCV approach...")
            
            # Define the codec and create VideoWriter object
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            opencv_output = os.path.join(os.path.dirname(output_path), "opencv_output.mp4")
            
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
                output_path
            ]
            
            print(f"Running FFMPEG audio merge command: {' '.join(ffmpeg_audio_cmd)}")
            result = subprocess.run(ffmpeg_audio_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("OpenCV + FFMPEG audio merge successful!")
                return True
            else:
                print(f"FFMPEG audio merge error: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error in OpenCV approach: {e}")
            return False
            
    def _cleanup_resources(self):
        """Clean up resources to prevent memory leaks."""
        print("Cleaning up video generation resources...")
        
        # Clear section images from section manager
        self.section_manager.clear_images()
        
        # Force garbage collection multiple times
        print("Running deep garbage collection...")
        for _ in range(3):
            gc.collect()
        
        print("Video generation resources cleaned up")
        
    def create_shorts_from_standard(self, standard_video_path, output_path, word_timings_path):
        """
        Create a vertical shorts video from an existing standard video.
        
        Args:
            standard_video_path (str): Path to the standard video
            output_path (str): Path to save the shorts video
            word_timings_path (str): Path to the word timings file (for duration verification)
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.shorts_creator.create_shorts_from_standard(
            standard_video_path, 
            output_path, 
            word_timings_path
        ) 