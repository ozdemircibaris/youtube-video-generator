#!/usr/bin/env python3
"""
Test script for multilingual video generation

Usage:
    python test_multilingual.py [input_file] [options]

Options:
    --language=LANGUAGE    Generate video in specific language (english, korean, german, spanish, french)
    --all-languages        Generate videos in all supported languages
    --upload               Upload videos to YouTube after generation
    --shorts               Generate YouTube Shorts versions

Example:
    python test_multilingual.py input/template.txt --language=korean
    python test_multilingual.py input/template.txt --all-languages
"""

import os
import sys
from src.main import generate_video, batch_generate_videos
from src.translator import translate_template_file

def test_translation_only(input_file):
    """Test translation functionality without generating videos"""
    languages = ['korean', 'german', 'spanish', 'french']
    
    print("\n=== Testing Translation Functionality ===\n")
    results = {}
    
    for language in languages:
        print(f"Translating template to {language}...")
        try:
            _, translated_file = translate_template_file(input_file, language)
            if translated_file and os.path.exists(translated_file):
                results[language] = translated_file
            else:
                results[language] = None
        except Exception as e:
            print(f"Error translating to {language}: {e}")
            results[language] = None
    
    # Print summary
    print("\n=== Translation Results ===")
    for lang, file_path in results.items():
        if file_path:
            print(f"✅ {lang.title()}: {os.path.basename(file_path)}")
        else:
            print(f"❌ {lang.title()}: Failed")

def test_video_generation(input_file, all_languages=False, language=None, upload=False, shorts=False):
    """Test video generation in one or all languages"""
    if all_languages:
        print("\n=== Testing Video Generation in All Languages ===\n")
        languages = ['english', 'korean', 'german', 'spanish', 'french']
        results = batch_generate_videos(input_file, languages, upload, shorts)
        
        # Print summary
        print("\n=== Video Generation Results ===")
        for lang, result in results.items():
            if result:
                print(f"✅ {lang.title()} video: {os.path.basename(result['main_video'])}")
                if 'shorts_video' in result and result['shorts_video']:
                    print(f"   Shorts: {os.path.basename(result['shorts_video'])}")
            else:
                print(f"❌ {lang.title()} video: Failed to generate")
    
    elif language:
        print(f"\n=== Testing Video Generation in {language.title()} ===\n")
        result = generate_video(input_file, None, upload, None, shorts, language)
        
        # Print result
        print("\n=== Video Generation Result ===")
        if result:
            print(f"✅ {language.title()} video: {os.path.basename(result['main_video'])}")
            if 'shorts_video' in result and result['shorts_video']:
                print(f"   Shorts: {os.path.basename(result['shorts_video'])}")
        else:
            print(f"❌ {language.title()} video: Failed to generate")
    else:
        # Default to English
        print("\n=== Testing Video Generation in English ===\n")
        result = generate_video(input_file, None, upload, None, shorts, 'english')
        
        # Print result
        print("\n=== Video Generation Result ===")
        if result:
            print(f"✅ English video: {os.path.basename(result['main_video'])}")
            if 'shorts_video' in result and result['shorts_video']:
                print(f"   Shorts: {os.path.basename(result['shorts_video'])}")
        else:
            print("❌ English video: Failed to generate")

def main():
    """Run the multilingual tests based on command line arguments"""
    # Default input file
    input_file = "input/template.txt"
    
    # Parse command line arguments
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        input_file = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist.")
        sys.exit(1)
    
    # Parse options
    translation_only = "--translation-only" in sys.argv
    all_languages = "--all-languages" in sys.argv
    upload = "--upload" in sys.argv
    shorts = "--shorts" in sys.argv
    language = None
    
    # Check for language option
    for arg in sys.argv:
        if arg.startswith("--language="):
            language = arg.split("=")[1].lower()
    
    # Run tests
    if translation_only:
        test_translation_only(input_file)
    else:
        test_video_generation(input_file, all_languages, language, upload, shorts)

if __name__ == "__main__":
    main() 