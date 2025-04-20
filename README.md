# AI-Powered YouTube Educational Video Generator

An automated system to generate multilingual educational videos using AI services including Amazon Polly for text-to-speech, Azure OpenAI for translations, and Azure Stable Diffusion for thumbnail generation.

## Project Overview

This project creates educational videos with synchronized text highlighting from simple template files. The system automatically translates content into multiple languages, generates professional voiceover using Amazon Polly, creates videos with real-time word highlighting, and produces custom thumbnails using Azure Stable Diffusion.

## Features

- **Template-Based Video Generation**: Create videos from simple text templates with SSML support
- **Professional Text-to-Speech**: Utilize Amazon Polly neural voices for natural-sounding narration
- **Real-Time Word Highlighting**: Synchronize highlighted text with speech
- **Multilingual Support**: Generate videos in multiple languages (English, German, Spanish, French, Korean)
- **Automatic Translation**: Translate content using Azure OpenAI
- **Language-Specific Font Support**: Properly display text in various languages, including Korean
- **Custom Thumbnail Generation**: Create professional thumbnails using Azure Stable Diffusion

## Development Principles

- **Modularity**: Each component maintains a specific responsibility
- **Size Constraints**: No file exceeds 500 lines of code
- **Component-Based Architecture**: System is built with discrete, reusable components
- **Dynamic Processing**: The pipeline is designed to handle content dynamically
- **No Fallback Mechanisms**: The system is designed to terminate immediately upon encountering errors
- **Full AI Integration**: Seamlessly integrate AI services

## Project Structure

```
youtube-video-generator/
├── assets/                  # Asset files like fonts
│   └── fonts/               # Font files for different languages
├── input/                   # Input template files
│   ├── template.txt         # Main template file (English)
│   ├── template_de.txt      # German template (auto-generated)
│   ├── template_es.txt      # Spanish template (auto-generated)
│   ├── template_fr.txt      # French template (auto-generated)
│   └── template_ko.txt      # Korean template (auto-generated)
├── output/                  # Generated output files
│   ├── speech_en.mp3        # Generated English audio
│   ├── timings_en.json      # English word timing information
│   ├── video_en.mp4         # Final English video
│   ├── thumbnail_en.jpg     # Generated English thumbnail
│   └── ...                  # Similar files for other languages
├── src/                     # Source code modules
│   ├── __init__.py          # Package initialization
│   ├── config.py            # Configuration settings
│   ├── image_generator.py   # Azure Stable Diffusion integration
│   ├── polly_generator.py   # Amazon Polly integration
│   ├── template_parser.py   # Template file parser
│   ├── translator.py        # Azure OpenAI translation module
│   └── video_generator.py   # Video generation with text highlighting
├── main.py                  # Main application entry point
└── requirements.txt         # Project dependencies
```

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

   # YouTube API credentials for future uploading
   YOUTUBE_API_CREDENTIALS=path_to_credentials_file
   ```

4. Create an `assets/fonts` directory and add the following fonts:
   - `NotoSans-Regular.ttf`: Default font for most languages
   - `NotoSerifKR-VariableFont_wght.ttf`: Font for Korean text

## Template Format

Templates use a simple format with metadata fields and SSML content:

```
#title: Video Title
#english_level: beginner
#voice: Matthew
#description: Your video description here
#tags: tag1, tag2, tag3
#thumbnail_title: Thumbnail Title Text
#thumbnail_prompt: Detailed prompt for thumbnail generation with Stable Diffusion

#content: Main Content Title
<speak>
<prosody rate="95%" volume="loud">
Your content text here.

<mark name="section_start"/>This text will be marked with timing information.
You can use SSML tags for better pronunciation and timing.<mark name="section_end"/>
</prosody>
</speak>
```

## Usage

### Basic Usage

To generate a video in English only:

```
python main.py
```

### Multilingual Video Generation

To generate videos in all supported languages:

```
python main.py --all-languages
```

### Thumbnail Generation Only

To generate only thumbnails for all supported languages:

```
python main.py --all-languages --thumbnails-only
```

### Future: YouTube Upload

To generate and upload videos to YouTube (when implemented):

```
python main.py --all-languages --upload
```

## Supported Languages

Currently, the following languages are supported with their default voices:

- English: Matthew
- German: Daniel
- Spanish: Lucia
- French: Remi
- Korean: Seoyeon

## Components

### Template Parser

Parses template files, extracting metadata and SSML content for processing.

### Translator

Uses Azure OpenAI to translate template content into multiple languages.

### Polly Generator

Integrates with Amazon Polly to generate speech from SSML content and extract word timing information.

### Video Generator

Creates video frames with synchronized text and highlights the current word being spoken.

### Image Generator

Uses Azure Stable Diffusion to generate professional thumbnails based on template prompts. Note the following requirements for the Azure Stable Diffusion API:

- Authentication requires an "Authorization" header with the API key
- Include "accept": "application/json" in the headers
- Only certain image sizes are supported (the code uses 1366x768)
- The response contains the image data in an "image" field as base64

## Thumbnail Generation Details

The thumbnail generation process uses Azure Stable Diffusion with the following specifics:

1. Each template includes a `thumbnail_prompt` field with detailed instructions for the image generation
2. The system generates thumbnails in the specified dimensions (resizing to 1280x720 if needed)
3. Thumbnails are saved as JPG files in the output directory
4. Each language gets its own thumbnail with localized text
5. The original English prompt is preserved for all languages to ensure high-quality results

## Future Features

The following features are planned for future implementation:

1. **Background Images**

   - Generate relevant background images for video content
   - Replace current black background with contextual images

2. **YouTube Upload**

   - Automatically upload generated videos to YouTube
   - Set titles, descriptions, and tags based on template data
   - Support for scheduling and playlist organization

3. **Custom Intro/Outro**
   - Add customizable intro and outro segments
   - Include custom branding elements

## Requirements

- Python 3.8+
- AWS Account with Amazon Polly access
- Azure OpenAI API access
- Azure Stable Diffusion API access
- YouTube API credentials (for future upload feature)

## License

[Your license information here]

## Contributing

Contributions are welcome! Please follow these guidelines:

- Maintain modular architecture
- Keep files under 500 lines
- Follow the component-based approach
- Ensure all features are dynamic and adaptable
- Add comprehensive error handling
- Do not implement fallback mechanisms; terminate on errors
