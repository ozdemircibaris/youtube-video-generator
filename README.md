# AI-Powered YouTube Educational Video Generator

An automated system to generate multilingual educational videos using AI services including Amazon Polly for text-to-speech, Azure OpenAI for translations, and Azure Stable Diffusion for thumbnail and section image generation.

## Overview

This project creates educational videos with synchronized text highlighting from simple template files. The system automatically translates content into multiple languages, generates professional voiceover using Amazon Polly, creates videos with real-time word highlighting, produces custom thumbnails, and embeds section-specific background images using Azure Stable Diffusion.

## Demo Videos

Check out examples of the generated educational videos on our social media:

- YouTube: [World of Languages](https://www.youtube.com/channel/UCLL3ulEh6Oo_xRVA0QdZ2cA)
- TikTok: [@worldoflanguages30](https://www.tiktok.com/@worldoflanguages30)

## Features

- **Template-Based Video Generation**: Create videos from simple text templates with SSML support
- **Professional Text-to-Speech**: Utilize Amazon Polly neural voices for natural-sounding narration
- **Real-Time Word Highlighting**: Synchronize highlighted text with speech
- **Multilingual Support**: Generate videos in multiple languages (English, German, Spanish, French, Korean)
- **Automatic Translation**: Translate content using Azure OpenAI
- **Custom Thumbnail Generation**: Create professional thumbnails using Azure Stable Diffusion
- **Section Background Images**: Generate and display content-specific background images
- **YouTube Shorts Support**: Generate vertical format videos for YouTube Shorts
- **YouTube Upload Automation**: Directly upload videos to YouTube with proper metadata
- **Scheduled Publishing**: Option to schedule video releases at optimal times

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/youtube-video-generator.git
   cd youtube-video-generator
   ```

2. Install the required dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with the necessary API credentials:

   ```
   # AWS credentials for Amazon Polly
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   AWS_REGION=us-east-1

   # Azure OpenAI API credentials for translation
   AZURE_OPENAI_ENDPOINT=your_azure_endpoint
   AZURE_OPENAI_API_KEY=your_azure_api_key
   AZURE_OPENAI_API_VERSION=your_api_version
   AZURE_OPENAI_COMPLETION_DEPLOYMENT=your_deployment_name

   # Azure Stable Diffusion for thumbnail generation
   SD_API_KEY=your_sd_api_key
   SD_AZURE_ENDPOINT=your_sd_azure_endpoint
   ```

4. For YouTube uploads, set up OAuth credentials:

   - Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the YouTube Data API v3
   - Create OAuth 2.0 credentials
   - Download the credentials JSON file and save it to `credentials/youtube_credentials.json`

5. Create an `assets/fonts` directory and add the following fonts:
   - `NotoSans-Regular.ttf`: Default font for most languages
   - `NotoSerifKR-VariableFont_wght.ttf`: Font for Korean text

## Usage

### Basic Usage

Generate a video in English only:

```
python main.py
```

### Multilingual Video Generation

Generate videos in all supported languages:

```
python main.py --all-languages
```

### Thumbnail Generation Only

Generate only thumbnails for all supported languages:

```
python main.py --all-languages --thumbnails-only
```

### YouTube Shorts Generation

Generate videos in YouTube Shorts format (vertical 9:16 ratio):

```
python main.py --shorts
```

### YouTube Upload

Generate and upload videos to YouTube:

```
python main.py --upload
```

Generate and upload videos for all languages:

```
python main.py --all-languages --upload
```

Generate both standard and Shorts videos and upload them:

```
python main.py --shorts --upload
```

Generate everything (standard + Shorts videos) in all languages and upload them:

```
python main.py --all-languages --shorts --upload
```

## Template Format

Templates use a simple format with metadata fields, SSML content, and section image definitions:

```
#title: Video Title
#english_level: beginner
#voice: Matthew
#description: Your video description here
#tags: tag1, tag2, tag3
#thumbnail_title: Thumbnail Title Text
#thumbnail_prompt: Detailed prompt for thumbnail generation with Stable Diffusion

#images_scenario:
- section: section_name1
  prompt: Detailed prompt for section image generation
  description: When to display this section image

- section: section_name2
  prompt: Another section image prompt
  description: When to display this second section image

#content: Main Content Title
<speak>
<prosody rate="95%" volume="loud">
Your content text here.

<mark name="section_name1_start"/>This text will be displayed with the first section image as background.
You can use SSML tags for better pronunciation and timing.<mark name="section_name1_end"/>

<mark name="section_name2_start"/>This text will be displayed with the second section image as background.<mark name="section_name2_end"/>
</prosody>
</speak>
```

### Template Variables

You can use `{language}` as a variable in your template, which will be replaced with the appropriate language name during translation.

## Supported Languages

The following languages are supported with their default voices:

- English: Matthew
- German: Daniel
- Spanish: Lucia
- French: Remi
- Korean: Seoyeon

## Video Configuration

The configuration settings are defined in `src/config.py`:

- **Standard Videos**: 1920x1080 (16:9) resolution at 30 FPS
- **YouTube Shorts**: 1080x1920 (9:16) resolution with max duration of 60 seconds
- **Text Formatting**: Customizable font size, color, and highlighting
- **Thumbnails**: 1280x720 resolution with optimized settings for YouTube

## Output Structure

```
output/
└── {video-id}/          # Unique ID for each video generation
    ├── section_images/  # Background images for each section
    ├── en/              # English output
    │   ├── speech.mp3   # Generated English audio
    │   ├── timings.json # English word timing information
    │   ├── video.mp4    # Final English video
    │   ├── shorts.mp4   # YouTube Shorts format (if enabled)
    │   └── thumbnail.jpg # Generated English thumbnail
    ├── de/              # German output
    ├── es/              # Spanish output
    ├── fr/              # French output
    ├── ko/              # Korean output
    └── manifest.json    # Information about the generation
```

## Requirements

- Python 3.8+
- AWS Account with Amazon Polly access
- Azure OpenAI API access
- Azure Stable Diffusion API access
- YouTube API credentials (for upload feature)
- Required Python packages (see requirements.txt)
