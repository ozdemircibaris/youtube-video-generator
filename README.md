# README

## Project Overview

This project is a local video generation application for YouTube. The application takes text input along with additional parameters and generates a video using the following steps:

1. **Text Processing**: The application reads text from a file, which includes the main content and an English level parameter.
2. **Audio Generation**: Using Google Text-to-Speech API, the text is converted into speech. The speech rate is adjusted based on the English level.
3. **Time-Pointing**: `enable_time_pointing` is enabled in the API to extract precise word timing.
4. **Video Creation**:
   - A black background is used.
   - White text is displayed with highlighted words as they are spoken.
   - Sentences are shown progressively, with a maximum of 5 words per line.
   - The text is center-aligned both horizontally and vertically.
5. **Final Video Composition**:
   - An intro video from the `assets` folder is added at the beginning.
   - The generated content video is placed in the middle.
   - An outro video from the `assets` folder is added at the end.
   - A background music file (`background-music.mp3`) is played at 30% volume, with potential adjustments during the intro.
6. **Export & Upload**:
   - The final video is exported in 1080p.
   - The video is uploaded to YouTube using the YouTube API.
   - The title is set manually, while the description and tags are automatically generated for better audience reach.

---
