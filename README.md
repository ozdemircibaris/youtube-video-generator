# AI-Powered YouTube Educational Video Generator

An automated system to generate multilingual educational videos using AI services including Amazon Polly for text-to-speech, Azure OpenAI for translations, and Azure Stable Diffusion for thumbnail and section image generation.

## Project Overview

This project creates educational videos with synchronized text highlighting from simple template files. The system automatically translates content into multiple languages, generates professional voiceover using Amazon Polly, creates videos with real-time word highlighting, produces custom thumbnails, and embeds section-specific background images using Azure Stable Diffusion.

## Features

- **Template-Based Video Generation**: Create videos from simple text templates with SSML support
- **Professional Text-to-Speech**: Utilize Amazon Polly neural voices for natural-sounding narration
- **Real-Time Word Highlighting**: Synchronize highlighted text with speech
- **Multilingual Support**: Generate videos in multiple languages (English, German, Spanish, French, Korean)
- **Automatic Translation**: Translate content using Azure OpenAI
- **Language-Specific Font Support**: Properly display text in various languages, including Korean
- **Custom Thumbnail Generation**: Create professional thumbnails using Azure Stable Diffusion
- **Section Background Images**: Generate and display content-specific background images
- **Video ID System**: Unique ID generation for each video with organized output structure
- **Language-Specific Output Folders**: Separate folders for each language's content

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
│   └── {video-id}/          # Unique ID for each video generation
│       ├── section_images/  # Background images for each section
│       │   ├── elephant_en.jpg
│       │   ├── lion_en.jpg
│       │   └── ...
│       ├── en/              # English output
│       │   ├── speech.mp3   # Generated English audio
│       │   ├── timings.json # English word timing information
│       │   ├── video.mp4    # Final English video
│       │   └── thumbnail.jpg # Generated English thumbnail
│       ├── de/              # German output
│       │   └── ...          # Similar files for German
│       ├── es/              # Spanish output
│       ├── fr/              # French output
│       ├── ko/              # Korean output
│       └── manifest.json    # Information about the generation
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

### Section Images

The `#images_scenario` section defines background images for different parts of your video:

- **section**: Name of the section (should match the marker names in SSML content)
- **prompt**: The prompt for Azure Stable Diffusion to generate an appropriate image
- **description**: Description of when the image should be displayed (for documentation)

In your SSML content, use `<mark name="section_name_start"/>` and `<mark name="section_name_end"/>` tags to indicate where each section begins and ends. The system will display the corresponding section image during that portion of the video.

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

Parses template files, extracting metadata, section image definitions, and SSML content for processing.

### Translator

Uses Azure OpenAI to translate template content into multiple languages.

### Polly Generator

Integrates with Amazon Polly to generate speech from SSML content and extract word timing information.

### Video Generator

Creates video frames with synchronized text and highlights the current word being spoken. Now supports background section images that change based on SSML markers.

### Image Generator

Uses Azure Stable Diffusion to generate professional thumbnails and section-specific background images based on template prompts.

## Video ID System

Each video generation creates a unique ID based on:

- Title of the video (slugified)
- Timestamp
- Short UUID

Example: `5-amazing-animals-3421-a7b8c9d0`

All output files are organized under this ID in the output directory, with separate folders for each language.

## Thumbnail Generation Details

The thumbnail generation process uses Azure Stable Diffusion with the following specifics:

1. Each template includes a `thumbnail_prompt` field with detailed instructions for the image generation
2. The system generates thumbnails in the specified dimensions (resizing to 1280x720 if needed)
3. Thumbnails are saved as JPG files in the language-specific directory
4. Each language gets its own thumbnail with localized text
5. The original English prompt is preserved for all languages to ensure high-quality results

## Section Image Generation Details

The section image generation process works as follows:

1. Each template includes an `#images_scenario` section with image prompts for each content section
2. The system generates high-quality images using Azure Stable Diffusion (1920x1080)
3. Section images are displayed as backgrounds during the corresponding sections of the video
4. Text is shown with a semi-transparent background for readability
5. Transitions between sections are handled automatically

## Future Features

The following features are planned for future implementation:

1. **Animated Transitions**

   - Add smooth transitions between sections
   - Implement fade effects for images and text

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
