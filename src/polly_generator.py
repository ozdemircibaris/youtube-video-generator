"""
Amazon Polly integration for text-to-speech with word timing information.
"""

import boto3
import json
import time
import os
from botocore.exceptions import BotoCoreError, ClientError
import traceback

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
        Generate speech from SSML text and save word timing information using asynchronous API.
        
        Args:
            ssml_text (str): SSML text to convert to speech
            voice_id (str): Amazon Polly voice ID
            output_path (str): Path to save audio file
            word_timings_path (str): Path to save word timings JSON file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("Starting asynchronous speech synthesis with Amazon Polly...")
            
            # Generate audio file
            response = self.polly_client.start_speech_synthesis_task(
                Engine='neural',
                OutputFormat=config.POLLY_OUTPUT_FORMAT,
                SampleRate=config.POLLY_SAMPLE_RATE,
                Text=ssml_text,
                TextType='ssml',
                VoiceId=voice_id,
                OutputS3BucketName='youtube-video-tts',  
                OutputS3KeyPrefix='audio/'
            )
            
            audio_task_id = response['SynthesisTask']['TaskId']
            print(f"Audio synthesis task ID: {audio_task_id}")
            
            # Generate speech marks for word timing
            marks_response = self.polly_client.start_speech_synthesis_task(
                Engine='neural',
                OutputFormat='json',
                Text=ssml_text,
                TextType='ssml',
                VoiceId=voice_id,
                SpeechMarkTypes=['word', 'ssml'],  # Both 'word' and 'ssml' type markers
                OutputS3BucketName='youtube-video-tts',
                OutputS3KeyPrefix='speechmarks/'
            )
            
            marks_task_id = marks_response['SynthesisTask']['TaskId']
            print(f"Speech marks task ID: {marks_task_id}")
            
            # Wait for tasks to complete
            audio_output_uri = self._wait_for_task_completion(audio_task_id)
            marks_output_uri = self._wait_for_task_completion(marks_task_id)
            
            if not audio_output_uri or not marks_output_uri:
                print("One of the synthesis tasks failed")
                return False
            
            # Download files from S3
            if not self._download_from_s3(audio_output_uri, output_path):
                print("Failed to download audio from S3")
                return False
                
            # Parse and process speech marks
            speech_marks = self._download_and_process_speech_marks(marks_output_uri, word_timings_path)
            
            if not speech_marks:
                print("Failed to process speech marks")
                return False
                
            return True
                
        except (BotoCoreError, ClientError) as error:
            print(f"Error in speech synthesis: {error}")
            return False
        
    def _wait_for_task_completion(self, task_id, max_tries=60):
        """
        Wait for a speech synthesis task to complete.
        
        Args:
            task_id (str): The task ID to check
            max_tries (int): Maximum number of attempts
            
        Returns:
            str: The S3 URI of the output file, or None if failed
        """
        print(f"Waiting for task {task_id} to complete...")
        
        for i in range(max_tries):
            try:
                response = self.polly_client.get_speech_synthesis_task(TaskId=task_id)
                task_status = response['SynthesisTask']['TaskStatus']
                
                print(f"Task {task_id} status: {task_status}")
                
                if task_status == 'completed':
                    return response['SynthesisTask']['OutputUri']
                elif task_status == 'failed':
                    print(f"Task failed: {response['SynthesisTask'].get('TaskStatusReason', 'Unknown reason')}")
                    return None
                    
                # Wait before checking again
                time.sleep(2)
                
            except (BotoCoreError, ClientError) as error:
                print(f"Error checking task status: {error}")
                return None
                
        print(f"Task {task_id} did not complete within the timeout period")
        return None
        
    def _download_from_s3(self, s3_uri, local_path):
        """
        Download a file from S3 to a local path.
        
        Args:
            s3_uri (str): The S3 URI of the file (HTTPS URL or s3:// format)
            local_path (str): The local path to save the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"Downloading file from {s3_uri} to {local_path}")
            
            # Parse the S3 URI based on format
            if s3_uri.startswith('https://'):
                # Handle HTTPS URL format from Amazon Polly
                # URL format: https://s3.REGION.amazonaws.com/BUCKET/KEY
                parts = s3_uri.replace('https://', '').split('/', 1)
                domain_parts = parts[0].split('.')
                bucket = parts[1].split('/', 1)[0]
                key = parts[1].split('/', 1)[1]
            elif s3_uri.startswith('s3://'):
                # Handle s3:// format
                s3_parts = s3_uri.replace('s3://', '').split('/', 1)
                bucket = s3_parts[0]
                key = s3_parts[1]
            else:
                print(f"Unsupported URI format: {s3_uri}")
                return False
            
            print(f"Parsed S3 location - Bucket: {bucket}, Key: {key}")
            
            # Create S3 client
            s3_client = boto3.client('s3',
                aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                region_name=config.AWS_REGION
            )
            
            # Download the file
            s3_client.download_file(bucket, key, local_path)
            print(f"File downloaded successfully to {local_path}")
            return True
            
        except Exception as e:
            print(f"Error downloading file from S3: {e}")
            return False
            
    def _download_and_process_speech_marks(self, s3_uri, output_path):
        """
        Download and process speech marks from S3.
        
        Args:
            s3_uri (str): The S3 URI of the speech marks file
            output_path (str): Path to save processed word timings
            
        Returns:
            list: Processed word timings, or None if failed
        """
        try:
            # Create a temporary file for the raw speech marks
            temp_marks_file = os.path.join(config.OUTPUT_DIR, "temp_speech_marks.json")
            
            # Download the raw speech marks
            if not self._download_from_s3(s3_uri, temp_marks_file):
                return None
                
            # Process the speech marks
            with open(temp_marks_file, 'r') as f:
                speech_marks_data = f.read()
            
            # Save the raw speech marks for debugging
            raw_debug_file = os.path.join(os.path.dirname(output_path), "raw_speech_marks.txt")
            with open(raw_debug_file, 'w') as f:
                f.write(speech_marks_data)
            print(f"Saved raw speech marks to {raw_debug_file} for debugging")
                
            words_with_time = []
            
            # First pass: Extract words and their start times
            for line in speech_marks_data.split('\n'):
                if line.strip():
                    try:
                        mark = json.loads(line)
                        print(f"Processing mark: {mark}")  # Debug output to see all marks
                        
                        # Process both 'word' and 'ssml' type marks
                        if mark['type'] == 'word':
                            words_with_time.append({
                                'word': mark['value'],
                                'start_time': mark['time']
                            })
                        elif mark['type'] == 'ssml':
                            # Handle SSML marks (for section markers)
                            value = mark['value']
                            print(f"SSML mark value: {value}")  # Debug output
                            
                            # Check all possible formats of SSML marker values
                            if value.startswith('mark:'):
                                marker_name = value.replace('mark:', '')
                                print(f"Found mark tag: {marker_name}")
                                words_with_time.append({
                                    'word': marker_name,
                                    'start_time': mark['time']
                                })
                            # Alternative format sometimes returned by Polly
                            elif '_start' in value or '_end' in value:
                                print(f"Found direct marker: {value}")
                                words_with_time.append({
                                    'word': value,
                                    'start_time': mark['time']
                                })
                            else:
                                print(f"Unknown SSML mark format: {value}")
                    except json.JSONDecodeError as e:
                        print(f"Error parsing speech mark: {line}")
                        print(f"Error: {e}")
                        return None
            
            # Second pass: Calculate durations
            word_timings = []
            for i in range(len(words_with_time)):
                current_word = words_with_time[i]
                
                if i < len(words_with_time) - 1:
                    next_word = words_with_time[i + 1]
                    duration = next_word['start_time'] - current_word['start_time'] - 20
                else:
                    duration = 500  # 500ms for the last word
                
                word_timings.append({
                    'word': current_word['word'],
                    'start_time': current_word['start_time'],
                    'end_time': current_word['start_time'] + duration,
                    'duration': duration
                })
            
            # Save processed speech marks
            with open(output_path, 'w') as f:
                json.dump(word_timings, f, indent=2)
                
            print(f"Processed {len(word_timings)} word timings and saved to {output_path}")
            return word_timings
                
        except Exception as e:
            print(f"Error processing speech marks: {e}")
            traceback.print_exc()  # Daha detaylı hata mesajı için
            return None