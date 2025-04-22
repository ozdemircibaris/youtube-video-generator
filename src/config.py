"""
Configuration settings for YouTube video generator.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# Video Configuration
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30
VIDEO_BACKGROUND_COLOR = (0, 0, 0)  # Black background

# YouTube Shorts Configuration
SHORTS_VIDEO_WIDTH = 1080
SHORTS_VIDEO_HEIGHT = 1920  # 9:16 aspect ratio for vertical video
SHORTS_MAX_DURATION_MS = 60000  # 60 seconds (1 minute) in milliseconds

# Font Configuration
FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")
DEFAULT_FONT = "NotoSans-Regular.ttf"
KOREAN_FONT = "NotoSerifKR-VariableFont_wght.ttf"

# Language-specific fonts
LANGUAGE_FONTS = {
    'ko': KOREAN_FONT,  # Korean
    'en': DEFAULT_FONT,  # English
    'de': DEFAULT_FONT,  # German
    'es': DEFAULT_FONT,  # Spanish
    'fr': DEFAULT_FONT   # French
}

# Create font directory if it doesn't exist
os.makedirs(FONT_DIR, exist_ok=True)

# Text Configuration
TEXT_COLOR = (255, 255, 255)  # White text
TEXT_OUTLINE_COLOR = (0, 0, 0)  # Black outline
TEXT_OUTLINE_THICKNESS = 2
TEXT_FONT_SIZE = 60
HIGHLIGHT_COLOR = (0, 255, 255)  # Yellow in BGR format (not RGB!)
HIGHLIGHT_OUTLINE_COLOR = (0, 0, 0)  # Black outline for highlighted text
MAX_WORDS_PER_LINE = 4
MAX_LINES = 3

# Paths
INPUT_DIR = "input"
OUTPUT_DIR = "output"
TEMPLATE_FILE = os.path.join(INPUT_DIR, "template.txt")
SECTION_IMAGES_DIR = os.path.join(OUTPUT_DIR, "section_images")

# Create directories if they don't exist
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SECTION_IMAGES_DIR, exist_ok=True)

# Amazon Polly Settings
POLLY_OUTPUT_FORMAT = "mp3"
POLLY_SAMPLE_RATE = "22050"
AUDIO_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "speech.mp3")
WORD_TIMINGS_PATH = os.path.join(OUTPUT_DIR, "word_timings.json")
VIDEO_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "video.mp4")

# Thumbnail Configuration
THUMBNAIL_WIDTH = 1280
THUMBNAIL_HEIGHT = 720  # YouTube thumbnail aspect ratio (16:9)
THUMBNAIL_FORMAT = "jpg"
THUMBNAIL_QUALITY = 95  # JPEG quality (1-100)
THUMBNAIL_DEFAULT_PROMPT_PREFIX = "Create a professional, eye-catching YouTube thumbnail with high-quality visuals."
