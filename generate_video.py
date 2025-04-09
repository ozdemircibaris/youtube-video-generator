#!/usr/bin/env python3

import os
import sys
from src.main import generate_video, batch_generate_videos

def main():
    """Sample script to demonstrate generating videos in multiple languages"""
    
    # Check for input file
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # Default to template.txt
        input_file = "input/template.txt"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist.")
        sys.exit(1)
    
    # Parse command line arguments
    all_languages = "--all-languages" in sys.argv or "-a" in sys.argv
    upload = "--upload" in sys.argv or "-u" in sys.argv
    shorts = "--shorts" in sys.argv or "-s" in sys.argv
    language = None
    
    # Extract language if specified
    for arg in sys.argv:
        if arg.startswith("--language="):
            language = arg.split("=")[1]
        elif arg == "--language" or arg == "-l":
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv):
                language = sys.argv[idx + 1]
    
    # Generate videos
    if all_languages:
        print("Generating videos in all supported languages...")
        languages = ['english', 'korean', 'german', 'spanish', 'french']
        results = batch_generate_videos(input_file, languages, upload, shorts)
        
        # Print summary of results
        print("\n=== Video Generation Summary ===")
        for lang, result in results.items():
            if result:
                print(f"✅ {lang.title()} video: {os.path.basename(result['main_video'])}")
                if 'shorts_video' in result and result['shorts_video']:
                    print(f"   Shorts: {os.path.basename(result['shorts_video'])}")
            else:
                print(f"❌ {lang.title()} video: Failed to generate")
    
    elif language:
        print(f"Generating video in {language}...")
        result = generate_video(input_file, None, upload, None, shorts, language)
        
        if result:
            print(f"\n✅ {language.title()} video: {os.path.basename(result['main_video'])}")
            if 'shorts_video' in result and result['shorts_video']:
                print(f"   Shorts: {os.path.basename(result['shorts_video'])}")
        else:
            print(f"\n❌ {language.title()} video: Failed to generate")
    
    else:
        # Default to English
        print("Generating video in English...")
        result = generate_video(input_file, None, upload, None, shorts, 'english')
        
        if result:
            print(f"\n✅ English video: {os.path.basename(result['main_video'])}")
            if 'shorts_video' in result and result['shorts_video']:
                print(f"   Shorts: {os.path.basename(result['shorts_video'])}")
        else:
            print("\n❌ English video: Failed to generate")

if __name__ == "__main__":
    main() 