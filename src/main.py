import os
import argparse
import time
from src.tts import generate_speech
from src.video_generator import create_content_video, compose_final_video, create_shorts_video
from src.youtube_uploader import upload_video
from src.config import OUTPUT_DIR

def process_input_file(input_file_path):
    """Process the input text file to extract text and parameters"""
    with open(input_file_path, 'r') as f:
        content = f.read().strip()
    
    # Split the content by lines
    lines = content.split('\n')
    
    # Extract parameters (if any)
    parameters = {}
    text_lines = []
    
    for line in lines:
        # Check if line is a parameter (format: #param: value)
        if line.startswith('#'):
            param_parts = line[1:].split(':', 1)
            if len(param_parts) == 2:
                key = param_parts[0].strip()
                value = param_parts[1].strip()
                parameters[key] = value
        else:
            # Regular text line
            text_lines.append(line)
    
    # Join text lines back into one string
    text = '\n'.join(text_lines).strip()
    
    return text, parameters

def generate_video(input_file_path, output_video_name=None, upload=False, video_title=None, generate_shorts=False):
    """Generate a video from input text file and optionally upload to YouTube"""
    # Process input file
    text, parameters = process_input_file(input_file_path)
    
    # Extract parameters with defaults
    english_level = parameters.get('english_level', 'intermediate')
    voice_name = parameters.get('voice', 'en-US-Neural2-F')
    
    # Generate timestamped filename using current timestamp if not provided
    timestamp = int(time.time())
    
    if not output_video_name:
        output_video_name = f"video_{timestamp}.mp4"
    
    # Generate audio with speech-to-text
    print(f"Generating speech for text... (English level: {english_level})")
    audio_filename = f"audio_{timestamp}.mp3"
    time_points, audio_path = generate_speech(text, audio_filename, english_level, voice_name)
    
    # Create content video with synchronized text
    print("Creating content video with synchronized text...")
    content_video_filename = f"content_{timestamp}.mp4"
    content_video_path = create_content_video(text, time_points, content_video_filename, audio_path)
    
    # Compose final video with intro, content, outro and background music
    print("Composing final video with intro, content, outro and background music...")
    final_video_path = compose_final_video(content_video_path, audio_path, output_video_name)
    
    print(f"Video generated successfully: {final_video_path}")
    
    # Generate YouTube Shorts version if requested
    shorts_video_path = None
    if generate_shorts:
        print("Generating YouTube Shorts version...")
        shorts_filename = f"shorts_{timestamp}.mp4"
        shorts_video_path = create_shorts_video(content_video_path, audio_path, shorts_filename)
        print(f"YouTube Shorts video generated successfully: {shorts_video_path}")
    
    # Upload to YouTube if requested
    if upload:
        print("Uploading video to YouTube...")
        
        # Use video title from parameters, argument, or generate from input filename
        if not video_title:
            video_title = parameters.get('title', os.path.splitext(os.path.basename(input_file_path))[0])
        
        # Extract description and tags from parameters if available
        description = parameters.get('description', None)
        tags_str = parameters.get('tags', None)
        tags = tags_str.split(',') if tags_str else None
        
        # Upload the regular video
        youtube_id = upload_video(
            final_video_path, 
            title=video_title,
            description=description,
            tags=tags
        )
        
        if youtube_id:
            print(f"Video uploaded successfully to YouTube: https://www.youtube.com/watch?v={youtube_id}")
            
            # If Shorts version was generated, upload it too
            if shorts_video_path:
                # Update description to include link to full video
                shorts_description = f"Check out the full video: https://www.youtube.com/watch?v={youtube_id}"
                if description:
                    shorts_description = f"{description}\n\n{shorts_description}"
                
                shorts_title = f"{video_title} #Shorts"
                shorts_youtube_id = upload_video(
                    shorts_video_path,
                    title=shorts_title,
                    description=shorts_description,
                    tags=tags,
                    is_shorts=True
                )
                
                if shorts_youtube_id:
                    print(f"Shorts video uploaded successfully to YouTube: https://www.youtube.com/watch?v={shorts_youtube_id}")
                else:
                    print("Failed to upload Shorts video to YouTube.")
        else:
            print("Failed to upload video to YouTube.")
    
    result = {"main_video": final_video_path}
    if generate_shorts and shorts_video_path:
        result["shorts_video"] = shorts_video_path
    
    return result

def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description='Generate YouTube videos from text.')
    parser.add_argument('input_file', help='Path to the input text file')
    parser.add_argument('--output', '-o', help='Output video filename')
    parser.add_argument('--upload', '-u', action='store_true', help='Upload to YouTube after generation')
    parser.add_argument('--title', '-t', help='YouTube video title (only used with --upload)')
    parser.add_argument('--shorts', '-s', action='store_true', help='Generate a YouTube Shorts version')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Generate video
    generate_video(args.input_file, args.output, args.upload, args.title, args.shorts)

if __name__ == "__main__":
    main() 