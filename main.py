"""
Main module for YouTube video generator.
"""

import os
import json
import argparse
import sys
import traceback

from src.template_parser import parse_template_file
from src.polly_generator import PollyGenerator
from src.video_generator import VideoGenerator
from src.translator import Translator
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
                if key != 'content' and key != 'ssml_content':
                    f.write(f"#{key}: {value}\n")
            
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


def process_template(template_path, output_dir, language_code='en'):
    """
    Process a single template file to generate a video.
    
    Args:
        template_path (str): Path to the template file
        output_dir (str): Directory to save output files
        language_code (str): Language code for file naming (default: 'en')
        
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
        
        print(f"Generating speech with voice: {voice_id}")
        
        # Generate speech with Amazon Polly
        polly = PollyGenerator()
        
        # Create output paths with language code
        audio_output_path = os.path.join(output_dir, f"speech_{language_code}.mp3")
        word_timings_path = os.path.join(output_dir, f"timings_{language_code}.json")
        video_output_path = os.path.join(output_dir, f"video_{language_code}.mp4")
        
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
        
        # Create video with synchronized text
        print("Creating video...")
        
        # Initialize VideoGenerator with language code for proper font selection
        video_gen = VideoGenerator(language_code)
        video_result = video_gen.create_video(
            word_timings_path,
            audio_output_path,
            video_output_path
        )
        
        if not video_result:
            print("Failed to create video.")
            raise RuntimeError("Video generation failed")
        
        print(f"Video created successfully at {video_output_path}")
        return True
        
    except Exception as e:
        print(f"Error processing template {template_path}: {e}")
        traceback.print_exc()
        return False


def main():
    """Main function to run the video generator."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="YouTube Video Generator")
    parser.add_argument("--all-languages", action="store_true", help="Generate videos for all supported languages")
    parser.add_argument("--upload", action="store_true", help="Upload videos to YouTube after generation")
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
    
        # Check if AWS credentials are set
        if not config.AWS_ACCESS_KEY_ID or not config.AWS_SECRET_ACCESS_KEY:
            print("AWS credentials not found. Please set them in the .env file.")
            sys.exit(1)
        
        # Validate template file exists
        template_path = config.TEMPLATE_FILE
        if not os.path.exists(template_path):
            print(f"Template file not found at {template_path}")
            sys.exit(1)
        
        # Process the English template (original)
        process_template(template_path, config.OUTPUT_DIR, 'en')
        print("Successfully processed English template.")
        
        # If --all-languages flag is provided, translate and process other languages
        if args.all_languages:
            # Check if Azure OpenAI credentials are set
            if not os.getenv('AZURE_OPENAI_API_KEY') or not os.getenv('AZURE_OPENAI_ENDPOINT'):
                print("Azure OpenAI credentials not found. Required for translation.")
                sys.exit(1)
            
            print("\n--- Generating videos for all supported languages ---")
            
            # Parse the original template once more
            try:
                template_data = parse_template_file(template_path)
                if not template_data:
                    print("Failed to parse template file for translation.")
                    sys.exit(1)
                
                # Initialize translator
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
            
            # Process each language separately
            for lang_code, lang_name in languages.items():
                print(f"\n=== Translating to {lang_name} ({lang_code}) ===")
                
                try:
                    # Translate template
                    translated_data = translator.translate_template(template_data, lang_code)
                    
                    # Save translated template
                    lang_template_path = os.path.join(config.INPUT_DIR, f"template_{lang_code}.txt")
                    save_template_file(translated_data, lang_template_path)
                    print(f"Translated template saved to {lang_template_path}")
                    
                    # Process the translated template but continue with other languages if this one fails
                    if not process_template(lang_template_path, config.OUTPUT_DIR, lang_code):
                        print(f"Warning: Processing template for {lang_name} failed but continuing with other languages")
                    else:
                        print(f"Successfully processed {lang_name} ({lang_code}) template.")
                    
                except Exception as e:
                    print(f"Error in {lang_name} ({lang_code}) processing: {e}")
                    traceback.print_exc()
                    print(f"Continuing with next language despite error.")
                    # We don't terminate the pipeline here, instead continue with next language
            
            print("\n--- Language processing completed ---")
        
        # Upload videos if --upload flag is provided
        if args.upload:
            print("\nVideo upload to YouTube not yet implemented.")
            # Future implementation will go here
    
    except Exception as e:
        print(f"Error in main process: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()