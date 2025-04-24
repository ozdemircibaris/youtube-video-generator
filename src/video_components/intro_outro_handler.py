"""
Handles adding intro, outro, and background music to videos.
"""

import os
import traceback
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips

class IntroOutroHandler:
    def __init__(self):
        """Initialize the intro/outro handler."""
        self.assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
        self.intro_path = os.path.join(self.assets_dir, "intro.mp4")
        self.outro_path = os.path.join(self.assets_dir, "outro.mp4")
        self.bg_music_path = os.path.join(self.assets_dir, "background-music.mp3")
        
    def add_intro_outro_music(self, content_video_path, content_audio_path, final_output_path):
        """
        Add intro, outro, and background music to the content video.
        
        Args:
            content_video_path (str): Path to the content video
            content_audio_path (str): Path to the content audio
            final_output_path (str): Path to save the final video
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("\nAdding intro, outro, and background music...")
            
            # Check if files exist
            intro_exists = os.path.exists(self.intro_path)
            outro_exists = os.path.exists(self.outro_path)
            bg_music_exists = os.path.exists(self.bg_music_path)
            
            print(f"Intro video: {'Found' if intro_exists else 'Not found'} at {self.intro_path}")
            print(f"Outro video: {'Found' if outro_exists else 'Not found'} at {self.outro_path}")
            print(f"Background music: {'Found' if bg_music_exists else 'Not found'} at {self.bg_music_path}")
            
            # If neither intro nor outro exists, just return the content video
            if not intro_exists and not outro_exists:
                print("No intro or outro found. Keeping original content video.")
                import shutil
                shutil.copy2(content_video_path, final_output_path)
                return True
            
            # Load the content video
            print("Loading content video...")
            content_clip = VideoFileClip(content_video_path)
            
            clips_to_concat = []
            
            # Add intro if it exists
            if intro_exists:
                print("Loading intro video...")
                intro_clip = VideoFileClip(self.intro_path)
                clips_to_concat.append(intro_clip)
            
            # Add content
            clips_to_concat.append(content_clip)
            
            # Add outro if it exists
            if outro_exists:
                print("Loading outro video...")
                outro_clip = VideoFileClip(self.outro_path)
                clips_to_concat.append(outro_clip)
            
            # Concatenate all clips
            print("Concatenating video clips...")
            final_clip = concatenate_videoclips(clips_to_concat)
            
            # Add background music to intro and outro if music exists
            if bg_music_exists and (intro_exists or outro_exists):
                self._add_background_music(
                    final_clip, content_audio_path, 
                    intro_exists, outro_exists, 
                    intro_clip.duration if intro_exists else 0,
                    outro_clip.duration if outro_exists else 0,
                    content_clip.duration
                )
            
            # Write the final video
            print(f"Writing final video to {final_output_path}...")
            final_clip.write_videofile(
                final_output_path,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=os.path.join(os.path.dirname(final_output_path), "temp_audio.m4a"),
                remove_temp=True,
                threads=4,
                preset="medium",
                ffmpeg_params=["-pix_fmt", "yuv420p"]
            )
            
            # Close all clips to release resources
            final_clip.close()
            content_clip.close()
            
            if intro_exists:
                intro_clip.close()
            if outro_exists:
                outro_clip.close()
            
            print("Successfully combined intro, content, and outro with background music!")
            return True
            
        except Exception as e:
            print(f"Error adding intro/outro: {e}")
            traceback.print_exc()
            return False
            
    def _add_background_music(self, final_clip, content_audio_path, 
                           has_intro, has_outro, intro_duration, 
                           outro_duration, content_duration):
        """Add background music to intro and outro sections."""
        print("Adding background music to intro/outro sections...")
        
        # Load the background music
        bg_music = AudioFileClip(self.bg_music_path)
        
        # Load content audio
        content_audio = AudioFileClip(content_audio_path)
        
        # Calculate total duration
        total_duration = intro_duration + content_duration + outro_duration
        
        # Create a merged audio clip:
        # - Background music during intro
        # - Content audio during content
        # - Background music during outro
        
        # First, loop the background music if needed to cover intro and outro
        bg_music_needed_duration = intro_duration + outro_duration
        if bg_music.duration < bg_music_needed_duration:
            # Loop the background music if it's too short
            loop_count = int(bg_music_needed_duration / bg_music.duration) + 1
            bg_music = bg_music.loop(loop_count)
        
        # Clip background music to the needed duration
        bg_music = bg_music.subclip(0, bg_music_needed_duration)
        
        # Fade out the background music at the end of the intro
        if intro_duration > 0:
            bg_music = bg_music.audio_fadeout(1)
        
        # Set audio for the final clip segments
        if has_intro and has_outro:
            # Both intro and outro exist
            intro_audio = bg_music.subclip(0, intro_duration)
            outro_audio = bg_music.subclip(intro_duration, intro_duration + outro_duration)
            
            # Combined audio: intro music + content audio + outro music
            final_audio = CompositeAudioClip([
                intro_audio.set_start(0),
                content_audio.set_start(intro_duration),
                outro_audio.set_start(intro_duration + content_duration)
            ])
            
        elif has_intro:
            # Only intro exists
            intro_audio = bg_music.subclip(0, intro_duration)
            
            # Combined audio: intro music + content audio
            final_audio = CompositeAudioClip([
                intro_audio.set_start(0),
                content_audio.set_start(intro_duration)
            ])
            
        elif has_outro:
            # Only outro exists
            outro_audio = bg_music.subclip(0, outro_duration)
            
            # Combined audio: content audio + outro music
            final_audio = CompositeAudioClip([
                content_audio.set_start(0),
                outro_audio.set_start(content_duration)
            ])
        
        # Set the final audio to the clip
        final_clip.audio = final_audio 