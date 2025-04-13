import os
import argparse
import time
from src.tts import generate_speech
from src.video_generator import create_content_video, compose_final_video, create_shorts_video
from src.youtube_uploader import upload_video
from src.config import OUTPUT_DIR, VOICE_MAPPINGS, DEFAULT_POLLY_VOICE
from src.translator import translate_template_file, get_language_voice
from src.thumbnail_generator import generate_thumbnail

def process_input_file(input_file_path):
    """Process the input text file to extract text and parameters"""
    with open(input_file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    # Split the content by lines
    lines = content.split('\n')
    
    # Extract parameters (if any)
    parameters = {}
    text_lines = []
    
    # Track if we're in a parameter block or content block
    current_param = None
    current_value = []
    in_content_block = False
    
    for line in lines:
        # Check if line is a new parameter (format: #param: value)
        if line.startswith('#'):
            # If we were processing a previous parameter, save it
            if current_param:
                parameters[current_param] = '\n'.join(current_value).strip()
                current_param = None
                current_value = []
            
            param_parts = line[1:].split(':', 1)
            if len(param_parts) == 2:
                current_param = param_parts[0].strip()
                
                # Special handling for content tag - this starts the actual video content
                if current_param == 'content':
                    in_content_block = True
                    # Start with any content on the same line
                    if param_parts[1].strip():
                        text_lines.append(param_parts[1].strip())
                    current_param = None
                    current_value = []
                else:
                    current_value = [param_parts[1].strip()]
        elif current_param and not line.strip():
            # Empty line marks the end of a parameter value
            parameters[current_param] = '\n'.join(current_value).strip()
            current_param = None
            current_value = []
        elif current_param:
            # Continue adding to the current parameter
            current_value.append(line)
        elif in_content_block:
            # In content block, add to text lines
            text_lines.append(line)
    
    # Handle any final parameter
    if current_param:
        parameters[current_param] = '\n'.join(current_value).strip()
    
    # Join text lines back into one string
    text = '\n'.join(text_lines).strip()
    
    return text, parameters

def generate_video(input_file_path, output_video_name=None, upload=False, video_title=None, generate_shorts=False, language='english'):
    """Generate a video from input text file and optionally upload to YouTube and/or TikTok"""
    print(f"Generating video in {language}...")
    
    # Translate template if needed
    if language.lower() != 'english':
        print(f"Translating template to {language}...")
        _, translated_template = translate_template_file(input_file_path, language)
        if translated_template:
            input_file_path = translated_template
            print(f"Using translated template: {input_file_path}")
        else:
            print(f"Failed to translate template to {language}. Using original template.")
    
    # Process input file
    text, parameters = process_input_file(input_file_path)
    
    # Extract parameters with defaults
    english_level = parameters.get('english_level', 'intermediate')
    
    # Get voice based on language
    voice_name = parameters.get('voice', get_language_voice(language))
    
    # Make sure voice_name is a valid Amazon Polly voice
    if voice_name and voice_name.startswith('en-US-Neural') and voice_name in VOICE_MAPPINGS:
        # We got a Google TTS voice, map it to Amazon Polly
        polly_voice = VOICE_MAPPINGS.get(voice_name, DEFAULT_POLLY_VOICE)
        print(f"Mapped Google TTS voice '{voice_name}' to Amazon Polly voice '{polly_voice}'")
    else:
        # Assume it's already a Polly voice or use the default for the language
        polly_voice = voice_name if voice_name else get_language_voice(language)
        print(f"Using Amazon Polly voice: {polly_voice}")
    
    # Generate timestamped filename using current timestamp if not provided
    timestamp = int(time.time())
    
    if not output_video_name:
        lang_suffix = f"_{language.lower()}" if language.lower() != 'english' else ""
        output_video_name = f"video{lang_suffix}_{timestamp}.mp4"
    
    # Generate audio with speech-to-text
    print(f"Generating speech for text... (English level: {english_level}, Voice: {polly_voice}, Language: {language})")
    audio_filename = f"audio_{language.lower()}_{timestamp}.mp3"
    time_points, audio_path = generate_speech(text, audio_filename, english_level, polly_voice)
    
    if not time_points or not audio_path:
        print("Error generating speech. Process aborted.")
        return None
    
    # Create content video with synchronized text
    print("Creating content video with synchronized text...")
    content_video_filename = f"content_{language.lower()}_{timestamp}.mp4"
    
    content_video_path = create_content_video(text, time_points, content_video_filename, audio_path)
    
    # Compose final video with intro, content, outro and background music
    print("Composing final video with intro, content, outro and background music...")
    final_video_path = compose_final_video(content_video_path, audio_path, output_video_name)
    
    print(f"Video generated successfully: {final_video_path}")
    
    # Generate YouTube Shorts version if requested
    shorts_video_path = None
    if generate_shorts:
        print("Generating YouTube Shorts version...")
        shorts_filename = f"shorts_{language.lower()}_{timestamp}.mp4"
        shorts_video_path = create_shorts_video(content_video_path, audio_path, shorts_filename)
        print(f"YouTube Shorts video generated successfully: {shorts_video_path}")
    
    # Upload to YouTube if requested
    thumbnail_path = None
    if upload:
        # Use video title from parameters, argument, or generate from input filename
        if not video_title:
            video_title = parameters.get('title', os.path.splitext(os.path.basename(input_file_path))[0])
        
        # Generate thumbnail for the video
        print("Generating thumbnail for the video...")
        thumbnail_path = generate_thumbnail(video_title, language, use_simple=True)
        if thumbnail_path:
            print(f"Thumbnail generated successfully: {thumbnail_path}")
        else:
            print("Failed to generate thumbnail. Will upload without custom thumbnail.")
        
        print("Uploading video to YouTube...")
        
        # Extract description and tags from parameters if available
        description = parameters.get('description', None)
        tags_str = parameters.get('tags', None)
        tags = tags_str.split(',') if tags_str else None
        
        # Append language information to title if not English
        if language.lower() != 'english':
            video_title = f"{video_title} [{language.title()}]"
        
        # Upload the regular video
        youtube_id = upload_video(
            final_video_path, 
            title=video_title,
            description=description,
            tags=tags,
            thumbnail_path=thumbnail_path
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
                # Generate a separate thumbnail for shorts if needed
                shorts_thumbnail_path = None
                if thumbnail_path:
                    print("Generating thumbnail for Shorts video...")
                    shorts_thumbnail_path = generate_thumbnail(
                        shorts_title, 
                        language,
                        prompt=f"Vertical YouTube Shorts thumbnail, {video_title}, portrait orientation",
                        use_simple=True
                    )
                
                shorts_youtube_id = upload_video(
                    shorts_video_path,
                    title=shorts_title,
                    description=shorts_description,
                    tags=tags,
                    is_shorts=True,
                    thumbnail_path=shorts_thumbnail_path
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
    if thumbnail_path:
        result["thumbnail"] = thumbnail_path
    
    return result

def batch_generate_videos(input_file_path, languages=None, upload=False, generate_shorts=False):
    """Generate videos in multiple languages from a single template file"""
    if not languages:
        languages = ['english']  # Default to English only if no languages specified
    
    results = {}
    
    for language in languages:
        print(f"\n=== Generating {language.title()} version ===\n")
        
        # Generate video with language-specific naming
        lang_suffix = f"_{language.lower()}" if language.lower() != 'english' else ""
        output_name = f"video{lang_suffix}_{int(time.time())}.mp4"
        
        result = generate_video(
            input_file_path, 
            output_video_name=output_name,
            upload=upload,
            generate_shorts=generate_shorts,
            language=language
        )
        
        if result:
            results[language] = result
            print(f"{language.title()} video generated successfully")
        else:
            print(f"Failed to generate {language.title()} video")
    
    return results

def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description='Generate YouTube videos from text.')
    parser.add_argument('input_file', help='Path to the input text file')
    parser.add_argument('--output', '-o', help='Output video filename')
    parser.add_argument('--upload', '-u', action='store_true', help='Upload to YouTube after generation')
    parser.add_argument('--title', '-t', help='Video title (only used with --upload)')
    parser.add_argument('--shorts', '-s', action='store_true', help='Generate a YouTube Shorts version and upload to both YouTube and TikTok')
    parser.add_argument('--language', '-l', help='Target language for the video (english, korean, german, spanish, french)', default='english')
    parser.add_argument('--all-languages', '-a', action='store_true', help='Generate videos in all supported languages')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Generate videos in multiple languages if all-languages flag is set
    if args.all_languages:
        print("Generating videos in all supported languages...")
        languages = ['english', 'korean', 'german', 'spanish', 'french']
        batch_generate_videos(args.input_file, languages, args.upload, args.shorts)
    else:
        # Generate video in the specified language
        generate_video(args.input_file, args.output, args.upload, args.title, args.shorts, args.language)

if __name__ == "__main__":
    main()