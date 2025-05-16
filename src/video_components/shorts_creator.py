"""
ShortsCreator component for generating YouTube Shorts format videos.
"""

import os
import json
import traceback
import subprocess
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
                
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
            # Load the word timings to get the total duration
            try:
                with open(word_timings_path, 'r') as f:
                    word_timings = json.load(f)
                    
                # Calculate the total duration
                total_duration_ms = self._calculate_duration_from_timings(word_timings)
                if total_duration_ms <= 0:
                    print("Warning: Invalid word timings data, using video duration instead")
                    total_duration_ms = None  # We'll determine from the video later
            except Exception as e:
                print(f"Warning: Could not load word timings, using video duration instead: {e}")
                word_timings = []
                total_duration_ms = None
                
            # For Shorts, limit to 60 seconds
            shorts_max_duration_ms = config.SHORTS_MAX_DURATION_MS  # 60 seconds
            
            # Ensure target dimensions are even (required by h264)
            width = self.width - (self.width % 2)
            height = self.height - (self.height % 2)
                
            # Try/except block for video loading
            try:
                # Load the standard video
                print(f"Loading video: {standard_video_path}")
                video = VideoFileClip(standard_video_path)
                
                # If we couldn't get duration from word timings, get it from the video
                if total_duration_ms is None:
                    total_duration_ms = video.duration * 1000
                    print(f"Using video duration: {total_duration_ms/1000:.1f} seconds")
                
                # Determine if we need to trim the video
                if total_duration_ms > shorts_max_duration_ms:
                    print(f"Original content duration ({total_duration_ms/1000:.1f}s) exceeds Shorts limit. Trimming to 60s.")
                    end_time_ms = shorts_max_duration_ms
                else:
                    end_time_ms = total_duration_ms
                    
                print(f"Creating shorts with duration: {end_time_ms/1000:.1f} seconds")
                
                # INTRO/OUTRO TEMIZLEME: İçerik videosunu belirle ve intro/outro'yu kaldır
                # Word timings'teki ilk ve son kelimelerin zamanlamalarını bul
                if len(word_timings) > 0:
                    first_word = word_timings[0]
                    last_word = word_timings[-1]
                    
                    # İçerik videosunun başlangıç ve bitiş zamanlarını belirle
                    content_start_time = first_word.get('start_time', 0) / 1000.0  # saniyeye çevir
                    content_end_time = last_word.get('end_time', video.duration) / 1000.0  # saniyeye çevir
                    
                    # İçerik video süresi hesapla (marj ekleyerek)
                    content_duration = content_end_time - content_start_time
                    
                    # Eğer içerik videoda intro varsa (content_start_time > 0.5s), intro'yu atlayıp sadece içerik kısmını al
                    if content_start_time > 0.5:
                        print(f"Tespit edilen intro ({content_start_time:.2f}s) atlanıyor, sadece içerik alınıyor.")
                        # İçerik bölümünü original videodan kes ve 0. saniyeden başlat
                        intro_end = max(0, content_start_time - 0.2)  # İntro bitişi (200ms marj)
                        content_duration = min(video.duration - intro_end, content_duration + 0.5)  # İçerik süresi (500ms marj)
                        video = video.subclip(intro_end, min(video.duration, intro_end + content_duration))
                        print(f"Video intro sonrasından alındı: {intro_end:.2f}s --> {intro_end + content_duration:.2f}s, yeni süre: {video.duration:.2f}s")
                    
                    # Eğer videonun sonunda outro varsa da atla
                    elif content_end_time < video.duration - 0.5:
                        print(f"Tespit edilen outro atlanıyor: {content_end_time:.2f}s sonrası atlanıyor.")
                        outro_start = min(video.duration, content_end_time + 0.2)  # Outro başlangıcı (200ms marj)
                        video = video.subclip(0, outro_start)
                        print(f"Video outro öncesine kadar alındı: 0s --> {outro_start:.2f}s, yeni süre: {video.duration:.2f}s")
                    
                    # Hem intro hem outro varsa, sadece içerik kısmını al
                    elif content_start_time > 0.5 and content_end_time < video.duration - 0.5:
                        print(f"Tespit edilen intro ve outro atlanıyor, sadece içerik alınıyor: {content_start_time:.2f}s --> {content_end_time:.2f}s")
                        intro_end = max(0, content_start_time - 0.2)  # İntro bitişi (200ms marj)
                        outro_start = min(video.duration, content_end_time + 0.2)  # Outro başlangıcı (200ms marj)
                        video = video.subclip(intro_end, outro_start)
                        print(f"İçerik video kırpıldı, yeni süre: {video.duration:.2f}s")

                # Make sure we have audio
                if video.audio is None:
                    print("Warning: Video has no audio track. Trying to extract audio...")
                    try:
                        # Try to extract audio using ffmpeg directly
                        temp_audio_path = os.path.join(os.path.dirname(output_path), "temp_audio.m4a")
                        ffmpeg_audio_cmd = [
                            'ffmpeg',
                            '-y',
                            '-i', standard_video_path,
                            '-vn',
                            '-c:a', 'aac',
                            '-b:a', '192k',
                            temp_audio_path
                        ]
                        subprocess.run(ffmpeg_audio_cmd, capture_output=True, check=True)
                        
                        # Load the audio if extraction worked
                        if os.path.exists(temp_audio_path) and os.path.getsize(temp_audio_path) > 1000:
                            from moviepy.editor import AudioFileClip
                            audio = AudioFileClip(temp_audio_path)
                        else:
                            print("Audio extraction failed. Creating silent video.")
                            audio = None
                    except Exception as audio_err:
                        print(f"Error extracting audio: {audio_err}")
                        audio = None
                else:
                    # Extract audio from the loaded video
                    audio = video.audio
                
                # Create black background with target dimensions
                print("Creating black background for vertical layout...")
                bg = ColorClip(size=(width, height), color=(0, 0, 0), duration=video.duration)
                
                # Use outscale factor to resize the original video
                print("Creating vertical layout...")
                final_video = self._create_vertical_layout(video, bg, width, height)
                
                # Trim if necessary
                if total_duration_ms > shorts_max_duration_ms:
                    print(f"Trimming video to {shorts_max_duration_ms/1000} seconds...")
                    final_video = self._trim_video(final_video, audio, shorts_max_duration_ms)
                else:
                    # Make sure we have the audio
                    if audio is not None:
                        final_video = final_video.set_audio(audio)
                
                # Write the shorts video with enhanced quality settings
                print("Writing shorts video with enhanced quality...")
                self._write_video(final_video, output_path)
                
                # Clean up resources
                self._cleanup_resources(video, final_video)
                
                # Verify the output
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    print(f"Shorts video created successfully at {output_path}")
                    
                    # Clean up any temporary files
                    temp_audio_path = os.path.join(os.path.dirname(output_path), "temp_audio.m4a")
                    if os.path.exists(temp_audio_path):
                        try:
                            os.remove(temp_audio_path)
                        except:
                            pass
                    
                    return True
                else:
                    print(f"Failed to create shorts video at {output_path}")
                    return False
                
            except Exception as video_err:
                print(f"Error processing video: {video_err}")
                traceback.print_exc()
                
                # Try direct FFmpeg approach as fallback
                print("Attempting direct FFmpeg approach as fallback...")
                try:
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-y',
                        '-i', standard_video_path,
                        '-vf', f'scale=-1:{height},pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black',
                        '-c:v', 'libx264',
                        '-preset', 'medium',
                        '-crf', '23',
                        '-c:a', 'aac',
                        '-b:a', '192k',
                        '-shortest',
                        '-t', '60', # Limit to 60 seconds
                        output_path
                    ]
                    
                    print(f"Running FFmpeg command: {' '.join(ffmpeg_cmd)}")
                    ffmpeg_result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                    
                    if ffmpeg_result.returncode == 0 and os.path.exists(output_path):
                        print("Direct FFmpeg approach successful!")
                        return True
                    else:
                        print(f"FFmpeg error: {ffmpeg_result.stderr}")
                        return False
                except Exception as ffmpeg_err:
                    print(f"Error in FFmpeg fallback: {ffmpeg_err}")
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

    def create_shorts_from_content_video(self, content_video_path, output_path):
        """
        Create a vertical shorts video directly from content_video.mp4 without intro/outro detection.
        This is specifically for content_video which already has no intro/outro.
        
        Args:
            content_video_path (str): Path to the content video (without intro/outro)
            output_path (str): Path to save the shorts video
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"Creating shorts directly from content video: {content_video_path}")
            
            # Verify the content video exists
            if not os.path.exists(content_video_path):
                print(f"Content video not found at: {content_video_path}")
                return False
                
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
            # Ensure target dimensions are even (required by h264)
            width = self.width - (self.width % 2)
            height = self.height - (self.height % 2)
                
            # Try MoviePy approach first
            try:
                # Load the content video
                print(f"Loading content video: {content_video_path}")
                video = VideoFileClip(content_video_path)
                
                # Get duration in milliseconds
                total_duration_ms = video.duration * 1000
                print(f"Content video duration: {total_duration_ms/1000:.1f} seconds")
                
                # For Shorts, limit to 60 seconds
                shorts_max_duration_ms = config.SHORTS_MAX_DURATION_MS  # 60 seconds
                
                # Extract audio
                if video.audio is None:
                    print("Warning: Video has no audio track. Trying to extract audio...")
                    try:
                        # Try to extract audio using ffmpeg directly
                        temp_audio_path = os.path.join(os.path.dirname(output_path), "temp_audio.m4a")
                        ffmpeg_audio_cmd = [
                            'ffmpeg',
                            '-y',
                            '-i', content_video_path,
                            '-vn',
                            '-c:a', 'aac',
                            '-b:a', '192k',
                            temp_audio_path
                        ]
                        subprocess.run(ffmpeg_audio_cmd, capture_output=True, check=True)
                        
                        # Load the audio if extraction worked
                        if os.path.exists(temp_audio_path) and os.path.getsize(temp_audio_path) > 1000:
                            from moviepy.editor import AudioFileClip
                            audio = AudioFileClip(temp_audio_path)
                        else:
                            print("Audio extraction failed. Creating silent video.")
                            audio = None
                    except Exception as audio_err:
                        print(f"Error extracting audio: {audio_err}")
                        audio = None
                else:
                    # Extract audio from the loaded video
                    audio = video.audio
                
                # Create black background with target dimensions
                print("Creating black background for vertical layout...")
                bg = ColorClip(size=(width, height), color=(0, 0, 0), duration=video.duration)
                
                # Create vertical layout
                print("Creating vertical layout...")
                final_video = self._create_vertical_layout(video, bg, width, height)
                
                # Trim if necessary
                if total_duration_ms > shorts_max_duration_ms:
                    print(f"Trimming video to {shorts_max_duration_ms/1000} seconds...")
                    final_video = self._trim_video(final_video, audio, shorts_max_duration_ms)
                else:
                    # Make sure we have the audio
                    if audio is not None:
                        final_video = final_video.set_audio(audio)
                
                # Write the shorts video with enhanced quality settings
                print("Writing shorts video with enhanced quality...")
                self._write_video(final_video, output_path)
                
                # Clean up resources
                self._cleanup_resources(video, final_video)
                
                # Verify the output
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    print(f"Shorts video created successfully at {output_path}")
                    
                    # Clean up any temporary files
                    temp_audio_path = os.path.join(os.path.dirname(output_path), "temp_audio.m4a")
                    if os.path.exists(temp_audio_path):
                        try:
                            os.remove(temp_audio_path)
                        except:
                            pass
                    
                    return True
                else:
                    print(f"Failed to create shorts video at {output_path}")
                    return False
                    
            except Exception as moviepy_err:
                print(f"Error in MoviePy approach: {moviepy_err}")
                traceback.print_exc()
                
                # Fall back to FFmpeg approach
                print("Falling back to direct FFmpeg approach...")
                
            # Direct FFmpeg approach (used either as primary or fallback)
            try:
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-y',
                    '-i', content_video_path,
                    '-vf', f'scale=-1:{height},pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black',
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
                    print("FFmpeg approach successful!")
                    return True
                else:
                    print(f"FFmpeg error: {ffmpeg_result.stderr}")
                    return False
            except Exception as ffmpeg_err:
                print(f"Error in FFmpeg approach: {ffmpeg_err}")
                traceback.print_exc()
                return False
                
        except Exception as e:
            print(f"Error creating shorts video: {e}")
            traceback.print_exc()
            return False 