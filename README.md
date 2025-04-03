# YouTube Video Generator

This tool automatically creates educational videos from text input, adds synchronized captions, and can upload them directly to YouTube.

## Input Format

Input files should be placed in the `input` directory and follow this format:

```
#title: Your Video Title
#english_level: intermediate
#voice: en-US-Neural2-F
#description: Your video description here.
You can write multiple lines for descriptions
and they will be properly joined together.

#tags: tag1,tag2,tag3,tag4

This is the main content of your video. This text will be converted to speech.

You can write as much text as you need, using multiple paragraphs.

The system will automatically split your content into sentences and
synchronize them with the speech in the final video.
```

### Important Formatting Rules:

1. **Parameters** start with a `#` symbol followed by a parameter name, a colon, and the value.
2. Multi-line parameter values are supported - just continue writing in the next line without adding a `#`.
3. **Leave an empty line** between parameter blocks and the main content.
4. Main content can span multiple paragraphs and will be properly processed.

### Available Parameters:

- `title`: The title of your video
- `english_level`: (beginner, intermediate, advanced, proficient) - affects speech rate
- `voice`: Google Text-to-Speech voice name (e.g., en-US-Neural2-F)
- `description`: YouTube video description
- `tags`: Comma-separated list of tags for the video

## Usage

```bash
# Generate video from input file
python -m src.main input/your_input_file.txt

# Generate and upload to YouTube
python -m src.main input/your_input_file.txt --upload

# Generate with custom output filename
python -m src.main input/your_input_file.txt --output custom_name.mp4

# Generate a YouTube Shorts version too
python -m src.main input/your_input_file.txt --shorts
```

## Example

Check out `input/template.txt` for a detailed example of a properly formatted input file.

---
