import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google Cloud TTS API Key
GOOGLE_TTS_API_KEY = os.getenv('GOOGLE_TTS_API_KEY')

# YouTube API credentials
YOUTUBE_API_CREDENTIALS_JSON = os.getenv('YOUTUBE_API_CREDENTIALS')
if YOUTUBE_API_CREDENTIALS_JSON:
    YOUTUBE_API_CREDENTIALS = json.loads(YOUTUBE_API_CREDENTIALS_JSON)
else:
    with open('youtube-credentials.json', 'r') as f:
        YOUTUBE_API_CREDENTIALS = json.load(f)

# Paths
ASSETS_DIR = 'assets'
INTRO_VIDEO = os.path.join(ASSETS_DIR, 'intro.mp4')
OUTRO_VIDEO = os.path.join(ASSETS_DIR, 'outro.mp4')
BACKGROUND_MUSIC = os.path.join(ASSETS_DIR, 'background-music.mp3')
BACKGROUND_VIDEOS_DIR = os.path.join(ASSETS_DIR, 'background_videos')
OUTPUT_DIR = 'output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Regular video settings
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FONT_SIZE = 60
FONT_COLOR = '#FFD700'  # Gold/yellow color
HIGHLIGHT_COLOR = '#FFFF00'  # Bright yellow for highlights
MAX_WORDS_PER_LINE = 5
BACKGROUND_COLOR = 'black'  # Still used as fallback
BACKGROUND_MUSIC_VOLUME = 0.3  # 30%

# YouTube Shorts settings
SHORTS_MAX_DURATION = 60  # Max duration in seconds for YouTube Shorts
SHORTS_VIDEO_WIDTH = 1080
SHORTS_VIDEO_HEIGHT = 1920
SHORTS_FONT_SIZE = 70  # Slightly larger text for better readability on mobile

# Speech settings
ENGLISH_LEVEL_RATES = {
    'beginner': 0.7,
    'intermediate': 0.8,
    'advanced': 0.9,
    'proficient': 1.0
} 