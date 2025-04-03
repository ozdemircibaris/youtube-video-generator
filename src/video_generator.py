import os
import numpy as np
import re
import random
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, concatenate_videoclips, CompositeVideoClip, ColorClip,
    ImageSequenceClip, clips_array
)
from src.config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, FONT_SIZE, FONT_COLOR, HIGHLIGHT_COLOR,
    MAX_WORDS_PER_LINE, BACKGROUND_COLOR, OUTPUT_DIR,
    INTRO_VIDEO, OUTRO_VIDEO, BACKGROUND_MUSIC, BACKGROUND_MUSIC_VOLUME,
    BACKGROUND_VIDEOS_DIR, SHORTS_MAX_DURATION, SHORTS_VIDEO_WIDTH, SHORTS_VIDEO_HEIGHT,
    SHORTS_FONT_SIZE, ENGLISH_LEVEL_RATES
)
import pydub
import math
import glob
import cv2
import time

def get_random_background_video():
    """Get a random background video from the background_videos directory"""
    background_videos = glob.glob(os.path.join(BACKGROUND_VIDEOS_DIR, '*.mp4'))
    if not background_videos:
        print("No background videos found. Using solid color background.")
        return None
    
    # Select a random video
    selected_video = random.choice(background_videos)
    print(f"Selected background video: {os.path.basename(selected_video)}")
    return selected_video

def split_text_into_sentences(text):
    """Split text into sentences"""
    # Simple sentence splitting - handles periods, question marks, and exclamation points
    sentences = re.split(r'(?<=[.!?])\s+', text)
    # Filter out empty sentences
    return [s for s in sentences if s.strip()]

def get_audio_duration(audio_path):
    """Get the actual duration of an audio file"""
    try:
        audio = pydub.AudioSegment.from_file(audio_path)
        return audio.duration_seconds
    except Exception as e:
        print(f"Error getting audio duration: {e}")
        return None

def add_text_to_frame(frame, text, position=(50, 50), font_size=40, color=(255, 223, 0), thickness=2, bg_opacity=0.6):
    """Add text to a frame using OpenCV instead of TextClip"""
    # Make a copy of the frame to avoid modifying the original
    result = frame.copy()
    
    # Add semi-transparent black background for readability
    h, w = frame.shape[:2]
    overlay = np.zeros_like(frame)
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, bg_opacity, result, 1 - bg_opacity, 0, result)
    
    # Calculate text size to center text
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(text, font, font_size/30, thickness)[0]
    
    # Split text into lines if it's too long
    max_width = w - 100  # Leave margins
    if text_size[0] > max_width:
        words = text.split()
        lines = []
        current_line = []
        current_width = 0
        
        for word in words:
            word_size = cv2.getTextSize(word + " ", font, font_size/30, thickness)[0]
            if current_width + word_size[0] <= max_width:
                current_line.append(word)
                current_width += word_size[0]
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_width = word_size[0]
        
        if current_line:
            lines.append(" ".join(current_line))
    else:
        lines = [text]
    
    # Calculate vertical centering
    line_height = text_size[1] + 10
    total_height = line_height * len(lines)
    y_start = (h - total_height) // 2
    
    # Add each line of text
    for i, line in enumerate(lines):
        line_size = cv2.getTextSize(line, font, font_size/30, thickness)[0]
        x = (w - line_size[0]) // 2  # Center horizontally
        y = y_start + (i + 1) * line_height
        
        # Add text shadow/outline (for better readability)
        cv2.putText(result, line, (x+2, y+2), font, font_size/30, (0, 0, 0), thickness+1)
        cv2.putText(result, line, (x, y), font, font_size/30, color, thickness)
    
    return result

def create_opencv_text_video(bg_clip, sentence_timings, audio_duration, font_size=60):
    """Create text overlays using OpenCV instead of TextClip"""
    print("Creating text overlays using OpenCV...")
    
    # Check the input parameters
    if bg_clip is None:
        print("ERROR: Background clip is None. Cannot create text overlays.")
        return None
    
    if not sentence_timings:
        print("WARNING: No sentence timings provided. Video will have no text overlays.")
    else:
        print(f"Received {len(sentence_timings)} sentences for text overlay")
        # Print first few sentence timings for debugging
        for i, st in enumerate(sentence_timings[:3]):
            print(f"  Sentence {i+1}: '{st['text']}' ({st['start']:.2f}s - {st['end']:.2f}s)")
        if len(sentence_timings) > 3:
            print(f"  ... and {len(sentence_timings) - 3} more sentences")
    
    # Get the frame size from the background clip
    frame_width, frame_height = VIDEO_WIDTH, VIDEO_HEIGHT
    fps = 30
    
    print(f"Creating video with dimensions {frame_width}x{frame_height} at {fps} fps")
    
    # Create a VideoWriter to save the video
    temp_output = os.path.join(OUTPUT_DIR, f"temp_content_{int(time.time())}.mp4")
    
    # Try different codecs for compatibility
    try:
        # First try H264 on Mac
        if os.name == 'posix' and os.uname().sysname == 'Darwin':  # macOS
            print("Detected macOS, using 'avc1' codec")
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
        else:
            # Use mp4v for other platforms
            print(f"Using 'mp4v' codec")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        
        out = cv2.VideoWriter(temp_output, fourcc, fps, (frame_width, frame_height))
        
        # If the video writer failed to open, try alternative codecs
        if not out.isOpened():
            print("First codec choice failed, trying alternative...")
            
            # Try XVID as a fallback
            print("Trying 'XVID' codec...")
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            temp_output = os.path.join(OUTPUT_DIR, f"temp_content_xvid_{int(time.time())}.avi")
            out = cv2.VideoWriter(temp_output, fourcc, fps, (frame_width, frame_height))
            
            if not out.isOpened():
                # Last resort - try MJPG
                print("Trying 'MJPG' codec...")
                fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                temp_output = os.path.join(OUTPUT_DIR, f"temp_content_mjpg_{int(time.time())}.avi")
                out = cv2.VideoWriter(temp_output, fourcc, fps, (frame_width, frame_height))
        
        if not out.isOpened():
            print(f"ERROR: Could not open video writer with any codec. Video generation will fail.")
            return None
        
        print(f"Successfully opened video writer with codec {fourcc} to file {temp_output}")
    
    except Exception as codec_error:
        print(f"ERROR setting up video codec: {codec_error}")
        return None
    
    # Calculate total number of frames
    total_frames = int(audio_duration * fps)
    print(f"Planning to create {total_frames} frames for {audio_duration:.2f}s of audio")
    
    # Create a mapping of frame number to text to display
    frame_to_text = {}
    for sentence in sentence_timings:
        start_frame = int(sentence['start'] * fps)
        end_frame = int(sentence['end'] * fps)
        for frame_num in range(start_frame, end_frame):
            frame_to_text[frame_num] = sentence['text']
    
    # Get frames from background clip and add text
    print(f"Processing {total_frames} frames with text overlays...")
    failed_frames = 0
    frames_with_text = 0
    
    for frame_num in range(total_frames):
        # Get the timestamp for this frame
        timestamp = frame_num / fps
        
        # Get the frame from the background clip
        try:
            bg_frame = bg_clip.get_frame(timestamp)
            
            # Convert from float [0-1] to uint8 [0-255] if necessary
            if bg_frame.dtype != np.uint8:
                bg_frame = (bg_frame * 255).astype(np.uint8)
            
            # Ensure the frame has the right shape
            if bg_frame.shape[0] != frame_height or bg_frame.shape[1] != frame_width:
                print(f"WARNING: Frame size mismatch. Expected {frame_width}x{frame_height}, got {bg_frame.shape[1]}x{bg_frame.shape[0]}. Resizing...")
                bg_frame = cv2.resize(bg_frame, (frame_width, frame_height))
            
            # Get the text for this frame (if any)
            text = frame_to_text.get(frame_num, "")
            
            # Add text to the frame
            if text:
                frame_with_text = add_text_to_frame(
                    bg_frame, 
                    text, 
                    font_size=font_size, 
                    color=(255, 223, 0)  # RGB for dark yellow
                )
                frames_with_text += 1
            else:
                frame_with_text = bg_frame
            
            # Convert RGB to BGR for OpenCV
            frame_with_text = cv2.cvtColor(frame_with_text, cv2.COLOR_RGB2BGR)
            
            # Write the frame
            out.write(frame_with_text)
            
            # Print progress every 30 frames (about every second)
            if frame_num % 30 == 0:
                print(f"Processed {frame_num}/{total_frames} frames ({frame_num/total_frames*100:.1f}%)")
        
        except Exception as e:
            print(f"ERROR processing frame {frame_num}: {e}")
            # Create a black frame as fallback
            black_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
            out.write(black_frame)
            failed_frames += 1
    
    # Release the video writer
    out.release()
    print(f"OpenCV text video saved to {temp_output}")
    print(f"Frames with text: {frames_with_text}/{total_frames} ({frames_with_text/total_frames*100:.1f}%)")
    print(f"Failed frames: {failed_frames}/{total_frames} ({failed_frames/total_frames*100:.1f}%)")
    
    # Check if we have a reasonable number of frames with text
    if frames_with_text < total_frames * 0.1 and sentence_timings:
        print("WARNING: Very few frames have text overlays. Text might not be visible in the video.")
    
    # Convert back to MoviePy clip (without audio)
    try:
        print(f"Loading final video from {temp_output}")
        text_video = VideoFileClip(temp_output)
        print(f"Video loaded: duration={text_video.duration:.2f}s, size={text_video.size}")
        return text_video
    except Exception as e:
        print(f"ERROR loading the OpenCV text video: {e}")
        return None

def create_content_video(text, time_points, output_filename, audio_path=None):
    """Create a video with sentences synchronized to audio timing"""
    content_video_path = os.path.join(OUTPUT_DIR, output_filename)
    
    try:
        # Get audio details
        audio_duration = 0
        if audio_path:
            audio_duration = get_audio_duration(audio_path)
            if audio_duration:
                print(f"Audio duration: {audio_duration:.2f}s")
        
        if not audio_duration and time_points:
            audio_duration = time_points[-1]['end_time']
            print(f"Using calculated audio duration: {audio_duration:.2f}s")
        
        if not audio_duration:
            print("Could not determine audio duration. Using default of 60 seconds.")
            audio_duration = 60
        
        # Split text into sentences and find timings
        sentences = split_text_into_sentences(text)
        print(f"Processing {len(sentences)} sentences")
        
        # Match sentences with their timings
        sentence_timings = []
        current_sentence = 0
        sentence_start = 0
        
        # For improved debugging, print the sentence we're trying to match
        if sentences:
            print(f"First sentence to match: '{sentences[0]}'")
        
        # Identify sentences in the text
        for i, word_info in enumerate(time_points):
            word = word_info['word']
            # Check if we've reached the end of a sentence
            if (word.endswith('.') or word.endswith('!') or word.endswith('?') or 
                i == len(time_points) - 1):
                if current_sentence < len(sentences):
                    start_time = time_points[sentence_start]['start_time']
                    end_time = word_info['end_time']
                    
                    # For slow speech rates, extend display time slightly past the audio
                    # to give more reading time
                    if start_time == 0:  # First sentence
                        # Start slightly before audio (if possible)
                        display_start = max(0, start_time - 0.5)
                    else:
                        display_start = start_time
                    
                    # For beginner level, keep text on screen longer
                    speech_rate = ENGLISH_LEVEL_RATES.get('beginner', 0.3)  # Default to beginner rate
                    if speech_rate <= 0.4:
                        # Add extra time after the word is spoken
                        display_end = end_time + 1.0  # Add 1 second for very slow speech
                    else:
                        display_end = end_time
                    
                    sentence_timings.append({
                        'text': sentences[current_sentence],
                        'start': display_start,
                        'end': display_end
                    })
                    print(f"Matched sentence {current_sentence+1}: '{sentences[current_sentence]}'")
                    print(f"  Time: {display_start:.2f}s - {display_end:.2f}s (Duration: {display_end-display_start:.2f}s)")
                    
                    current_sentence += 1
                    sentence_start = i + 1
        
        # Fill in any missing sentences with estimated timings
        if current_sentence < len(sentences):
            print(f"Warning: {len(sentences) - current_sentence} sentences could not be matched with word timings")
            last_end = time_points[-1]['end_time'] if time_points else 0
            
            # For slower speech rates, allow more time per sentence
            speech_rate = ENGLISH_LEVEL_RATES.get('beginner', 0.3)
            seconds_per_sentence = 5.0 / speech_rate  # Scale up for slower speech
            
            for i in range(current_sentence, len(sentences)):
                sentence_length = len(sentences[i])
                # Adjust duration based on sentence length
                sentence_duration = max(3, min(10, sentence_length / 10)) * (1.0 / speech_rate)
                
                sentence_timings.append({
                    'text': sentences[i],
                    'start': last_end,
                    'end': last_end + sentence_duration
                })
                print(f"Estimated timing for sentence {i+1}: '{sentences[i]}'")
                print(f"  Time: {last_end:.2f}s - {last_end + sentence_duration:.2f}s (Duration: {sentence_duration:.2f}s)")
                
                last_end += sentence_duration
        
        # STEP 1: Create background clip with proper fps
        print("Creating background video...")
        bg_clip = create_bg_video(audio_duration)
        
        # STEP 2: Create text overlays using OpenCV
        # This completely replaces the previous TextClip approach
        final_content = create_opencv_text_video(bg_clip, sentence_timings, audio_duration)
        
        # If OpenCV method failed, fall back to a simple colored clip
        if final_content is None:
            print("OpenCV text overlay failed. Using solid color background...")
            final_content = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), 
                                     color=(0, 0, 0)).set_duration(audio_duration)
        
        # STEP 3: Add audio to the final content
        if audio_path and os.path.exists(audio_path):
            try:
                audio = AudioFileClip(audio_path)
                final_content = final_content.set_audio(audio)
                print(f"Added audio to content: {audio_path}")
            except Exception as audio_error:
                print(f"Error adding audio to content: {audio_error}")
        
        # Save the content video
        print(f"Saving content video to {content_video_path}")
        try:
            final_content.write_videofile(content_video_path, fps=30, codec='libx264',
                                     logger=None, verbose=False)
            print(f"Content video saved successfully to {content_video_path}")
            return content_video_path
        except Exception as save_error:
            print(f"Error saving content video: {save_error}")
            # Try to save with a different name
            fallback_path = os.path.join(OUTPUT_DIR, "simple_" + output_filename)
            print(f"Trying to save to alternative path: {fallback_path}")
            try:
                final_content.write_videofile(fallback_path, fps=30, codec='libx264',
                                         logger=None, verbose=False)
                print(f"Content video saved successfully to alternative path: {fallback_path}")
                return fallback_path
            except Exception as alt_save_error:
                print(f"Could not save content video to alternative path: {alt_save_error}")
                raise  # Re-raise to be caught by outer try-except
    
    except Exception as e:
        print(f"Error creating content video: {e}")
        # Create a simple fallback with just a black background
        try:
            print("Creating color-only fallback video...")
            # Use a tuple for black color instead of the constant
            fallback = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), 
                               color=(0, 0, 0)).set_duration(audio_duration)
            
            if audio_path and os.path.exists(audio_path):
                try:
                    fallback_audio = AudioFileClip(audio_path)
                    fallback = fallback.set_audio(fallback_audio)
                    print("Added audio to fallback video")
                except Exception as audio_error:
                    print(f"Could not add audio to fallback: {audio_error}")
            
            # Write the fallback video
            fallback_path = os.path.join(OUTPUT_DIR, "fallback_" + output_filename)
            print(f"Saving fallback video to {fallback_path}")
            fallback.write_videofile(fallback_path, fps=30, codec='libx264', logger=None, verbose=False)
            print(f"Fallback video saved successfully to {fallback_path}")
            return fallback_path
            
        except Exception as fallback_error:
            print(f"Could not create fallback video: {fallback_error}")
            # Create an absolute last resort - a 1-second black clip
            try:
                print("Creating last resort fallback...")
                # Use a tuple for black color
                last_resort = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), 
                                      color=(0, 0, 0)).set_duration(1)
                last_resort_path = os.path.join(OUTPUT_DIR, "error_" + output_filename)
                last_resort.write_videofile(last_resort_path, fps=30, codec='libx264', logger=None, verbose=False)
                print(f"Last resort video saved to {last_resort_path}")
                return last_resort_path
            except Exception as last_error:
                print(f"All fallback methods failed: {last_error}")
                return None

def compose_final_video(content_video_path, audio_path, output_filename):
    """Compose the final video with intro, content, outro and background music"""
    try:
        # Validate content video path
        if not content_video_path:
            print("Content video path is None. Cannot compose final video.")
            return None
            
        if not os.path.exists(content_video_path):
            print(f"Content video not found at path: {content_video_path}")
            
            # Try to find any video files in the output directory as a fallback
            fallback_videos = [f for f in os.listdir(OUTPUT_DIR) 
                              if f.endswith('.mp4') and (f.startswith('fallback_') or f.startswith('error_'))]
            
            if fallback_videos:
                # Use the most recent fallback video
                fallback_videos.sort(key=lambda f: os.path.getmtime(os.path.join(OUTPUT_DIR, f)), reverse=True)
                content_video_path = os.path.join(OUTPUT_DIR, fallback_videos[0])
                print(f"Using fallback video instead: {content_video_path}")
            else:
                print("No fallback videos found. Cannot compose final video.")
                return None
        
        # Load video clips
        try:
            intro = VideoFileClip(INTRO_VIDEO)
            content = VideoFileClip(content_video_path)
            outro = VideoFileClip(OUTRO_VIDEO)
            
            print(f"Video clips loaded successfully:")
            print(f"- Intro: {intro.duration:.2f}s, size={intro.size}")
            print(f"- Content: {content.duration:.2f}s, size={content.size}")
            print(f"- Outro: {outro.duration:.2f}s, size={outro.size}")
        except Exception as clip_error:
            print(f"Error loading video clips: {clip_error}")
            return content_video_path  # Just return the content video as is
        
        # Ensure content has correct audio
        if audio_path and os.path.exists(audio_path):
            try:
                content_audio = AudioFileClip(audio_path)
                content = content.set_audio(content_audio)
                print(f"Added audio to content: {audio_path}, duration={content_audio.duration:.2f}s")
            except Exception as audio_error:
                print(f"Error adding audio to content: {audio_error}")
        
        # Load background music for intro/outro
        try:
            if not os.path.exists(BACKGROUND_MUSIC):
                print(f"ERROR: Background music file not found at: {BACKGROUND_MUSIC}")
                # Use an alternative approach without background music
                final = concatenate_videoclips([intro, content, outro])
            else:
                print(f"Loading background music from: {BACKGROUND_MUSIC}")
                
                # Try using pydub first to check if the audio file is valid
                try:
                    audio_check = pydub.AudioSegment.from_file(BACKGROUND_MUSIC)
                    print(f"Background music duration via pydub: {audio_check.duration_seconds:.2f}s")
                except Exception as pydub_error:
                    print(f"Warning: Could not validate audio file with pydub: {pydub_error}")
                
                # Load with MoviePy
                try:
                    # Try with explicit codec options
                    bg_music = AudioFileClip(BACKGROUND_MUSIC, buffersize=50000, fps=44100)
                    print(f"Background music loaded successfully: duration={bg_music.duration:.2f}s")
                except Exception as audio_load_error:
                    print(f"Failed to load audio with custom params: {audio_load_error}")
                    # Try default loading
                    bg_music = AudioFileClip(BACKGROUND_MUSIC)
                    print(f"Background music loaded with default parameters: duration={bg_music.duration:.2f}s")
                
                # Loop if needed
                total_duration = intro.duration + content.duration + outro.duration
                print(f"Total video duration: {total_duration:.2f}s")
                
                if bg_music.duration < total_duration:
                    print(f"Background music ({bg_music.duration:.2f}s) shorter than video ({total_duration:.2f}s), creating loops...")
                    
                    # Manually create a looped audio by concatenating the clip multiple times
                    loops_needed = math.ceil(total_duration / bg_music.duration)
                    print(f"Creating {loops_needed} loops of the background music")
                    
                    # Create list of audio clips
                    audio_loops = [bg_music] * loops_needed
                    
                    # Concatenate the audio clips
                    from moviepy.editor import concatenate_audioclips
                    looped_bg_music = concatenate_audioclips(audio_loops)
                    
                    # Trim to the exact duration needed
                    bg_music = looped_bg_music.subclip(0, total_duration)
                    print(f"Created looped background music with duration: {bg_music.duration:.2f}s")
                else:
                    print(f"Trimming background music from {bg_music.duration:.2f}s to {total_duration:.2f}s")
                    bg_music = bg_music.subclip(0, total_duration)
                
                # Set volume
                original_volume = bg_music.volumex(1.0)  # Save original volume version
                bg_music = bg_music.volumex(BACKGROUND_MUSIC_VOLUME)
                print(f"Set background music volume to {BACKGROUND_MUSIC_VOLUME*100:.0f}%")
                
                # Add music to intro/outro with explicit new clips to avoid reference issues
                print("Creating new intro with background music...")
                intro_with_music = intro.set_audio(bg_music.subclip(0, intro.duration))
                
                print("Creating new outro with background music...")
                outro_with_music = outro.set_audio(bg_music.subclip(
                    intro.duration + content.duration,
                    total_duration
                ))
                
                # Create a separate audio debug clip to verify music is working
                try:
                    debug_clip = ColorClip(color=(0,0,0), size=(640, 360), duration=5)
                    debug_clip = debug_clip.set_audio(original_volume.subclip(0, 5))
                    debug_path = os.path.join(OUTPUT_DIR, "audio_debug.mp4")
                    debug_clip.write_videofile(debug_path, fps=30, codec='libx264', audio_codec='aac',
                                              logger=None, verbose=False)
                    print(f"Created audio debug clip: {debug_path}")
                except Exception as debug_error:
                    print(f"Error creating audio debug clip: {debug_error}")
                
                # Concatenate with the new audio-enhanced clips
                print("Concatenating clips with background music...")
                final = concatenate_videoclips([intro_with_music, content, outro_with_music])
                
                print(f"Successfully added background music to intro and outro")
        except Exception as music_error:
            print(f"ERROR adding background music: {music_error}")
            # Continue without background music
            print("Falling back to no background music")
            final = concatenate_videoclips([intro, content, outro])
        
        # Save the final video
        final_path = os.path.join(OUTPUT_DIR, "final_" + output_filename)
        print(f"Saving final video to {final_path}")
        try:
            final.write_videofile(final_path, fps=30, codec='libx264',
                                logger=None, verbose=False)
            
            print(f"Final video saved successfully to {final_path}")
            return final_path
            
        except Exception as save_error:
            print(f"Error saving final video: {save_error}")
            return content_video_path
        
    except Exception as e:
        print(f"Error composing final video: {e}")
        return content_video_path 

def create_bg_video(duration):
    """Create a background video by using a random video from the background_videos folder"""
    try:
        # Get all video files from the background videos directory
        bg_files = glob.glob(os.path.join(BACKGROUND_VIDEOS_DIR, '*.mp4'))
        print(f"Found {len(bg_files)} background videos in {BACKGROUND_VIDEOS_DIR}")
        
        if not bg_files:
            print(f"WARNING: No background videos found in {BACKGROUND_VIDEOS_DIR}. Using solid color background.")
            return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=BACKGROUND_COLOR).set_duration(duration)
        
        # Select a random background video
        bg_file = random.choice(bg_files)
        print(f"Selected background video: {os.path.basename(bg_file)} (full path: {bg_file})")
        
        if not os.path.exists(bg_file):
            print(f"ERROR: Selected background video does not exist at path: {bg_file}")
            return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=BACKGROUND_COLOR).set_duration(duration)
        
        try:
            # Try to directly use the video file as a clip
            print(f"Loading video file: {bg_file}")
            bg_clip = VideoFileClip(bg_file)
            
            # Resize to target dimensions while maintaining aspect ratio
            print(f"Resizing video from {bg_clip.size} to height={VIDEO_HEIGHT}")
            bg_clip = bg_clip.resize(height=VIDEO_HEIGHT)
            
            # If the video is shorter than needed, loop it manually
            if bg_clip.duration < duration:
                print(f"Background video duration ({bg_clip.duration:.2f}s) is shorter than needed ({duration:.2f}s). Looping...")
                # Calculate how many loops we need
                loops = math.ceil(duration / bg_clip.duration)
                # Create a list of the same clip multiple times
                clips = [bg_clip] * loops
                # Concatenate all clips
                bg_clip = concatenate_videoclips(clips)
                # Trim to exact duration
                bg_clip = bg_clip.subclip(0, duration)
            else:
                # Trim if longer than needed
                bg_clip = bg_clip.subclip(0, duration)
            
            print(f"Background video prepared: duration={bg_clip.duration:.2f}s, fps={bg_clip.fps}, size={bg_clip.size}")
            return bg_clip
            
        except Exception as direct_error:
            print(f"ERROR using direct video method: {direct_error}")
            print("Falling back to frame extraction method...")
            
            # Alternative method using frame extraction
            print(f"Opening video with OpenCV: {bg_file}")
            cap = cv2.VideoCapture(bg_file)
            if not cap.isOpened():
                print(f"ERROR: OpenCV could not open video file: {bg_file}")
                raise ValueError(f"Could not open video file: {bg_file}")
            
            # Get video properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            original_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            total_duration = original_frame_count / fps if fps > 0 else 0
            
            print(f"Original video: {width}x{height}, {fps} fps, {original_frame_count} frames, {total_duration:.2f}s")
            
            # Target framerate for smooth playback
            target_fps = 30
            
            # Calculate how many frames we need for the target duration at the target FPS
            required_frames = int(duration * target_fps)
            
            # Calculate frame interval for extraction
            # If the video is shorter, we'll extract frames with overlap for looping
            if total_duration < duration:
                frame_interval = original_frame_count / required_frames
            else:
                # Use first N seconds only
                usable_frames = min(original_frame_count, int(duration * fps))
                frame_interval = usable_frames / required_frames
            
            print(f"Extracting {required_frames} frames at interval {frame_interval:.2f} frames")
            
            frames = []
            frame_count = 0
            
            while frame_count < required_frames:
                target_frame_index = int(frame_count * frame_interval) % original_frame_count
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_index)
                ret, frame = cap.read()
                
                if not ret:
                    print(f"WARNING: Failed to read frame at index {target_frame_index}")
                    break
                
                # Convert BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize frame to target dimensions
                target_width = int(VIDEO_WIDTH)
                target_height = int(VIDEO_HEIGHT)
                
                try:
                    # Try using PIL for resizing (better quality)
                    pil_image = Image.fromarray(frame)
                    
                    # Resize maintaining aspect ratio
                    aspect = width / height
                    if aspect > VIDEO_WIDTH / VIDEO_HEIGHT:  # wider than target
                        resize_width = target_width
                        resize_height = int(resize_width / aspect)
                    else:  # taller than target
                        resize_height = target_height
                        resize_width = int(resize_height * aspect)
                    
                    # Use Lanczos resampling if available, otherwise fallback
                    if hasattr(Image, 'Resampling') and hasattr(Image.Resampling, 'LANCZOS'):
                        resized_image = pil_image.resize((resize_width, resize_height), Image.Resampling.LANCZOS)
                    elif hasattr(Image, 'LANCZOS'):
                        resized_image = pil_image.resize((resize_width, resize_height), Image.LANCZOS)
                    else:
                        resized_image = pil_image.resize((resize_width, resize_height))
                    
                    # Create a black canvas of target size
                    canvas = Image.new('RGB', (target_width, target_height), (0, 0, 0))
                    
                    # Paste resized image in center
                    paste_x = (target_width - resize_width) // 2
                    paste_y = (target_height - resize_height) // 2
                    canvas.paste(resized_image, (paste_x, paste_y))
                    
                    # Convert back to numpy array
                    frame = np.array(canvas)
                
                except Exception as pil_error:
                    print(f"PIL resize error: {pil_error}")
                    # Fallback to cv2 resize
                    frame = cv2.resize(frame, (target_width, target_height))
                
                frames.append(frame)
                frame_count += 1
                
                if frame_count % 30 == 0:
                    print(f"Extracted {frame_count}/{required_frames} frames")
            
            cap.release()
            
            if not frames:
                print("ERROR: No frames extracted from video")
                raise ValueError("No frames extracted from video")
            
            # Create clip from frames with specified fps for smooth playback
            bg_clip = ImageSequenceClip(frames, fps=target_fps)
            
            # Save background only clip for debugging
            try:
                bg_debug_path = os.path.join(OUTPUT_DIR, "background_only.mp4")
                bg_clip.write_videofile(bg_debug_path, codec='libx264', fps=target_fps, audio=False, verbose=False, logger=None)
                print(f"Saved background-only debug video to {bg_debug_path}")
            except Exception as save_error:
                print(f"Could not save background debug video: {save_error}")
            
            print(f"Created background clip using {len(frames)} frames at {target_fps} fps")
            return bg_clip
            
    except Exception as e:
        print(f"ERROR creating background video: {e}")
        # Fallback to solid color background
        print("Using solid color background as fallback")
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=BACKGROUND_COLOR).set_duration(duration)

def create_shorts_video(content_video_path, audio_path, output_filename):
    """Create a vertical video suitable for YouTube Shorts from the content video"""
    try:
        shorts_video_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Load the content video
        if not os.path.exists(content_video_path):
            print(f"Content video not found at path: {content_video_path}")
            return None
            
        content = VideoFileClip(content_video_path)
        print(f"Loaded content video: {content_video_path}, duration={content.duration:.2f}s, size={content.size}")
        
        # Check if audio exists and load it
        audio = None
        if audio_path and os.path.exists(audio_path):
            try:
                audio = AudioFileClip(audio_path)
                print(f"Loaded audio: {audio_path}, duration={audio.duration:.2f}s")
            except Exception as audio_error:
                print(f"Error loading audio: {audio_error}")
        
        # Determine target duration (limited to SHORTS_MAX_DURATION)
        target_duration = min(content.duration, SHORTS_MAX_DURATION)
        print(f"Target Shorts duration: {target_duration:.2f}s")
        
        # Create a vertical background with solid color (RGB format for compatibility)
        bg_color = (0, 0, 0)  # Black background
        bg_clip = ColorClip(
            size=(SHORTS_VIDEO_WIDTH, SHORTS_VIDEO_HEIGHT),
            color=bg_color
        ).set_duration(target_duration)
        
        # Trim content to target duration
        if content.duration > target_duration:
            content = content.subclip(0, target_duration)
        
        # Calculate new dimensions while maintaining aspect ratio
        # For vertical video, we'll resize to fit width
        aspect_ratio = content.w / content.h
        new_width = SHORTS_VIDEO_WIDTH
        new_height = int(new_width / aspect_ratio)
        
        # Make sure new dimensions don't exceed the vertical video dimensions
        if new_height > SHORTS_VIDEO_HEIGHT:
            # If height would be too large, constrain by height instead
            new_height = SHORTS_VIDEO_HEIGHT
            new_width = int(new_height * aspect_ratio)
        
        print(f"Resizing content from {content.size} to {new_width}x{new_height}")
        
        # Resize the content
        resized_content = content.resize(width=new_width, height=new_height)
        
        # Position the content in the center of the vertical video
        x_position = (SHORTS_VIDEO_WIDTH - new_width) // 2
        y_position = (SHORTS_VIDEO_HEIGHT - new_height) // 2
        
        print(f"Positioning content at x={x_position}, y={y_position}")
        
        # Create the composite video with explicit size parameter
        print("Creating composite video...")
        final_clip = CompositeVideoClip(
            [bg_clip, resized_content.set_position((x_position, y_position))],
            size=(SHORTS_VIDEO_WIDTH, SHORTS_VIDEO_HEIGHT)
        ).set_duration(target_duration)
        
        # Add audio if available
        if audio:
            # Trim audio to match video duration
            if audio.duration > target_duration:
                audio = audio.subclip(0, target_duration)
            final_clip = final_clip.set_audio(audio)
        
        # Write the final shorts video
        print(f"Saving YouTube Shorts video to {shorts_video_path}")
        try:
            final_clip.write_videofile(
                shorts_video_path,
                fps=30,
                codec='libx264',
                logger=None,
                verbose=False
            )
            print(f"YouTube Shorts video saved successfully to {shorts_video_path}")
            return shorts_video_path
        except Exception as write_error:
            print(f"Error writing Shorts video file: {write_error}")
            
            # Try an alternative approach if the first one fails
            print("Trying alternative method...")
            try:
                # Create a simple black background with the content text
                simple_clip = ColorClip(
                    size=(SHORTS_VIDEO_WIDTH, SHORTS_VIDEO_HEIGHT),
                    color=bg_color
                ).set_duration(target_duration)
                
                if audio:
                    simple_clip = simple_clip.set_audio(audio)
                
                # Write the simple clip
                simple_path = os.path.join(OUTPUT_DIR, "simple_" + output_filename)
                simple_clip.write_videofile(
                    simple_path,
                    fps=30,
                    codec='libx264',
                    logger=None,
                    verbose=False
                )
                print(f"Simple Shorts video saved to {simple_path}")
                return simple_path
            except Exception as alt_error:
                print(f"Alternative method failed: {alt_error}")
                return None
        
    except Exception as e:
        print(f"Error creating YouTube Shorts video: {e}")
        import traceback
        traceback.print_exc()
        return None 