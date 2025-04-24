"""
ShortsCreator component for generating YouTube Shorts format videos.
"""

import os
import json
import traceback
from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip
import src.config as config

class ShortsCreator:
    def __init__(self, fps=30, width=1080, height=1920):
        """
        Initialize the shorts creator.
        
        Args:
            fps (int): Frames per second for the video
            width (int): Width of the shorts video (default: 1080)
            height (int): Height of the shorts video (default: 1920)
        """
        self.fps = fps
        self.width = width
        self.height = height
        
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
        try:
            print(f"Creating shorts video from standard video: {standard_video_path}")
            
            # Verify the paths
            if not os.path.exists(standard_video_path):
                print(f"Standard video not found at: {standard_video_path}")
                return False
                
            # Load the word timings to get the total duration
            with open(word_timings_path, 'r') as f:
                word_timings = json.load(f)
                
            # Calculate the total duration
            total_duration_ms = self._calculate_duration_from_timings(word_timings)
            if total_duration_ms <= 0:
                print("Invalid word timings data")
                return False
                
            # For Shorts, limit to 60 seconds
            shorts_max_duration_ms = config.SHORTS_MAX_DURATION_MS  # 60 seconds
            
            # Determine if we need to trim the video
            if total_duration_ms > shorts_max_duration_ms:
                print(f"Original content duration ({total_duration_ms/1000:.1f}s) exceeds Shorts limit. Trimming to 60s.")
                end_time_ms = shorts_max_duration_ms
            else:
                end_time_ms = total_duration_ms
                
            print(f"Creating shorts with duration: {end_time_ms/1000:.1f} seconds")
            
            # Ensure target dimensions are even (required by h264)
            width = self.width - (self.width % 2)
            height = self.height - (self.height % 2)
                
            # Load the standard video
            video = VideoFileClip(standard_video_path)
            
            # Extract audio
            audio = video.audio
            
            # Create black background with target dimensions
            bg = ColorClip(size=(width, height), color=(0, 0, 0), duration=video.duration)
            
            # Use outscale factor to resize the original video
            final_video = self._create_vertical_layout(video, bg, width, height)
            
            # Trim if necessary
            if total_duration_ms > shorts_max_duration_ms:
                final_video = self._trim_video(final_video, audio, shorts_max_duration_ms)
            else:
                # Make sure we have the audio
                final_video = final_video.set_audio(audio)
            
            # Write the shorts video with enhanced quality settings
            print("Writing shorts video with enhanced quality...")
            self._write_video(final_video, output_path)
            
            # Clean up resources
            self._cleanup_resources(video, final_video)
            
            if os.path.exists(output_path):
                print(f"Shorts video created successfully at {output_path}")
                return True
            else:
                print(f"Failed to create shorts video at {output_path}")
                return False
                
        except Exception as e:
            print(f"Error creating shorts video: {e}")
            traceback.print_exc()
            return False
            
    def _calculate_duration_from_timings(self, word_timings):
        """Calculate total duration from word timings."""
        if not word_timings or not isinstance(word_timings, list) or len(word_timings) == 0:
            return 0
            
        last_word = word_timings[-1]
        if isinstance(last_word, dict) and 'end_time' in last_word:
            return last_word['end_time']
        return 0
        
    def _create_vertical_layout(self, video, bg, width, height):
        """Create vertical layout for Shorts."""
        # Use outscale factor (this will make the video appear smaller within the frame)
        outscale_factor = 0.5  # 50% of original size - 50% zoom out
        
        # Calculate new dimensions maintaining aspect ratio
        input_ratio = video.w / video.h
        
        # Determine sizing approach based on video aspect
        if input_ratio > 1.5:  # Very wide video
            # For very wide content, do a partial crop + scale
            # First crop sides a bit, then scale to fit
            crop_amount = int(video.w * 0.15)  # Crop 15% from sides (7.5% each side)
            cropped = video.crop(x1=crop_amount/2, x2=video.w-crop_amount/2)
            
            # Then scale to shorts height with outscale
            new_height = int(height * outscale_factor)
            new_width = int(new_height * (cropped.w / cropped.h))
            resized_video = cropped.resize((new_width, new_height))
            
        else:  # Normal or narrower video
            # Use standard fit approach
            if input_ratio >= 1:  # Wider than tall (or square)
                # Base sizing on height for better visibility 
                new_height = int(height * outscale_factor)
                new_width = int(new_height * input_ratio)
            else:  # Taller than wide
                # Base on width for better fill
                new_width = int(width * outscale_factor)
                new_height = int(new_width / input_ratio)
            
            # Resize the video
            resized_video = video.resize((new_width, new_height))
        
        # Ensure dimensions are even
        if new_width % 2 != 0:
            new_width -= 1
            resized_video = resized_video.resize((new_width, new_height))
        if new_height % 2 != 0:
            new_height -= 1
            resized_video = resized_video.resize((new_width, new_height))
            
        print(f"Resizing video to {new_width}x{new_height} (balanced approach)")
        
        # Position the video in the center of the frame
        return CompositeVideoClip([
            bg,
            resized_video.set_position("center")
        ])
        
    def _trim_video(self, video, audio, max_duration_ms):
        """Trim video to maximum duration for Shorts."""
        trimmed_video = video.subclip(0, max_duration_ms/1000)
        # Also trim audio
        trimmed_audio = audio.subclip(0, max_duration_ms/1000)
        return trimmed_video.set_audio(trimmed_audio)
        
    def _write_video(self, video, output_path):
        """Write video with enhanced quality settings."""
        video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=self.fps,
            bitrate="5000k",    # Higher bitrate for better quality
            threads=4,          # More threads for faster encoding
            preset='medium',    # Good balance between speed and quality
            ffmpeg_params=["-pix_fmt", "yuv420p", "-profile:v", "high"]  # Better compatibility & quality
        )
        
    def _cleanup_resources(self, *clips):
        """Clean up resources."""
        for clip in clips:
            if clip is not None:
                try:
                    clip.close()
                except:
                    pass 