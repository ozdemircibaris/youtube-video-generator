"""
YouTube Educational Video Generator package.
"""

from src.video_components.adapter import get_video_generator_class

# Get the appropriate VideoGenerator class to maintain backwards compatibility
VideoGenerator = get_video_generator_class()

# Export top-level classes for easy access
__all__ = [
    'VideoGenerator'
]