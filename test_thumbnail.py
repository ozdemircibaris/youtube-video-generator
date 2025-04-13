#!/usr/bin/env python
"""
Thumbnail Generator Test Script

This script tests the thumbnail generation functionality by generating a thumbnail
for a given title and prompt without having to generate a full video.

Usage:
  python test_thumbnail.py --title "Your Video Title" [--language english] [--prompt "Custom prompt"]

Example:
  python test_thumbnail.py --title "Learn Basic French Phrases" --language french
"""

import os
import argparse
import time
from src.thumbnail_generator import generate_thumbnail
from src.config import OUTPUT_DIR

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test thumbnail generation')
    parser.add_argument('--title', required=True, help='Video title to use for the thumbnail')
    parser.add_argument('--language', default='english', help='Language of the video (affects prompt)')
    parser.add_argument('--prompt', help='Custom prompt to override the default template')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(os.path.join(OUTPUT_DIR, 'thumbnails'), exist_ok=True)
    
    print(f"Generating thumbnail for title: {args.title}")
    print(f"Language: {args.language}")
    
    start_time = time.time()
    
    # Generate the thumbnail
    if args.prompt:
        print(f"Using custom prompt: {args.prompt}")
        thumbnail_path = generate_thumbnail(args.title, args.language, args.prompt)
    else:
        thumbnail_path = generate_thumbnail(args.title, args.language)
    
    # Check result
    if thumbnail_path and os.path.exists(thumbnail_path):
        elapsed_time = time.time() - start_time
        print(f"✅ Thumbnail generated successfully in {elapsed_time:.2f} seconds")
        print(f"Thumbnail saved to: {thumbnail_path}")
        
        # Print OS-specific open command
        if os.name == 'posix':  # macOS or Linux
            print(f"Run 'open {thumbnail_path}' to view the thumbnail")
        elif os.name == 'nt':  # Windows
            print(f"Run 'start {thumbnail_path}' to view the thumbnail")
    else:
        print("❌ Failed to generate thumbnail")

if __name__ == "__main__":
    main() 