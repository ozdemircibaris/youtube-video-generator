"""
Amazon Polly integration for text-to-speech with word timing information.
"""

import boto3
import json
import time
import os
from botocore.exceptions import BotoCoreError, ClientError

from src import config


class PollyGenerator:
    def __init__(self):
        """Initialize Amazon Polly client."""
        self.polly_client = boto3.client(
            'polly',
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region_name=config.AWS_REGION
        )
    
    def generate_speech(self, ssml_text, voice_id, output_path, word_timings_path):
        """
        Generate speech from SSML text and save word timing information.
        
        Args:
            ssml_text (str): SSML text to convert to speech
            voice_id (str): Amazon Polly voice ID
            output_path (str): Path to save audio file
            word_timings_path (str): Path to save word timings JSON file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("Generating speech with Amazon Polly...")
            # Generate speech directly instead of using a task
            response = self.polly_client.synthesize_speech(
                Engine='neural',
                OutputFormat=config.POLLY_OUTPUT_FORMAT,
                SampleRate=config.POLLY_SAMPLE_RATE,
                Text=ssml_text,
                TextType='ssml',
                VoiceId=voice_id
            )
            
            # Save the audio stream to file
            if "AudioStream" in response:
                with open(output_path, 'wb') as file:
                    file.write(response["AudioStream"].read())
                print(f"Speech audio saved to {output_path}")
                
                # Get speech marks for word timing
                speech_marks = self._get_speech_marks(ssml_text, voice_id)
                
                if not speech_marks:
                    print("Failed to get speech marks from Polly")
                    return False
                
                # Save speech marks to file
                with open(word_timings_path, 'w') as f:
                    json.dump(speech_marks, f, indent=2)
                print(f"Word timings saved to {word_timings_path}")
                
                return True
            else:
                print("No AudioStream found in the response")
                return False
                
        except (BotoCoreError, ClientError) as error:
            print(f"Error in speech synthesis: {error}")
            return False
    
    def _get_speech_marks(self, ssml_text, voice_id):
        """
        Get speech marks for word timing.
        
        Args:
            ssml_text (str): SSML text
            voice_id (str): Amazon Polly voice ID
            
        Returns:
            list: List of word timing information
        """
        try:
            print("Getting word timing information...")
            
            # Create a temporary file for speech marks
            temp_speech_marks_file = os.path.join(config.OUTPUT_DIR, "temp_speech_marks.txt")
            
            response = self.polly_client.synthesize_speech(
                Engine='neural',
                OutputFormat='json',
                Text=ssml_text,
                TextType='ssml',
                VoiceId=voice_id,
                SpeechMarkTypes=['word']
            )
            
            # Parse the speech marks from the response
            word_timings = []
            previous_end_time = 0
            
            if 'AudioStream' in response:
                speech_marks_data = response['AudioStream'].read().decode('utf-8')
                
                # Save raw speech marks for debugging
                with open(temp_speech_marks_file, 'w') as f:
                    f.write(speech_marks_data)
                
                words_with_time = []
                
                # First pass: Extract words and their start times
                for line in speech_marks_data.split('\n'):
                    if line.strip():
                        try:
                            mark = json.loads(line)
                            if mark['type'] == 'word':
                                words_with_time.append({
                                    'word': mark['value'],
                                    'start_time': mark['time']
                                })
                        except json.JSONDecodeError as e:
                            print(f"Error parsing speech mark: {line}")
                            print(f"Error: {e}")
                            return []
                
                # Second pass: Calculate durations based on next word start time
                for i in range(len(words_with_time)):
                    current_word = words_with_time[i]
                    
                    # For all words except the last one
                    if i < len(words_with_time) - 1:
                        next_word = words_with_time[i + 1]
                        # Duration is the time until the next word starts
                        # Subtract a small gap
                        duration = next_word['start_time'] - current_word['start_time'] - 20
                    else:
                        # For the last word, use a fixed duration
                        duration = 500  # 500ms for the last word
                    
                    word_timings.append({
                        'word': current_word['word'],
                        'start_time': current_word['start_time'],
                        'end_time': current_word['start_time'] + duration,
                        'duration': duration
                    })
            
            print(f"Retrieved {len(word_timings)} word timings")
            return word_timings
                
        except (BotoCoreError, ClientError) as error:
            print(f"Error getting speech marks: {error}")
            return []