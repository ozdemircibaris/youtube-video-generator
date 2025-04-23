import os
import json
import argparse
import sys
import traceback
import uuid
import time
import gc
import multiprocessing

# Multiprocessing ayarlarını başlangıçta yapılandır
# macOS'ta "fork" yerine "spawn" kullanmak daha güvenlidir
multiprocessing.set_start_method('spawn', force=True)

from src.template_parser import parse_template_file
from src.polly_generator import PollyGenerator
from src.video_generator import VideoGenerator
from src.translator import Translator
from src.image_generator import ImageGenerator
from src.youtube_uploader import YouTubeUploader
import src.config as config


def create_env_file():
    """Create a .env file for AWS credentials if it doesn't exist."""
    env_path = ".env"
    
    if not os.path.exists(env_path):
        with open(env_path, 'w') as f:
            f.write("AWS_ACCESS_KEY_ID=\n")
            f.write("AWS_SECRET_ACCESS_KEY=\n")
            f.write("AWS_REGION=us-east-1\n")
            f.write("AZURE_OPENAI_ENDPOINT=\n")
            f.write("AZURE_OPENAI_API_KEY=\n")
            f.write("AZURE_OPENAI_API_VERSION=\n")
            f.write("AZURE_OPENAI_COMPLETION_DEPLOYMENT=\n")
            f.write("SD_API_KEY=\n")
            f.write("SD_AZURE_ENDPOINT=\n")
        print("Created .env file. Please fill in your AWS and Azure OpenAI credentials.")


def save_template_file(template_data, filename):
    """
    Save template data to a file in the correct format.
    
    Args:
        template_data (dict): Template data dictionary
        filename (str): Output filename
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure the destination directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            # Write metadata fields
            for key, value in template_data.items():
                if key != 'content' and key != 'ssml_content' and key != 'images_scenario':
                    f.write(f"#{key}: {value}\n")
            
            # Handle images_scenario specially to preserve original format
            if 'images_scenario' in template_data:
                f.write("\n#images_scenario:\n")
                for section in template_data['images_scenario']:
                    f.write("- section: " + section.get('section', '') + "\n")
                    f.write("  prompt: " + section.get('prompt', '') + "\n")
                    f.write("  description: " + section.get('description', '') + "\n")
                    f.write("\n")
            
            # Write content last (including SSML content)
            if 'content' in template_data:
                f.write(f"\n#content: {template_data['content']}")
                
        print(f"Template file saved successfully to {filename}")
        return True
    except Exception as e:
        print(f"Error saving template file: {e}")
        traceback.print_exc()
        # We don't want to terminate the pipeline here, so we'll still return True
        # This way, even if we can't save the template file, we'll try to process it
        return True


def generate_video_id(template_data):
    """
    Generate a unique ID for the video based on template data and timestamp.
    
    Args:
        template_data (dict): Template data dictionary
        
    Returns:
        str: Unique video ID
    """
    # Extract title or use a fallback
    title = template_data.get('title', 'video')
    
    # Slugify the title (convert to lowercase, replace spaces with dashes)
    slug = title.lower().replace(' ', '-')[:30]
    
    # Clean the slug (remove special characters)
    slug = ''.join(c if c.isalnum() or c == '-' else '' for c in slug)
    
    # Add timestamp for uniqueness (use only seconds portion)
    timestamp = int(time.time()) % 10000
    
    # Generate short uuid (first 8 characters)
    short_uuid = str(uuid.uuid4())[:8]
    
    # Combine for final ID
    video_id = f"{slug}-{timestamp}-{short_uuid}"
    
    return video_id


def setup_project_directories(video_id):
    """
    Set up project directories for the given video ID.
    
    Args:
        video_id (str): Unique video ID
        
    Returns:
        dict: Dictionary with project paths
    """
    # Create main video directory
    video_dir = os.path.join(config.OUTPUT_DIR, video_id)
    os.makedirs(video_dir, exist_ok=True)
    
    # Create section images directory
    section_images_dir = os.path.join(video_dir, "section_images")
    os.makedirs(section_images_dir, exist_ok=True)
    
    # Create language directories
    paths = {
        'video_dir': video_dir,
        'section_images_dir': section_images_dir,
        'languages': {}
    }
    
    # Define supported languages
    languages = {
        'en': 'English',
        'de': 'German',
        'es': 'Spanish',
        'fr': 'French',
        'ko': 'Korean'
    }
    
    # Create directory for each language
    for lang_code, lang_name in languages.items():
        lang_dir = os.path.join(video_dir, lang_code)
        os.makedirs(lang_dir, exist_ok=True)
        
        paths['languages'][lang_code] = {
            'dir': lang_dir,
            'audio': os.path.join(lang_dir, f"speech.mp3"),
            'timings': os.path.join(lang_dir, f"timings.json"),
            'video': os.path.join(lang_dir, f"video.mp4"),
            'thumbnail': os.path.join(lang_dir, f"thumbnail.jpg"),
            'shorts': os.path.join(lang_dir, f"shorts.mp4")  # Add path for Shorts video
        }
    
    print(f"Created project directories for video ID: {video_id}")
    return paths


def generate_section_images(template_data, paths, language_code='en'):
    """
    Generate images for each section based on template data.
    
    Args:
        template_data (dict): Template data with images_scenario
        paths (dict): Dictionary with project paths
        language_code (str): Language code for file naming
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if SD credentials are available
        if not os.getenv('SD_API_KEY') or not os.getenv('SD_AZURE_ENDPOINT'):
            print("Stable Diffusion credentials not found. Cannot generate section images.")
            return False
            
        # Get images_scenario data
        images_scenario = template_data.get('images_scenario')
        if not images_scenario:
            print(f"No images_scenario found in template for language {language_code}")
            return False
            
        # Get section images directory from paths
        section_images_dir = paths['section_images_dir']
        
        # Initialize image generator
        image_gen = ImageGenerator()
        
        print(f"\n--- Generating section images for {language_code} ---")
        
        # Generate images for each section
        for section_data in images_scenario:
            section_name = section_data.get('section')
            prompt = section_data.get('prompt')
            
            if not section_name or not prompt:
                print(f"Skip section due to missing data: {section_data}")
                continue
                
            # Set output path
            section_image_path = os.path.join(section_images_dir, f"{section_name}_{language_code}.jpg")
            
            print(f"Generating image for section: {section_name}")
            
            # Generate image using Stable Diffusion
            result = image_gen.generate_section_image(
                prompt, 
                section_image_path, 
                section_name
            )
            
            if result:
                print(f"Section image generated successfully at {section_image_path}")
            else:
                print(f"Failed to generate section image for {section_name}")
        
        return True
            
    except Exception as e:
        print(f"Error generating section images: {e}")
        traceback.print_exc()
        return False


def process_template(template_path, paths, language_code='en', is_shorts=False):
    """
    Process a single template file to generate a video.
    
    Args:
        template_path (str): Path to the template file
        paths (dict): Dictionary with project paths
        language_code (str): Language code for file naming (default: 'en')
        is_shorts (bool): Whether to also generate a YouTube Shorts format video
        
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n--- Processing template: {template_path} for language {language_code} ---")
    
    try:
        # Parse template file
        template_data = parse_template_file(template_path)
        
        if not template_data:
            print("Failed to parse template file.")
            raise ValueError("Template parsing failed")
        
        # Extract needed data
        ssml_content = template_data.get('ssml_content')
        voice_id = template_data.get('voice', 'Matthew')
        
        if not ssml_content:
            print("No SSML content found in template.")
            raise ValueError("SSML content missing")
            
        # Map language code to language name
        language_names = {
            'en': 'English',
            'de': 'German',
            'es': 'Spanish',
            'fr': 'French',
            'ko': 'Korean'
        }
        
        # Get the language name from the code, default to English if not found
        language_name = language_names.get(language_code, 'English')
        
        # Replace {language} placeholders in SSML content
        if '{language}' in ssml_content:
            print(f"Replacing {{language}} placeholders with '{language_name}'")
            ssml_content = ssml_content.replace('{language}', language_name)
        
        # Get file paths for this language
        lang_paths = paths['languages'][language_code]
        audio_output_path = lang_paths['audio']
        word_timings_path = lang_paths['timings']
        standard_video_output_path = lang_paths['video']
        shorts_video_output_path = lang_paths['shorts']
        section_images_dir = paths['section_images_dir']
        
        # Check if we're only processing shorts and can reuse existing standard video
        if is_shorts and os.path.exists(standard_video_output_path) and os.path.exists(word_timings_path):
            print(f"\n--- Using existing standard video to generate Shorts for {language_code} ---")
            
            # Create a shorts generator that will reuse the existing content
            shorts_gen = VideoGenerator(language_code, is_shorts=True, reuse_content=True)
            shorts_result = shorts_gen.create_shorts_from_standard(
                standard_video_output_path,
                shorts_video_output_path,
                word_timings_path
            )
            
            # Clean up resources after generating shorts video
            del shorts_gen
            gc.collect()
            
            if not shorts_result:
                print("Failed to create Shorts video from existing standard video.")
                return False
            else:
                print(f"Shorts video created successfully at {shorts_video_output_path}")
                return True
        
        # Otherwise, proceed with full generation process
        print(f"Generating speech with voice: {voice_id}")
        
        # Generate speech with Amazon Polly
        polly = PollyGenerator()
        
        speech_result = polly.generate_speech(
            ssml_content,
            voice_id,
            audio_output_path,
            word_timings_path
        )
        
        if not speech_result:
            print("Failed to generate speech.")
            raise RuntimeError("Speech generation failed")
        
        print("Speech generated successfully.")
        
        # Generate section images if template has images_scenario and English language
        # We only need to generate section images once for all languages
        if 'images_scenario' in template_data and language_code == 'en':
            print("Generating section images...")
            generate_section_images(template_data, paths, language_code)
        
        # Create video with synchronized text
        print("Creating video with section images...")
        print(f"Section images directory: {section_images_dir}")
        
        # Verify section images directory exists
        if not os.path.exists(section_images_dir):
            print(f"Creating section images directory: {section_images_dir}")
            os.makedirs(section_images_dir, exist_ok=True)
        
        # If we're not only doing shorts or no standard video exists, generate it
        if not is_shorts or not os.path.exists(standard_video_output_path):
            print("\n--- Generating standard 1080p video ---")
            video_gen = VideoGenerator(language_code, is_shorts=False)
            video_result = video_gen.create_video(
                word_timings_path,
                audio_output_path,
                standard_video_output_path,
                section_images_dir
            )
            
            # Clean up resources after generating standard video
            # This helps prevent resource leaks between video generations
            del video_gen
            gc.collect()
            
            if not video_result:
                print("Failed to create standard video.")
                raise RuntimeError("Standard video generation failed")
            
            print(f"Standard video created successfully at {standard_video_output_path}")
        
        # Generate Shorts vertical video if requested
        if is_shorts:
            print("\n--- Generating vertical Shorts video ---")
            print("Reusing processed content from standard video to create shorts version")
            
            # Create a shorts generator that will reuse the existing content
            shorts_gen = VideoGenerator(language_code, is_shorts=True, reuse_content=True)
            shorts_result = shorts_gen.create_shorts_from_standard(
                standard_video_output_path,
                shorts_video_output_path,
                word_timings_path
            )
            
            # Clean up resources after generating shorts video
            del shorts_gen
            gc.collect()
            
            if not shorts_result:
                print("Failed to create Shorts video, but standard video was created successfully.")
                # Don't raise exception here, as we already have a standard video
            else:
                print(f"Shorts video created successfully at {shorts_video_output_path}")
        
        return True
        
    except Exception as e:
        print(f"Error processing template {template_path}: {e}")
        traceback.print_exc()
        return False


def generate_thumbnail(template_data, paths, language_code='en'):
    """
    Generate thumbnail for a video using Stable Diffusion.
    
    Args:
        template_data (dict): Template data with thumbnail_prompt
        paths (dict): Dictionary with project paths
        language_code (str): Language code for file naming
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if SD credentials are available
        if not os.getenv('SD_API_KEY') or not os.getenv('SD_AZURE_ENDPOINT'):
            print("Stable Diffusion credentials not found. Cannot generate thumbnail.")
            return False
            
        # Get thumbnail prompt
        thumbnail_prompt = template_data.get('thumbnail_prompt')
        if not thumbnail_prompt:
            print(f"No thumbnail_prompt found in template for language {language_code}")
            return False
            
        # Initialize image generator
        image_gen = ImageGenerator()
        
        # Set output path
        lang_paths = paths['languages'][language_code]
        thumbnail_path = lang_paths['thumbnail']
        
        print(f"\n--- Generating thumbnail for {language_code} ---")
        
        # Generate thumbnail using Stable Diffusion
        result = image_gen.generate_thumbnail(
            thumbnail_prompt, 
            thumbnail_path, 
            language_code
        )
        
        if result:
            print(f"Thumbnail generated successfully at {thumbnail_path}")
            return True
        else:
            print(f"Failed to generate thumbnail for {language_code}")
            return False
            
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        traceback.print_exc()
        return False


def cleanup_resources():
    """Perform thorough cleanup of temporary files and memory resources."""
    print("\n----- Performing thorough resource cleanup -----")
    
    # Clean up temporary files
    tmp_files = []
    
    # Clean up potential temporary directories and files
    try:
        # Clean up MoviePy's temp files specifically
        import tempfile
        moviepy_dir = os.path.join(tempfile.gettempdir(), 'moviepy')
        
        if os.path.exists(moviepy_dir):
            print(f"Checking MoviePy temp directory: {moviepy_dir}")
            
            # Clean up all moviepy cache files
            for cache_file in os.listdir(moviepy_dir):
                if cache_file.endswith('.txt') or cache_file.endswith('.mp4') or cache_file.endswith('.mp3'):
                    cache_path = os.path.join(moviepy_dir, cache_file)
                    if os.path.isfile(cache_path):
                        os.remove(cache_path)
                        print(f"Removed MoviePy cache file: {cache_path}")
    except Exception as e:
        print(f"Warning: Error cleaning MoviePy cache: {e}")

    # Clean up ffmpeg process if any are still running
    try:
        import subprocess
        import signal
        import psutil
        
        print("Checking for stray ffmpeg processes...")
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'ffmpeg' in proc.info['name'].lower():
                    print(f"Terminating ffmpeg process with PID {proc.info['pid']}")
                    os.kill(proc.info['pid'], signal.SIGTERM)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except ImportError:
        print("psutil not installed, skipping ffmpeg process cleanup")
    except Exception as e:
        print(f"Warning: Error cleaning ffmpeg processes: {e}")
    
    # Force garbage collection cycles to clean up memory
    print("Running garbage collection...")
    gc.collect(generation=0)
    gc.collect(generation=1)
    gc.collect(generation=2)
    
    # On macOS, try to free up system resources with a system call
    if sys.platform == 'darwin':
        try:
            import subprocess
            subprocess.run(['purge'], capture_output=True)
            print("Ran macOS 'purge' command to free system buffers")
        except Exception as e:
            print(f"Warning: Could not run 'purge' command: {e}")
    
    # Sleep for a moment to allow OS to reclaim resources
    import time
    time.sleep(1)
    
    print(f"Cleaned up {len(tmp_files)} temporary files and freed memory resources")
    print("----- Resource cleanup completed -----\n")


def process_language_isolated(template_path, paths, language_code, is_shorts):
    """
    Process a single language in an isolated subprocess to prevent resource leaks.
    
    Args:
        template_path (str): Path to the template file
        paths (dict): Dictionary with project paths
        language_code (str): Language code
        is_shorts (bool): Whether to generate shorts
        
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n=== Processing {language_code} in isolated process ===")
    
    try:
        # Run the process directly in the current process (no subprocess)
        # This avoids memory fragmentation issues with multiple processes
        success = process_template(template_path, paths, language_code, is_shorts)
        
        if success:
            print(f"Processing for {language_code} completed successfully")
            return True
        else:
            print(f"Processing for {language_code} failed")
            return False
    except Exception as e:
        print(f"Error in processing {language_code}: {e}")
        return False
    finally:
        # Force cleanup after processing
        cleanup_resources()


def main():
    """Main function to run the video generator."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="YouTube Video Generator")
    parser.add_argument("--all-languages", action="store_true", help="Generate videos for all supported languages")
    parser.add_argument("--upload", action="store_true", help="Upload videos to YouTube after generation")
    parser.add_argument("--thumbnails-only", action="store_true", help="Generate only thumbnails without videos")
    parser.add_argument("--shorts", action="store_true", help="Generate both standard videos AND vertical format videos for YouTube Shorts (max 1 minute)")
    parser.add_argument("--low-memory", action="store_true", help="Run in low memory mode (more conservative resource usage)")
    args = parser.parse_args()
    
    try:
        # Check if assets/fonts directory exists
        if not os.path.exists(config.FONT_DIR):
            print(f"Font directory not found at {config.FONT_DIR}. Creating directory...")
            os.makedirs(config.FONT_DIR, exist_ok=True)
        
        # Check if required fonts exist
        default_font_path = os.path.join(config.FONT_DIR, config.DEFAULT_FONT)
        korean_font_path = os.path.join(config.FONT_DIR, config.KOREAN_FONT)
        
        if not os.path.exists(default_font_path):
            print(f"Warning: Default font not found at {default_font_path}")
        
        if not os.path.exists(korean_font_path):
            print(f"Warning: Korean font not found at {korean_font_path}")
    
        # Check if AWS credentials are set (skip for thumbnails-only mode)
        if not args.thumbnails_only and (not config.AWS_ACCESS_KEY_ID or not config.AWS_SECRET_ACCESS_KEY):
            print("AWS credentials not found. Please set them in the .env file.")
            sys.exit(1)
        
        # Validate template file exists
        template_path = config.TEMPLATE_FILE
        if not os.path.exists(template_path):
            print(f"Template file not found at {template_path}")
            sys.exit(1)
        
        # Template dosyasında images_scenario yoksa örnek ekle
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        if '#images_scenario:' not in template_content:
            print("Adding sample images_scenario to template file...")
            
            sample_images_scenario = """
#images_scenario:
- section: elephant
  prompt: Realistic detailed image of a gray elephant with long trunk in natural habitat, high quality wildlife photography
  description: Show when describing the elephant's physical features

- section: lion
  prompt: Majestic lion with golden mane in African savanna, detailed wildlife photography
  description: Display during the lion description

- section: penguin
  prompt: Emperor penguin standing on ice in Antarctica, high resolution wildlife photography
  description: Show when explaining penguin characteristics

- section: giraffe
  prompt: Tall giraffe with spotted pattern eating from acacia tree, detailed wildlife photography
  description: Display during giraffe segment

- section: dolphin
  prompt: Dolphin jumping out of clear blue ocean water, detailed wildlife photography
  description: Show during dolphin explanation
"""
            
            with open(template_path, 'a', encoding='utf-8') as f:
                f.write(sample_images_scenario)
            
            print("Sample images_scenario added to template file.")
        
        # Parse the template file once
        template_data = parse_template_file(template_path)
        
        # Generate a unique video ID
        video_id = generate_video_id(template_data)
        print(f"Generated video ID: {video_id}")
        
        # Setup project directories
        paths = setup_project_directories(video_id)
        
        if not args.thumbnails_only:
            # Process the English template (original)
            print("\n--- Processing English content ---")
            process_language_isolated(template_path, paths, 'en', False)  # Standard video first
            
            # Force cleanup
            cleanup_resources()
            
            # If shorts requested, do it as a separate step to conserve memory
            if args.shorts:
                print("\n--- Processing English Shorts ---")
                process_language_isolated(template_path, paths, 'en', True)  # Shorts video
                cleanup_resources()
            
            print("Successfully processed English template.")
        
        # Generate thumbnail for English
        generate_thumbnail(template_data, paths, 'en')
        
        # Clean up resources after processing English
        cleanup_resources()
        
        # If --all-languages flag is provided, translate and process other languages
        if args.all_languages:
            # Check if Azure OpenAI credentials are set
            if not os.getenv('AZURE_OPENAI_API_KEY') or not os.getenv('AZURE_OPENAI_ENDPOINT'):
                print("Azure OpenAI credentials not found. Required for translation.")
                sys.exit(1)
            
            print("\n--- Generating content for all supported languages ---")
            
            # Initialize translator
            try:
                translator = Translator()
            except Exception as e:
                print(f"Setup error: {e}")
                traceback.print_exc()
                sys.exit(1)
            
            # Define target languages
            languages = {
                'de': 'German',   # German
                'es': 'Spanish',  # Spanish
                'fr': 'French',   # French
                'ko': 'Korean'    # Korean
            }
            
            # Process each language sequentially (not in parallel)
            for lang_code, lang_name in languages.items():
                print(f"\n=== Translating to {lang_name} ({lang_code}) ===")
                
                try:
                    # Always translate from the original template.txt
                    print(f"Reading original template from: {template_path}")
                    original_template_data = parse_template_file(template_path)
                    
                    if not original_template_data:
                        print(f"Error parsing original template. Skipping {lang_name}.")
                        continue
                    
                    # Create a new template file path for this language
                    lang_template_path = os.path.join(config.INPUT_DIR, f"template_{lang_code}.txt")
                    
                    # Translate the template - pass the language information to avoid translating title/description
                    translated_data = translator.translate_template_with_placeholders(
                        original_template_data, 
                        lang_code,
                        lang_name
                    )
                    
                    # Save translated template
                    save_template_file(translated_data, lang_template_path)
                    print(f"Translated template saved to {lang_template_path}")
                    
                    # Process the translated template for video generation (skip if thumbnails-only)
                    if not args.thumbnails_only:
                        # Process standard video
                        process_language_isolated(lang_template_path, paths, lang_code, False)
                        cleanup_resources()
                        
                        # If shorts requested, do it as a separate step
                        if args.shorts:
                            print(f"\n--- Processing {lang_name} Shorts ---")
                            # FIXED: Direct access to process_template instead of process_language_isolated
                            # This allows us to pass is_shorts=True directly to only generate the shorts video
                            try:
                                standard_video_path = paths['languages'][lang_code]['video']
                                shorts_video_path = paths['languages'][lang_code]['shorts']
                                word_timings_path = paths['languages'][lang_code]['timings']
                                
                                if os.path.exists(standard_video_path):
                                    print(f"Reusing existing standard video for {lang_name} Shorts")
                                    shorts_gen = VideoGenerator(lang_code, is_shorts=True, reuse_content=True)
                                    shorts_result = shorts_gen.create_shorts_from_standard(
                                        standard_video_path,
                                        shorts_video_path,
                                        word_timings_path
                                    )
                                    del shorts_gen
                                    
                                    if shorts_result:
                                        print(f"Shorts video created successfully for {lang_name}")
                                    else:
                                        print(f"Failed to create Shorts video for {lang_name}")
                                else:
                                    print(f"Standard video not found for {lang_name}, cannot create Shorts")
                            except Exception as e:
                                print(f"Error creating Shorts for {lang_name}: {e}")
                            
                            cleanup_resources()
                    
                    # Generate thumbnail for this language
                    generate_thumbnail(translated_data, paths, lang_code)
                    
                    # Force cleanup after thumbnail generation
                    cleanup_resources()
                    
                except Exception as e:
                    print(f"Error in {lang_name} ({lang_code}) processing: {e}")
                    traceback.print_exc()
                    print(f"Continuing with next language despite error.")
                    # We don't terminate the pipeline here, instead continue with next language
                
                print(f"Completed processing for {lang_name}")
            
            print("\n--- Language processing completed ---")
        
        # Create a manifest file with all paths
        manifest_path = os.path.join(paths['video_dir'], 'manifest.json')
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump({
                'video_id': video_id,
                'title': template_data.get('title', ''),
                'paths': paths,
                'generation_date': time.strftime('%Y-%m-%d %H:%M:%S')
            }, f, indent=2)
        
        print(f"\nVideo generation completed successfully with ID: {video_id}")
        print(f"Output files are located in: {paths['video_dir']}")
        
        # Upload videos if --upload flag is provided
        if args.upload:
            print("\n--- Starting YouTube upload process ---")
            
            # Initialize YouTube uploader
            uploader = YouTubeUploader()
            
            # Authenticate with YouTube
            if not uploader.authenticate():
                print("YouTube authentication failed. Videos will not be uploaded.")
                print("Please make sure you have the correct credentials file.")
                sys.exit(1)
            
            # Upload English video first
            print("\n=== Uploading English videos ===")
            english_paths = paths['languages']['en']
            upload_results = uploader.upload_videos_from_template(template_data, english_paths, 'en')
            
            if not upload_results:
                print("Failed to upload English videos.")
            else:
                print(f"Successfully uploaded {len(upload_results)} English videos to YouTube")
            
            # Upload other language videos if --all-languages flag is provided
            if args.all_languages:
                print("\n=== Uploading videos in other languages ===")
                
                languages = {
                    'de': 'German',   # German
                    'es': 'Spanish',  # Spanish
                    'fr': 'French',   # French
                    'ko': 'Korean'    # Korean
                }
                
                for lang_code, lang_name in languages.items():
                    # Get the translated template data
                    lang_template_path = os.path.join(config.INPUT_DIR, f"template_{lang_code}.txt")
                    if os.path.exists(lang_template_path):
                        lang_template_data = parse_template_file(lang_template_path)
                        
                        if lang_template_data:
                            print(f"\n--- Uploading {lang_name} videos ---")
                            lang_paths = paths['languages'][lang_code]
                            lang_results = uploader.upload_videos_from_template(lang_template_data, lang_paths, lang_code)
                            
                            if not lang_results:
                                print(f"Failed to upload {lang_name} videos.")
                            else:
                                print(f"Successfully uploaded {len(lang_results)} {lang_name} videos to YouTube")
            
            # Final summary
            print("\n=== YouTube upload process completed ===")
            print("Note: Newly uploaded videos may take some time to process on YouTube.")
    
    except Exception as e:
        print(f"Error in main process: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()