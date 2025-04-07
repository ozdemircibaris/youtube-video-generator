import os
import json
import boto3
import tempfile
import time
import pydub
import re
import subprocess
from src.config import (
    OUTPUT_DIR, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, 
    AWS_REGION, ENGLISH_LEVEL_RATES
)

def add_ssml_markup(text, engine="neural"):
    """
    Convert plain text to SSML with enhanced speech features
    
    Args:
        text (str): Raw text content
        engine (str): "neural" veya "standard" olabilir
        
    Returns:
        str: Text with SSML markup for better speech quality
    """
    # Neural engine için daha basit SSML kullanın
    if engine == "neural":
        return add_simple_ssml_markup(text)
    
    # Standard engine için tam SSML kullanabilirsiniz
    processed_text = text
    
    # Split into paragraphs
    paragraphs = processed_text.split("\n\n")
    processed_paragraphs = []
    
    for paragraph in paragraphs:
        # Skip empty paragraphs
        if not paragraph.strip():
            continue
            
        # Check if this is character dialogue
        is_dialogue = False
        speaker = None
        
        # Detect dialogue (in quotes or starting with dash)
        if '"' in paragraph or "'" in paragraph:
            is_dialogue = True
        elif paragraph.strip().startswith("-") or paragraph.strip().startswith("‚Äö√Ñ√Æ"):
            is_dialogue = True
            
        # Try to detect who is speaking
        if is_dialogue:
            # Look for a name and "said", "asked" etc. in the first few words
            words = paragraph.split()
            for i, word in enumerate(words[:5]):
                if word.endswith(',') and i+1 < len(words) and words[i+1].lower() in ["said", "asked", "whispered", "shouted", "replied"]:
                    speaker = word[:-1]  # Remove comma
                    break
        
        # Determine dialogue style
        dialogue_style = ""
        if is_dialogue:
            if speaker:
                # Set voice properties based on speaker
                if any(young_word in speaker.lower() for young_word in ["boy", "girl", "young", "child", "kid", "leo"]):
                    # Young character voice
                    dialogue_style = '<prosody rate="medium" pitch="+2st">'
                elif any(old_word in speaker.lower() for old_word in ["old", "elder", "ancient", "shopkeeper"]):
                    # Elderly character voice
                    dialogue_style = '<prosody rate="slow" pitch="-2st">'
                else:
                    # Default character voice
                    dialogue_style = '<prosody rate="medium">'
            else:
                # Default dialogue style if speaker not identified
                dialogue_style = '<prosody rate="medium">'
        
        # Process sentences within the paragraph
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        processed_sentences = []
        
        for sentence in sentences:
            processed = sentence
            
            # Add pauses based on punctuation
            processed = re.sub(r'([.!?])\s*$', r'\1<break time="700ms"/>', processed)
            processed = re.sub(r'([,;:])\s', r'\1<break time="350ms"/> ', processed)
            processed = re.sub(r'([‚Äö√Ñ√Æ-])\s', r'\1<break time="250ms"/> ', processed)
            
            # Add emphasis to quoted text in dialogue
            if is_dialogue:
                processed = re.sub(r'"([^"]+)"', r'<emphasis level="moderate">\1</emphasis>', processed)
                processed = re.sub(r"'([^']+)'", r'<emphasis level="moderate">\1</emphasis>', processed)
            
            # Add intonation changes for questions and exclamations
            if processed.strip().endswith('?'):
                processed = f'<prosody pitch="high">{processed}</prosody>'
            elif processed.strip().endswith('!'):
                processed = f'<prosody volume="loud" rate="quick">{processed}</prosody>'
            
            processed_sentences.append(processed)
        
        # Rejoin sentences
        processed_paragraph = " ".join(processed_sentences)
        
        # Wrap paragraph with dialogue style
        if is_dialogue and dialogue_style:
            processed_paragraph = f"{dialogue_style}{processed_paragraph}</prosody>"
        
        processed_paragraphs.append(processed_paragraph)
    
    # Add appropriate spacing between paragraphs
    final_text = '<break time="600ms"/>'.join(processed_paragraphs)
    
    # Special case processing
    final_text = re.sub(r'\.\.\.\s*', '...<break time="900ms"/>', final_text)  # Long pause for ellipsis
    
    # Add emphasis for special words
    emphasis_words = ["strange", "mysterious", "secret", "discovered", "amazing", "treasure", "hidden"]
    for word in emphasis_words:
        final_text = re.sub(rf'\b{word}\b', f'<emphasis level="moderate">{word}</emphasis>', final_text, flags=re.IGNORECASE)
    
    # Final SSML tag
    return f'<speak>{final_text}</speak>'

def add_simple_ssml_markup(text):
    """
    Add only basic SSML markup that is well-supported in Neural engine
    """
    # Split into paragraphs
    paragraphs = text.split("\n\n")
    processed_paragraphs = []
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        
        # Add simple breaks for punctuation
        processed = paragraph
        processed = re.sub(r'([.!?])\s+', r'\1<break time="500ms"/> ', processed)
        processed = re.sub(r'([,;:])\s+', r'\1<break time="300ms"/> ', processed)
        
        processed_paragraphs.append(processed)
    
    # Join paragraphs with longer breaks
    final_text = '<break time="700ms"/>'.join(processed_paragraphs)
    
    return f'<speak>{final_text}</speak>'

def get_audio_duration(file_path):
    """Get audio duration using multiple methods"""
    # Try pydub first
    try:
        audio = pydub.AudioSegment.from_file(file_path)
        return audio.duration_seconds
    except Exception as pydub_error:
        print(f"Warning: Could not load audio with pydub: {pydub_error}")
    
    # Try ffprobe next
    try:
        cmd = ['ffprobe', '-i', file_path, '-show_entries', 'format=duration', '-v', 'quiet', '-of', 'csv=p=0']
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception as ffprobe_error:
        print(f"Could not determine audio duration with ffprobe: {ffprobe_error}")
    
    # Finally, estimate from file size
    try:
        file_size = os.path.getsize(file_path)
        # MP3 için kabaca bit hızı tahmini (128 kbps)
        return file_size * 8 / (128 * 1024)
    except Exception as size_error:
        print(f"Could not estimate duration from file size: {size_error}")
        # Default value
        return 10.0  # Arbitrary default

def generate_speech(text, output_filename, english_level='intermediate', voice_name='Joanna', use_neural=True):
    """
    Generate speech from text using Amazon Polly with word timing information
    
    Args:
        text (str): The text to convert to speech
        output_filename (str): Output audio filename
        english_level (str): English proficiency level (beginner, intermediate, advanced, proficient)
        voice_name (str): Voice name to use (Joanna, Matthew, etc.)
        use_neural (bool): Whether to use the neural engine (True) or standard engine (False)
    
    Returns:
        dict: Word timing information for synchronization
        str: Path to the generated audio file
    """
    # Get speech rate based on English level
    speech_rates = ENGLISH_LEVEL_RATES
    speech_rate = speech_rates.get(english_level.lower(), '0.8')
    print(f"Using speech rate: {speech_rate} for English level: {english_level}")
    
    # Engine selection
    engine = "neural" if use_neural else "standard"
    print(f"Using Polly {engine} engine")
    
    # Check for AWS credentials
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        print("WARNING: AWS credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        print("in your environment variables or .env file.")
        return None, None
    
    # Initialize the Amazon Polly client
    try:
        polly_client = boto3.client('polly',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
    except Exception as e:
        print(f"Error initializing Amazon Polly client: {e}")
        return None, None
    
    # Add SSML markup to the text
    ssml_text = add_ssml_markup(text, engine)
    print("SSML markup applied to text")
    
    # Output path for audio file
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    try:
        # Request speech synthesis
        response = polly_client.synthesize_speech(
            Text=ssml_text,
            TextType="ssml",
            OutputFormat="mp3",
            VoiceId=voice_name,
            Engine=engine,
            SampleRate="24000",
            LexiconNames=[],
        )
        
        # Check if the request was successful
        if "AudioStream" in response:
            # Save the audio to a file
            with open(output_path, 'wb') as file:
                file.write(response["AudioStream"].read())
            print(f"Audio file saved to {output_path}")
            
            # Verify the audio file
            audio_duration = get_audio_duration(output_path)
            if audio_duration:
                print(f"Audio duration: {audio_duration:.2f} seconds")
            else:
                print("Warning: Could not determine audio duration")
        else:
            raise Exception("Response did not contain AudioStream")
    
    except Exception as e:
        print(f"Error generating speech audio: {e}")
        # Try with standard engine if neural failed
        if use_neural:
            print("Retrying with standard engine...")
            return generate_speech(text, output_filename, english_level, voice_name, use_neural=False)
        return None, None
    
    # Now request speech marks for word timing
    try:
        # Create a temporary file for speech marks
        temp_marks_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        temp_marks_path = temp_marks_file.name
        temp_marks_file.close()
        
        # Request speech marks
        response = polly_client.synthesize_speech(
            Text=ssml_text,
            TextType="ssml",
            OutputFormat="json",
            VoiceId=voice_name,
            Engine=engine,
            SpeechMarkTypes=["word"],
            SampleRate="24000",
        )
        
        # Save speech marks to file
        if "AudioStream" in response:
            with open(temp_marks_path, 'wb') as file:
                file.write(response["AudioStream"].read())
            print(f"Speech marks saved to temporary file: {temp_marks_path}")
        else:
            raise Exception("Response did not contain AudioStream for speech marks")
            
        # Parse speech marks to extract word timing
        word_positions = []
        with open(temp_marks_path, 'r') as file:
            lines = file.readlines()
            for line in lines:
                mark = json.loads(line)
                if mark['type'] == 'word':
                    # SSML etiketlerini temizle
                    clean_word = re.sub(r'<[^>]+>', '', mark['value'])
                    
                    # Time is in milliseconds, convert to seconds
                    start_time = mark['time'] / 1000.0
                    
                    # Polly bazen 'duration' değeri sağlamıyor
                    if 'duration' in mark:
                        duration = mark['duration'] / 1000.0
                    else:
                        # Temizlenmiş kelime uzunluğuna göre tahmin
                        duration = len(clean_word) * 0.05
                    
                    end_time = start_time + duration
                    
                    word_positions.append({
                        'word': clean_word,  # Temizlenmiş kelimeyi kullan
                        'start_time': start_time,
                        'end_time': end_time
                    })
        
        # Clean up temporary file
        os.unlink(temp_marks_path)
        
        # If no word positions were found, estimate them based on audio length
        if not word_positions:
            print("No word timing marks found. Estimating based on audio duration...")
            words = text.split()
            
            # Get audio duration if it exists
            audio_duration = get_audio_duration(output_path)
            if not audio_duration:
                audio_duration = 10.0  # Default duration if can't determine
                print(f"Using default audio duration: {audio_duration}s")
            
            # Create estimated word timings
            word_duration = audio_duration / len(words)
            
            word_positions = []
            current_time = 0
            
            for word in words:
                end_time = current_time + word_duration
                word_positions.append({
                    'word': word,
                    'start_time': current_time,
                    'end_time': end_time
                })
                current_time = end_time
                
        # Print timing information
        print("\nWord timing information:")
        print("---------------------------------")
        for i, wp in enumerate(word_positions[:5]):  # Show first 5 words
            print(f"{wp['word']:<15}\t{wp['start_time']:.2f}s\t{wp['end_time']:.2f}s")

        if len(word_positions) > 5:
            print(f"... and {len(word_positions) - 5} more words")

        print(f"\nTotal speech duration: {word_positions[-1]['end_time']:.2f} seconds")
        print(f"Number of words: {len(word_positions)}")

        # Make sure every word has a unique timing slot
        for i in range(len(word_positions)-1):
            if word_positions[i]['end_time'] > word_positions[i+1]['start_time']:
                word_positions[i]['end_time'] = word_positions[i+1]['start_time']

        return word_positions, output_path
    
    except Exception as e:
        print(f"Error generating speech marks: {e}")
        
        # Even if speech marks fail, return the audio path with simple estimated timing
        if os.path.exists(output_path):
            print("Falling back to estimated word timings...")
            words = text.split()
            
            # Get audio duration
            audio_duration = get_audio_duration(output_path)
            if not audio_duration:
                audio_duration = 10.0  # Default duration if can't determine
                print(f"Using default audio duration: {audio_duration}s")
            
            word_positions = []
            word_duration = audio_duration / len(words)
            current_time = 0
            
            for word in words:
                end_time = current_time + word_duration
                word_positions.append({
                    'word': word,
                    'start_time': current_time,
                    'end_time': end_time
                })
                current_time = end_time
            
            print(f"Created estimated word timings based on audio duration: {audio_duration:.2f}s")
            return word_positions, output_path
        
        return None, None