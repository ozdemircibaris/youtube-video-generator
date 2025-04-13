#!/usr/bin/env python
"""
Simple Thumbnail Generator Test Script

This script tests only the fallback thumbnail generation functionality,
which doesn't require Stable Diffusion and uses very little memory.

Usage:
  python test_simple_thumbnail.py --title "Your Video Title" [--language english]

Example:
  python test_simple_thumbnail.py --title "Learn Basic French Phrases" --language french
"""

import os
import argparse
import time
from src.thumbnail_generator import generate_simple_thumbnail
from src.config import OUTPUT_DIR

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test simple thumbnail generation')
    parser.add_argument('--title', required=True, help='Video title to use for the thumbnail')
    parser.add_argument('--language', default='english', help='Language of the video')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(os.path.join(OUTPUT_DIR, 'thumbnails'), exist_ok=True)
    
    print(f"Generating simple thumbnail for title: {args.title}")
    print(f"Language: {args.language}")
    
    start_time = time.time()
    
    # Generate the thumbnail directly using the simple method
    thumbnail_path = generate_simple_thumbnail(args.title, args.language)
    
    # Check result
    if thumbnail_path and os.path.exists(thumbnail_path):
        elapsed_time = time.time() - start_time
        print(f"✅ Simple thumbnail generated successfully in {elapsed_time:.2f} seconds")
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