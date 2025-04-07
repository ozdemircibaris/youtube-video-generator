# Google referanslarını kaldırıp AWS için yapılandırma ekleyelim
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS Credentials
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

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

# Amazon Polly voice mappings - Google TTS ses isimlerinden Polly isimlerine eşleme
VOICE_MAPPINGS = {
    'en-US-Neural2-F': 'Joanna',  # Neural female voice
    'en-US-Neural2-D': 'Matthew',  # Neural male voice
    'en-US-Neural2-A': 'Matthew',
    'en-US-Neural2-C': 'Joanna',
    'en-US-Neural2-E': 'Matthew',
    'en-US-Neural2-G': 'Joanna',
    'en-US-Neural2-H': 'Matthew',
    'en-US-Neural2-I': 'Joanna',
    'en-US-Neural2-J': 'Matthew',
    'en-US-Standard-A': 'Ivy',
    'en-US-Standard-B': 'Joey',
    'en-US-Standard-C': 'Kendra',
    'en-US-Standard-D': 'Justin',
    'en-US-Standard-E': 'Kimberly',
    'en-US-Standard-F': 'Salli',
    'en-US-Standard-G': 'Kevin',
    'en-US-Standard-H': 'Nicole',
    'en-US-Standard-I': 'Russell',
    'en-US-Standard-J': 'Samantha',
}

# Default Polly voice if no mapping found
DEFAULT_POLLY_VOICE = 'Joanna'