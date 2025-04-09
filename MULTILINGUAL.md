# Multilingual Video Generation Guide

This guide explains how to use the multilingual functionality of the YouTube Video Generator to create videos in multiple languages from a single template.

## Supported Languages

The system currently supports the following languages:

- **English**: Default source language, using Matthew (male) voice
- **Korean**: Translated using Azure OpenAI, using Seoyeon (female) voice
- **German**: Translated using Azure OpenAI, using Daniel (male) voice
- **Spanish**: Translated using Azure OpenAI, using Lucia (female) voice
- **French**: Translated using Azure OpenAI, using Remi (male) voice

## Quick Start

To generate a video in a specific language:

```bash
python -m src.main input/template.txt --language korean
```

To generate videos in all supported languages simultaneously:

```bash
python -m src.main input/template.txt --all-languages
```

## Testing the Translation Only

If you want to test the translation functionality without generating videos:

```bash
./test_multilingual.py input/template.txt --translation-only
```

This will create translated template files for all supported languages in the same directory as your input file.

## Customizing Voice Selection

By default, the system selects appropriate Amazon Polly voices for each language. If you want to override the voice selection, you can specify a voice in your template file using the Amazon Polly voice name directly:

```
#voice: Matthew  # English male voice
#voice: Joanna   # English female voice
#voice: Seoyeon  # Korean female voice
#voice: Daniel   # German male voice
#voice: Lucia    # Spanish female voice
#voice: Remi     # French male voice
```

The system no longer requires Google TTS voice names (like en-US-Neural2-D), and you should use Amazon Polly voice names directly in all templates.

For Korean specifically, the system uses the Noto Serif Korean font for text display, ensuring proper rendering of Korean characters.

## Full Example

1. Create a template file in English:

```
#title: The Surprise Chef | A2 English Story
#english_level: beginner
#voice: Matthew
#description: Practice your English with this fun story!
#tags: EnglishStory, LearnEnglish

#content: This is a story about a chef.
The chef works in a restaurant.
He loves to cook delicious food.
```

2. Generate videos in all languages with YouTube Shorts versions:

```bash
./test_multilingual.py input/your_template.txt --all-languages --shorts
```

3. This will create:
   - Video files for each language (English, Korean, German, Spanish, French)
   - Shorts versions of each video
   - Translated template files for future use

## Troubleshooting

If you encounter issues:

1. **Error with Azure OpenAI API**: Check your `.env` file to ensure the API keys and endpoints are correctly configured.

2. **Font rendering issues**: Ensure the Noto Serif Korean font is in the `assets/fonts` directory.

3. **Missing voice**: Check if the AWS Polly service has the specific voice you're trying to use.

4. **Incomplete translation**: If a translation is cut off, the content might be too long for a single API call. Try breaking it into smaller templates.

## Azure OpenAI Configuration

Make sure your `.env` file includes:

```
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_API_VERSION=2023-05-15
AZURE_OPENAI_COMPLETION_DEPLOYMENT=gpt-4o-new
```

You can change the deployment model as needed based on what's available in your Azure OpenAI service.
