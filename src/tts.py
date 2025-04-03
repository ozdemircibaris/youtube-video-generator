import os
import json
import requests
import base64
import time
from src.config import GOOGLE_TTS_API_KEY, ENGLISH_LEVEL_RATES, OUTPUT_DIR

def generate_speech(text, output_filename, english_level='intermediate', voice_name='en-US-Neural2-F'):
    """
    Generate speech from text using Google Text-to-Speech API
    
    Args:
        text (str): The text to convert to speech
        output_filename (str): Output audio filename
        english_level (str): English proficiency level (beginner, intermediate, advanced, proficient)
        voice_name (str): Voice name to use
    
    Returns:
        dict: Word timing information for synchronization
    """
    # Get speech rate based on English level
    speech_rate = ENGLISH_LEVEL_RATES.get(english_level.lower(), 1.0)
    print(f"Using speech rate: {speech_rate} for English level: {english_level}")
    
    # Prepare request data
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}"
    
    # Add SSML tags for timepointing
    ssml_text = f'<speak>{text}</speak>'
    
    request_data = {
        "input": {"ssml": ssml_text},
        "voice": {
            "languageCode": "en-US",
            "name": voice_name
        },
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": speech_rate,
            "effectsProfileId": ["small-bluetooth-speaker-class-device"],
            "pitch": 0
        }
    }
    
    # Make API request
    print("Sending request to Google TTS API...")
    response = requests.post(url, json=request_data)
    
    if response.status_code != 200:
        raise Exception(f"Error from Google TTS API: {response.text}")
    
    # Parse response
    response_data = response.json()
    
    # Convert audio content from base64
    audio_content = base64.b64decode(response_data.get("audioContent", ""))
    
    # Save the audio file
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    with open(output_path, 'wb') as out:
        out.write(audio_content)
    
    print(f"Audio file saved to {output_path}")
    
    # For REST API without time points, we need to simulate timepoints
    # We'll create more realistic word timing estimates
    words = text.split()
    total_chars = sum(len(word) for word in words)
    
    # Getting the audio file duration would be the most accurate approach
    # For now, use an estimate based on speech rate and text length
    estimated_total_duration = (total_chars / 15) / speech_rate  # ~15 chars per second at normal rate
    print(f"Estimated audio duration: {estimated_total_duration:.2f} seconds for {len(words)} words")
    print(f"Average word duration: {estimated_total_duration/len(words):.3f} seconds per word")
    
    # Use a more sophisticated approach for time estimation
    # Slower words at the beginning and end, faster in the middle
    # Also account for word length
    word_positions = []
    
    # Let's use a more realistic timing model
    # Average speaking rate is about 150 words per minute = 2.5 words per second
    # So each word takes about 0.4 seconds on average
    # Adjust for word length: longer words take more time
    base_word_duration = 0.4 / speech_rate  # adjust for speech rate
    
    print("\nDetailed word timing information:")
    print("---------------------------------")
    print("Word\t\tStart\tEnd\tDuration")
    print("---------------------------------")
    
    current_time = 0
    for i, word in enumerate(words):
        # Calculate duration based on word length and position
        # Add some randomness to make it more natural
        word_length_factor = len(word) / 5  # adjust for word length (5 chars is baseline)
        position_factor = 1.0  # default
        
        # Words at sentence boundaries tend to be slower
        if i == 0 or i == len(words) - 1 or "." in word or "," in word:
            position_factor = 1.2  # slower at boundaries or punctuation
        
        # Calculate duration with all factors
        word_duration = base_word_duration * max(0.8, min(1.5, word_length_factor * position_factor))
        
        # For very short words like "a", "the", ensure minimum duration
        if len(word) <= 2:
            word_duration = max(word_duration, 0.2 / speech_rate)
        
        # For longer words, cap the maximum duration
        if len(word) > 8:
            word_duration = min(word_duration, 0.7 / speech_rate)
        
        # Store the timing information
        word_positions.append({
            'word': word,
            'start_time': current_time,
            'end_time': current_time + word_duration
        })
        
        # Log the timing info
        print(f"{word:<15}\t{current_time:.2f}\t{current_time + word_duration:.2f}\t{word_duration:.2f}")
        
        # Update time for next word
        current_time += word_duration
    
    # Adjust to match estimated duration if needed
    actual_duration = word_positions[-1]['end_time']
    if abs(actual_duration - estimated_total_duration) > 1.0:
        scale_factor = estimated_total_duration / actual_duration
        print(f"\nAdjusting word durations by factor {scale_factor:.2f} to match estimated audio duration")
        
        new_current_time = 0
        for wp in word_positions:
            word_duration = (wp['end_time'] - wp['start_time']) * scale_factor
            wp['start_time'] = new_current_time
            wp['end_time'] = new_current_time + word_duration
            new_current_time += word_duration
    
    print(f"\nTotal speech duration: {word_positions[-1]['end_time']:.2f} seconds")
    print(f"Number of words: {len(words)}")
    
    # Final verification
    print("\nVerification:")
    print(f"First word starts at: {word_positions[0]['start_time']:.2f}")
    print(f"Last word ends at: {word_positions[-1]['end_time']:.2f}")
    print(f"Time per word: {word_positions[-1]['end_time']/len(words):.2f} seconds")
    
    return word_positions, output_path 