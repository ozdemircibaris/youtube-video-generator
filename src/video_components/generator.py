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
        self.skip_intro_outro = False  # Default olarak intro/outro eklenecek, main.py'dan değiştirilebilir
        
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
        
        # English subtitles support
        self.english_word_timings = None
        self.enable_english_subtitles = False
        
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
        Create a synchronized text-to-speech video.
        
        Args:
            word_timings_path (str): Path to word timings JSON file
            audio_path (str): Path to audio file
            output_path (str): Path to save the output video
            section_images_dir (str): Optional directory with section images
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load word timings
            with open(word_timings_path, 'r', encoding='utf-8') as f:
                word_timings = json.load(f)
                
            print(f"Loaded {len(word_timings)} word timings from {word_timings_path}")
            
            # Check if we should load English subtitles (for non-English videos)
            if self.language_code != 'en':
                # Try to load English word timings
                english_word_timings_path = word_timings_path.replace(f'/{self.language_code}/', '/en/')
                if os.path.exists(english_word_timings_path):
                    try:
                        with open(english_word_timings_path, 'r', encoding='utf-8') as f:
                            self.english_word_timings = json.load(f)
                        print(f"Loaded {len(self.english_word_timings)} English word timings for subtitles")
                        self.enable_english_subtitles = True
                        
                        # Update frame builder with English subtitles settings
                        self.frame_builder = FrameBuilder(
                            self.language_code, 
                            self.is_shorts, 
                            self.width, 
                            self.height, 
                            english_subtitles=True, 
                            english_word_timings=self.english_word_timings
                        )
                    except Exception as e:
                        print(f"Error loading English subtitles: {e}")
                else:
                    print(f"No English word timings found at {english_word_timings_path}")
            
            # If this is a shorts video, trim word timings to 60 seconds
            if self.is_shorts:
                word_timings = self._trim_word_timings_for_shorts(word_timings)
                # Also trim English subtitles if enabled
                if self.enable_english_subtitles:
                    self.english_word_timings = self._trim_word_timings_for_shorts(self.english_word_timings)
                    # Update frame builder with trimmed English subtitles
                    self.frame_builder.english_word_timings = self.english_word_timings
            
            # Get audio duration
            audio_duration_ms = self._get_audio_duration(audio_path)
            if audio_duration_ms <= 0:
                print("Error: Could not determine audio duration.")
                return False
                
            print(f"Audio duration: {audio_duration_ms} ms")
            
            # Calculate total frames based on audio duration
            total_frames = int((audio_duration_ms / 1000) * self.fps)
            print(f"Generating {total_frames} frames at {self.fps} FPS")
            
            # Process section images if provided
            if section_images_dir:
                self._process_section_images(section_images_dir, word_timings)
            
            # Generate frames
            frames, temp_frames_dir = self._generate_frames(word_timings, total_frames)
            
            if not frames:
                print("Error: No frames were generated.")
                return False
                
            print(f"Generated {len(frames)} frames in {temp_frames_dir}")
            
            # Create video from frames
            result = self._create_video_from_frames(frames, audio_path, temp_frames_dir, output_path)
            
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_frames_dir)
                print(f"Cleaned up temporary directory: {temp_frames_dir}")
            except Exception as e:
                print(f"Warning: Could not clean up temp directory: {e}")
            
            # Clean up resources
            self._cleanup_resources()
            
            return result
            
        except Exception as e:
            print(f"Error creating video: {e}")
            traceback.print_exc()
            return False
            
    def _get_audio_duration(self, audio_path):
        """
        Get the duration of an audio file in milliseconds.
        
        Args:
            audio_path (str): Path to the audio file
            
        Returns:
            float: Duration in milliseconds
        """
        try:
            # Use ffprobe to get duration
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                duration_sec = float(result.stdout.strip())
                duration_ms = duration_sec * 1000  # Convert to milliseconds
                return duration_ms
            else:
                print(f"Error getting audio duration: {result.stderr}")
                return 0
        except Exception as e:
            print(f"Error determining audio duration: {e}")
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
                
                # Shorts ise veya skip_intro_outro true ise
                if getattr(self, 'is_shorts', False) or getattr(self, 'skip_intro_outro', False):
                    # Eğer shorts ise, ShortsCreator kullanarak content videodan vertical version oluştur
                    if getattr(self, 'is_shorts', False):
                        print("Shorts video oluşturuluyor: Content video direk vertical formata dönüştürülüyor (intro/outro olmadan)")
                        word_timings_path = self._find_word_timings_path(audio_path)
                        
                        # Ensure the shorts creator is properly initialized with vertical dimensions
                        if not hasattr(self, 'shorts_creator') or self.shorts_creator is None:
                            self.shorts_creator = ShortsCreator(
                                fps=self.fps,
                                width=config.SHORTS_VIDEO_WIDTH,
                                height=config.SHORTS_VIDEO_HEIGHT
                            )
                        
                        # Use the new direct content_video method that doesn't try to remove intro/outro
                        try:
                            print("Using direct content_video approach for shorts generation")
                            shorts_result = self.shorts_creator.create_shorts_from_content_video(
                                content_video, 
                                output_path
                            )
                            
                            if not shorts_result:
                                raise Exception("Shorts creation using content_video method returned False")
                                
                            if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
                                raise Exception(f"Shorts output file is missing or too small: {output_path}")
                                
                            print(f"Shorts video successfully created from content_video at {output_path}")
                            return True
                        except Exception as e:
                            print(f"Error during direct shorts creation: {e}")
                            print("Falling back to standard shorts creation method...")
                            
                            # Fall back to the original method if the direct method fails
                            try:
                                shorts_result = self.shorts_creator.create_shorts_from_standard(
                                    content_video, 
                                    output_path,
                                    word_timings_path
                                )
                                
                                if not shorts_result:
                                    raise Exception("Fallback shorts creation returned False")
                                    
                                if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
                                    raise Exception(f"Shorts output file is missing or too small: {output_path}")
                                    
                                print(f"Shorts video successfully created using fallback method at {output_path}")
                                return True
                            except Exception as fallback_err:
                                print(f"Fallback shorts creation also failed: {fallback_err}")
                                print("Attempting alternative shorts creation method...")
                            
                            # If both methods fail, try the direct FFmpeg approach
                            try:
                                # Create a simpler vertical video using ffmpeg directly
                                print("Using direct ffmpeg approach for vertical shorts conversion")
                                ffmpeg_vertical_cmd = [
                                    'ffmpeg',
                                    '-y',
                                    '-i', content_video,
                                    '-vf', f'scale=-1:{config.SHORTS_VIDEO_HEIGHT},pad={config.SHORTS_VIDEO_WIDTH}:{config.SHORTS_VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black',
                                    '-c:v', 'libx264',
                                    '-preset', 'medium',
                                    '-crf', '23',
                                    '-c:a', 'copy',
                                    '-shortest',
                                    output_path
                                ]
                                
                                print(f"Running alternative FFMPEG command: {' '.join(ffmpeg_vertical_cmd)}")
                                alt_result = subprocess.run(ffmpeg_vertical_cmd, capture_output=True, text=True)
                                
                                if alt_result.returncode == 0 and os.path.exists(output_path):
                                    print("Alternative vertical shorts creation successful!")
                                    return True
                                else:
                                    print(f"Alternative approach failed: {alt_result.stderr}")
                                    raise Exception("All shorts creation methods failed")
                            except Exception as alt_err:
                                print(f"All shorts creation methods failed: {alt_err}")
                                print("Using normal content video as a last resort.")
                                import shutil
                                shutil.copy2(content_video, output_path)
                    else:
                        # Normal video ama intro/outro atlanacak - direkt content videoyu kopyala
                        print("skip_intro_outro=True olduğundan intro/outro eklenmedi, content video direkt kullanılıyor.")
                        import shutil
                        shutil.copy2(content_video, output_path)
                    return True
                
                # Normal video oluşturma (intro/outro ile)
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
            
    def _find_word_timings_path(self, audio_path):
        """Audio path'ten word_timings path'i tahmin et."""
        # audio_path: /path/to/lang_code/speech.mp3
        # word_timings: /path/to/lang_code/timings.json
        try:
            dir_path = os.path.dirname(audio_path)
            return os.path.join(dir_path, "timings.json")
        except:
            # Fallback - ana dizindeki word_timings.json'ı kullan
            return os.path.join(os.path.dirname(os.path.dirname(audio_path)), "word_timings.json")
            
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
        print(f"\n--- Creating shorts video from standard video: {standard_video_path} ---")
        
        # Verify the standard video exists
        if not os.path.exists(standard_video_path):
            print(f"Standard video not found at: {standard_video_path}")
            return False
            
        try:
            # Ensure the shorts creator is properly initialized
            if not hasattr(self, 'shorts_creator') or self.shorts_creator is None:
                self.shorts_creator = ShortsCreator(
                    fps=self.fps,
                    width=config.SHORTS_VIDEO_WIDTH,
                    height=config.SHORTS_VIDEO_HEIGHT
                )
            
            # Check if this is a content_video (which already has intro/outro removed)
            is_content_video = os.path.basename(standard_video_path) == "content_video.mp4"
            
            if is_content_video:
                print("Detected content_video.mp4: Using direct approach without intro/outro detection")
                # Use direct content video method for better results
                result = self.shorts_creator.create_shorts_from_content_video(
                    standard_video_path, 
                    output_path
                )
            else:
                # Use standard approach that attempts to detect and remove intro/outro
                print("Using standard approach with intro/outro detection")
                result = self.shorts_creator.create_shorts_from_standard(
                    standard_video_path, 
                    output_path, 
                    word_timings_path
                )
            
            # Verify the output file was created properly
            if result and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                print(f"Shorts video successfully created at {output_path}")
                return True
                
            # If primary method fails, try the direct FFmpeg approach
            print("Primary method failed. Trying alternative FFmpeg approach...")
            
            # Alternative approach: Use FFmpeg directly
            try:
                # Create a vertical video using FFmpeg
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-y',
                    '-i', standard_video_path,
                    '-vf', f'scale=-1:{config.SHORTS_VIDEO_HEIGHT},pad={config.SHORTS_VIDEO_WIDTH}:{config.SHORTS_VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black',
                    '-c:v', 'libx264',
                    '-preset', 'medium', 
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-shortest',
                    '-t', '60', # Limit to 60 seconds for Shorts
                    output_path
                ]
                
                print(f"Running FFmpeg command: {' '.join(ffmpeg_cmd)}")
                ffmpeg_result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                
                if ffmpeg_result.returncode == 0 and os.path.exists(output_path):
                    print("Alternative FFmpeg approach successful!")
                    return True
                else:
                    print(f"FFmpeg error: {ffmpeg_result.stderr}")
                    return False
            except Exception as e:
                print(f"Error in alternative FFmpeg approach: {e}")
                return False
                
        except Exception as e:
            print(f"Error creating shorts from standard video: {e}")
            traceback.print_exc()
            return False
        
    def create_shorts_from_content_video(self, content_video_path, output_path):
        """
        Create a vertical shorts video directly from content_video.mp4 without intro/outro detection.
        
        Args:
            content_video_path (str): Path to the content video (without intro/outro)
            output_path (str): Path to save the shorts video
            
        Returns:
            bool: True if successful, False otherwise
        """
        print(f"\n--- Creating shorts directly from content video: {content_video_path} ---")
        
        # Verify the content video exists
        if not os.path.exists(content_video_path):
            print(f"Content video not found at: {content_video_path}")
            return False
            
        try:
            # Ensure the shorts creator is properly initialized
            if not hasattr(self, 'shorts_creator') or self.shorts_creator is None:
                self.shorts_creator = ShortsCreator(
                    fps=self.fps,
                    width=config.SHORTS_VIDEO_WIDTH,
                    height=config.SHORTS_VIDEO_HEIGHT
                )
            
            # Use the ShortsCreator's method
            result = self.shorts_creator.create_shorts_from_content_video(
                content_video_path, 
                output_path
            )
            
            # Verify the output file was created properly
            if result and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                print(f"Shorts video successfully created from content_video at {output_path}")
                return True
                
            # If the primary method fails, try the direct FFmpeg approach
            print("Primary method failed. Trying alternative FFmpeg approach...")
            
            # Alternative approach: Use FFmpeg directly
            try:
                # Create a vertical video using FFmpeg
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-y',
                    '-i', content_video_path,
                    '-vf', f'scale=-1:{config.SHORTS_VIDEO_HEIGHT},pad={config.SHORTS_VIDEO_WIDTH}:{config.SHORTS_VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black',
                    '-c:v', 'libx264',
                    '-preset', 'medium', 
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-shortest',
                    '-t', '60', # Limit to 60 seconds for Shorts
                    output_path
                ]
                
                print(f"Running FFmpeg command: {' '.join(ffmpeg_cmd)}")
                ffmpeg_result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                
                if ffmpeg_result.returncode == 0 and os.path.exists(output_path):
                    print("Alternative FFmpeg approach successful!")
                    return True
                else:
                    print(f"FFmpeg error: {ffmpeg_result.stderr}")
                    return False
            except Exception as e:
                print(f"Error in alternative FFmpeg approach: {e}")
                return False
                
        except Exception as e:
            print(f"Error creating shorts from content video: {e}")
            traceback.print_exc()
            return False 