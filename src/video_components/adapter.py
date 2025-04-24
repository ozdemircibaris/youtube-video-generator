"""
Adapter module for backward compatibility with the old VideoGenerator class.
This allows for a smooth transition from the monolithic structure to the component-based architecture.
"""

import os
import sys
import importlib.util

from src.video_components import VideoGenerator

# Check if the old monolithic video_generator.py file exists
old_module_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "video_generator.py")

def get_video_generator_class():
    """
    Return the appropriate VideoGenerator class based on what's available.
    
    Returns:
        class: VideoGenerator class
    """
    # If the old module exists, use the old implementation for backward compatibility
    if os.path.exists(old_module_path):
        try:
            # Dynamically import the old module
            spec = importlib.util.spec_from_file_location("legacy_video_generator", old_module_path)
            legacy_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(legacy_module)
            
            print("Using the original VideoGenerator implementation for backward compatibility.")
            return legacy_module.VideoGenerator
        except Exception as e:
            print(f"Error loading legacy VideoGenerator: {e}")
            print("Falling back to the new component-based implementation.")
            return VideoGenerator
    
    # Otherwise, use the new component-based implementation
    return VideoGenerator

# Export the appropriate VideoGenerator class
__all__ = ['get_video_generator_class'] 