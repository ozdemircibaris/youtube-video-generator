# YouTube Video Generator

This tool automatically creates educational videos from text input, adds synchronized captions, and can upload them directly to YouTube. It supports multiple languages by translating your content using Azure OpenAI.

## Features

- Automatic video generation with synchronized text captions
- High-quality text-to-speech using Amazon Polly
- Support for multiple languages with automatic translation
- YouTube Shorts generation option
- Direct upload to YouTube
- Custom thumbnail generation using AI

## Thumbnail Generation

The tool automatically generates custom thumbnails for your videos using Stable Diffusion:

- Thumbnails are created based on the video title and language
- Custom text overlay is added to the generated image
- Different thumbnails for regular videos and Shorts
- Automatically uploaded to YouTube along with the video

You can also test thumbnail generation independently:

```bash
# Generate a test thumbnail
python test_thumbnail.py --title "Your Video Title" --language english

# Generate with a custom prompt
python test_thumbnail.py --title "Learn Spanish Fast" --language spanish --prompt "Professional language learning thumbnail with Spanish flag"
```

## Input Format

Input files should be placed in the `input` directory and follow this format:

```
#title: Your Video Title
#english_level: intermediate
#voice: Matthew
#description: Your video description here.
You can write multiple lines for descriptions
and they will be properly joined together.

#tags: tag1,tag2,tag3,tag4

#content: This is the main content of your video. This text will be converted to speech.

You can write as much text as you need, using multiple paragraphs.

The system will automatically split your content into sentences and
synchronize them with the speech in the final video.
```

### Important Formatting Rules:

1. **Parameters** start with a `#` symbol followed by a parameter name, a colon, and the value.
2. Multi-line parameter values are supported - just continue writing in the next line without adding a `#`.
3. **Leave an empty line** between parameter blocks and the main content.
4. The **content** section must start with `#content:` followed by your main text content.
5. Main content can span multiple paragraphs and will be properly processed.

### Available Parameters:

- `title`: The title of your video
- `english_level`: (beginner, intermediate, advanced, proficient) - affects speech rate
- `voice`: Amazon Polly voice name to use (Matthew, Joanna, Daniel, Lucia, Seoyeon, etc.)
- `description`: YouTube video description
- `tags`: Comma-separated list of tags for the video

## Multi-Language Support

This tool can automatically translate your content to multiple languages and generate videos for each language. Supported languages:

- English (original) - Uses the voice specified in the template or defaults to Matthew (male voice)
- Korean - Uses Seoyeon (female voice)
- German - Uses Daniel (male voice)
- Spanish - Uses Lucia (female voice)
- French - Uses Remi (male voice)

When generating videos in multiple languages, appropriate voice models for each language are automatically selected as listed above.

## Usage

```bash
# Generate video from input file in English (default)
python -m src.main input/your_input_file.txt

# Generate video in a specific language
python -m src.main input/your_input_file.txt --language korean

# Generate and upload to YouTube
python -m src.main input/your_input_file.txt --upload

# Generate with custom output filename
python -m src.main input/your_input_file.txt --output custom_name.mp4

# Generate a YouTube Shorts version too
python -m src.main input/your_input_file.txt --shorts

# Generate videos in all supported languages
python -m src.main input/your_input_file.txt --all-languages

# Generate video in a specific language and upload to YouTube
python -m src.main input/your_input_file.txt --language german --upload

# Generate videos in all languages with Shorts versions and upload all to YouTube
python -m src.main input/your_input_file.txt --all-languages --shorts --upload
```

## Language-specific Options

When generating videos in multiple languages:

1. Each language will have its own video file with the language name in the filename.
2. All text content and metadata (title, description) are translated automatically.
3. Language-appropriate voice models are selected automatically (as listed in the Multi-Language Support section).
4. Proper fonts are used for displaying text, with support for Korean characters using Noto Serif KR font.
5. When uploading to YouTube, the language is included in the video title as [Language].

## Example

Check out `input/template.txt` for a detailed example of a properly formatted input file.

## Requirements

Make sure you have the following credentials set in your `.env` file:

```
# AWS credentials (for speech generation)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1

# Azure OpenAI credentials (for translation)
AZURE_OPENAI_ENDPOINT=your_azure_endpoint
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_API_VERSION=your_api_version
AZURE_OPENAI_COMPLETION_DEPLOYMENT=your_deployment_name
```

## Installation

1. Clone this repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your API credentials
4. Create a template file in the `input` directory
5. Run the generator using one of the commands above

---

## Demo Videos

Check out example videos created with this tool:

- YouTube: [World of Languages](https://www.youtube.com/channel/UCLL3ulEh6Oo_xRVA0QdZ2cA)
- TikTok: [World of Languages](https://www.tiktok.com/@worldoflanguages30)

---

## Assets Structure

The `assets` folder contains all the static files required for video generation:

- **intro.mp4**: Opening intro animation for the videos (generated with Canva)
- **outro.mp4**: Closing outro animation for the videos (generated with Canva)
- **background-music.mp3**: Background music track used in videos

### Background Videos

The `assets/background_videos` directory contains background video clips (numbered 1.mp4 through 11.mp4) sourced from Pexels. These videos are randomly selected and used as background visuals during content presentation.

### Fonts

The `assets/fonts` directory contains custom fonts used for text rendering:

- `NotoSerifKR-VariableFont_wght.ttf`: A variable font that supports Korean characters

When generating videos in different languages, the system automatically selects appropriate fonts for text overlays.

---
