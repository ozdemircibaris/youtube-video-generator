"""
Translator module for translating template content using Azure OpenAI.
"""

import os
import json
import requests
import re
import sys
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Translator:
    def __init__(self):
        """Initialize the translator with Azure OpenAI credentials."""
        self.api_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        self.api_key = os.getenv('AZURE_OPENAI_API_KEY')
        self.api_version = os.getenv('AZURE_OPENAI_API_VERSION')
        self.deployment_name = os.getenv('AZURE_OPENAI_COMPLETION_DEPLOYMENT')
        
        # Verify credentials are available
        if not self.api_endpoint or not self.api_key or not self.api_version or not self.deployment_name:
            raise ValueError("Azure OpenAI credentials are missing from environment variables")
            
        print(f"Translator initialized with API endpoint: {self.api_endpoint}")
        print(f"Using deployment: {self.deployment_name}, API version: {self.api_version}")
    
    def translate_template(self, template_data, target_language):
        """
        Translate template content to the target language.
        
        Args:
            template_data (dict): Parsed template data
            target_language (str): Target language code (e.g., 'de', 'es', 'fr', 'ko')
            
        Returns:
            dict: Translated template data
        """
        # Deep debug - print the complete template_data
        print(f"\n--- DEBUG: Original template_data for {target_language} ---")
        for key, value in template_data.items():
            # For large values, print only the first 100 chars
            if isinstance(value, str) and len(value) > 100:
                print(f"{key}: {value[:100]}... (truncated)")
            else:
                print(f"{key}: {value}")
        print("--- END DEBUG ---\n")
        
        # Copy the template data to avoid modifying the original
        translated_data = template_data.copy()
        
        # Set the appropriate voice for the target language
        if target_language == 'de':
            language_name = 'German'
            translated_data['voice'] = 'Daniel'
        elif target_language == 'es':
            language_name = 'Spanish'
            translated_data['voice'] = 'Lucia'
        elif target_language == 'fr':
            language_name = 'French'
            translated_data['voice'] = 'Remi'
        elif target_language == 'ko':
            language_name = 'Korean'
            translated_data['voice'] = 'Seoyeon'
        else:
            raise ValueError(f"Unsupported target language: {target_language}")
        
        print(f"Translating to {language_name} with voice ID: {translated_data['voice']}")
        
        # Translate the title
        if 'title' in template_data:
            try:
                original_title = template_data['title']
                print(f"Translating title: {original_title}")
                title_prompt = f"Translate the following title to {language_name}: {original_title}"
                translated_title = self._translate_text(title_prompt, target_language)
                translated_data['title'] = translated_title
                print(f"Translated title: {translated_title}")
            except Exception as e:
                print(f"Warning: Could not translate title: {e}")
                # Keep original title if translation fails
                translated_data['title'] = template_data['title']
        else:
            print("WARNING: No title found in template data")
        
        # Translate description
        if 'description' in template_data:
            try:
                desc_prompt = f"Translate the following description to {language_name}: {template_data['description']}"
                translated_data['description'] = self._translate_text(desc_prompt, target_language)
                print(f"Description translated successfully")
            except Exception as e:
                print(f"Warning: Could not translate description: {e}")
                # Keep original description if translation fails
                translated_data['description'] = template_data['description']
        else:
            print("WARNING: No description found in template data")
        
        # Translate thumbnail title if present
        if 'thumbnail_title' in template_data:
            try:
                thumb_prompt = f"Translate the following text to {language_name}: {template_data['thumbnail_title']}"
                translated_data['thumbnail_title'] = self._translate_text(thumb_prompt, target_language)
                print(f"Thumbnail title translated successfully")
            except Exception as e:
                print(f"Warning: Could not translate thumbnail title: {e}")
                # Keep original thumbnail title if translation fails
                translated_data['thumbnail_title'] = template_data['thumbnail_title']
        
        # Check if 'content' exists in template_data
        if 'content' not in template_data:
            print("ERROR: 'content' key missing in template_data")
            # Try to derive content from ssml_content
            if 'ssml_content' in template_data:
                print("Attempting to derive content from ssml_content")
                template_data['content'] = "Content " + template_data['ssml_content']
            else:
                raise KeyError("Neither 'content' nor 'ssml_content' found in template data")
        
        # Translate content
        content = template_data['content']
        print(f"Content to translate (first 100 chars): {content[:100]}")
        
        # Translated SSML content holder (default to original if translation fails)
        translated_ssml = None
        
        # Check if content contains SSML
        if '<speak>' in content:
            try:
                print("Content contains SSML tags")
                # Split the content into title and SSML parts
                parts = content.split('<speak>', 1)
                content_title = parts[0].strip()
                print(f"Content title: {content_title}")
                
                # Translate the content title
                title_prompt = f"Translate the following text to {language_name}: {content_title}"
                translated_title = self._translate_text(title_prompt, target_language)
                print(f"Translated content title: {translated_title}")
                
                # Extract the SSML content
                ssml_content = '<speak>' + parts[1]
                
                # Extract plain text from SSML for translation
                plain_text = self._remove_ssml_tags(ssml_content)
                print(f"Plain text extracted from SSML (first 100 chars): {plain_text[:100]}")
                
                # Translate the plain text content
                text_prompt = f"Translate the following text to {language_name}, preserving paragraph breaks and sentence structure: {plain_text}"
                translated_text = self._translate_text(text_prompt, target_language)
                print(f"Text translated successfully (first 100 chars): {translated_text[:100]}")
                
                # Restore SSML tags in the translated content
                translated_ssml = self._restore_ssml_tags(ssml_content, translated_text)
                print(f"SSML tags restored (first 100 chars): {translated_ssml[:100]}")
                
                # Combine the translated title and SSML content
                translated_data['content'] = f"{translated_title}\n{translated_ssml}"
                
                # Ensure ssml_content is also updated for proper processing
                translated_data['ssml_content'] = translated_ssml
                print("Content and ssml_content fields updated successfully")
            except Exception as e:
                print(f"Warning: Could not translate SSML content: {e}")
                # Keep original content if translation fails
                translated_data['content'] = template_data['content']
                # Ensure ssml_content exists
                if 'ssml_content' in template_data:
                    translated_data['ssml_content'] = template_data['ssml_content']
                else:
                    # Extract SSML content from original content
                    ssml_match = re.search(r'(<speak>.*?</speak>)', content, re.DOTALL)
                    if ssml_match:
                        translated_data['ssml_content'] = ssml_match.group(1)
                    else:
                        # Create a minimal valid SSML content as fallback
                        translated_data['ssml_content'] = f"<speak>\n<prosody rate=\"95%\" volume=\"loud\">\n{content_title}\n</prosody>\n</speak>"
        else:
            try:
                print("Content does not contain SSML tags, translating as plain text")
                # If no SSML, just translate the entire content
                content_prompt = f"Translate the following text to {language_name}: {content}"
                translated_data['content'] = self._translate_text(content_prompt, target_language)
                print("Plain text content translated successfully")
            except Exception as e:
                print(f"Warning: Could not translate plain text content: {e}")
                # Keep original content if translation fails
                translated_data['content'] = template_data['content']
        
        # Update tags if present
        if 'tags' in template_data:
            # Add language-specific tags
            tags = template_data['tags']
            lang_specific_tags = f"{language_name}Learning, {language_name}Vocabulary"
            translated_data['tags'] = f"{tags}, {lang_specific_tags}"
            print("Tags updated with language-specific tags")
        
        # Final validation - ensure ssml_content exists for video generation
        if 'ssml_content' not in translated_data:
            print("WARNING: ssml_content missing in translated data, trying to extract from content")
            if '<speak>' in translated_data.get('content', ''):
                # Extract SSML from content
                ssml_match = re.search(r'(<speak>.*?</speak>)', translated_data['content'], re.DOTALL)
                if ssml_match:
                    translated_data['ssml_content'] = ssml_match.group(1)
                    print("Successfully extracted ssml_content from content")
                else:
                    print("ERROR: Failed to extract ssml_content from content")
                    # Create a minimal valid SSML content as fallback
                    translated_data['ssml_content'] = f"<speak>\n<prosody rate=\"95%\" volume=\"loud\">\nContent in {language_name}\n</prosody>\n</speak>"
            else:
                print("ERROR: No SSML tags found in translated content")
                # Create a minimal valid SSML content as fallback
                translated_data['ssml_content'] = f"<speak>\n<prosody rate=\"95%\" volume=\"loud\">\nContent in {language_name}\n</prosody>\n</speak>"
        
        # Deep debug - print the complete translated data
        print(f"\n--- DEBUG: Translated template_data for {target_language} ---")
        for key, value in translated_data.items():
            # For large values, print only the first 50 chars
            if isinstance(value, str) and len(value) > 100:
                print(f"{key}: {value[:100]}... (truncated)")
            else:
                print(f"{key}: {value}")
        print("--- END DEBUG ---\n")
        
        return translated_data
    
    def _translate_text(self, prompt, language_code):
        """
        Send a translation request to Azure OpenAI.
        
        Args:
            prompt (str): The prompt for translation
            language_code (str): Language code for debugging
            
        Returns:
            str: Translated text
        """
        try:
            print(f"Sending translation request to Azure OpenAI for {language_code}")
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
            body = {
                "messages": [
                    {"role": "system", "content": "You are a professional translator. Translate the given text accurately while preserving the meaning, tone, and format."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 4000
            }
            
            url = f"{self.api_endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
            print(f"API URL: {url}")
            
            # Print prompt summary (truncated for readability)
            print(f"Translation prompt (first 100 chars): {prompt[:100]}...")
            
            # Send the request
            print("Sending API request...")
            response = requests.post(url, headers=headers, json=body)
            
            # Check for HTTP errors
            if response.status_code != 200:
                print(f"ERROR: API request failed with status code {response.status_code}")
                print(f"Response text: {response.text}")
                response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            # Debug - print the keys list (convert to list before JSON serialization)
            print(f"API Response received. Keys: {list(result.keys())}")
            
            # Print full response for debugging if needed
            # print(f"Full API response: {json.dumps(result)}")
            
            # Check if the expected keys exist in the response
            if 'choices' not in result:
                print(f"ERROR: 'choices' key missing from API response")
                raise ValueError(f"Invalid response from Azure OpenAI - 'choices' key missing")
            
            if len(result['choices']) == 0:
                print("ERROR: No choices returned in the API response")
                raise ValueError("No translation choices returned from Azure OpenAI")
            
            if 'message' not in result['choices'][0]:
                print(f"ERROR: 'message' key missing from choices: {json.dumps(result['choices'][0])}")
                raise ValueError("Invalid response structure - 'message' key missing")
            
            # More detailed error handling to catch problematic responses
            message = result['choices'][0]['message']
            if not isinstance(message, dict):
                print(f"ERROR: 'message' is not a dictionary: {type(message)}")
                raise ValueError(f"Unexpected message type: {type(message)}")
                
            # Check if 'content' exists in the message
            if 'content' not in message:
                print(f"ERROR: 'content' key missing from message: {json.dumps(message)}")
                
                # Try to extract any available text from the API response
                if isinstance(message, dict) and any(message.values()):
                    # Use any available field as a fallback
                    for key, value in message.items():
                        if isinstance(value, str) and value.strip():
                            print(f"Using '{key}' field as fallback content: {value[:50]}...")
                            return value.strip()
                
                # If all else fails, return a placeholder based on the prompt
                placeholder = f"[Translation to {language_code} unavailable]"
                print(f"No usable content found. Using placeholder: {placeholder}")
                return placeholder
            
            translated_text = message['content'].strip()
            print(f"Successfully received translation (first 100 chars): {translated_text[:100]}...")
            
            return translated_text
                
        except Exception as e:
            print(f"ERROR in _translate_text for {language_code}: {str(e)}")
            # Print full traceback for debugging
            traceback.print_exc()
            # Detailed error for debugging
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"Response text: {response.text}")
            # Instead of failing, return a placeholder
            placeholder = f"[Translation to {language_code} failed: {str(e)}]"
            print(f"Returning placeholder: {placeholder}")
            return placeholder
    
    def _remove_ssml_tags(self, ssml_content):
        """
        Remove SSML tags from content for translation, preserving markers.
        
        Args:
            ssml_content (str): Content with SSML tags
            
        Returns:
            str: Content without SSML tags
        """
        try:
            print("Removing SSML tags for translation")
            # Replace marker tags with placeholder text that won't be translated
            
            # Replace mark tags with unique placeholders
            mark_pattern = r'<mark name="([^"]+)"/>'
            mark_matches = re.finditer(mark_pattern, ssml_content)
            
            # Keep track of replacements to restore later
            self.mark_replacements = {}
            
            content = ssml_content
            mark_count = 0
            for match in mark_matches:
                placeholder = f"__MARK_{match.group(1)}__"
                self.mark_replacements[placeholder] = match.group(0)
                content = content.replace(match.group(0), placeholder)
                mark_count += 1
            
            print(f"Replaced {mark_count} mark tags with placeholders")
            
            # Replace other SSML tags
            content = re.sub(r'<speak>', '', content)
            content = re.sub(r'<prosody[^>]+>', '', content)
            content = re.sub(r'</prosody>', '', content)
            content = re.sub(r'</speak>', '', content)
            
            print(f"SSML tags removed, resulting text (first 100 chars): {content[:100]}...")
            return content.strip()
            
        except Exception as e:
            print(f"ERROR in _remove_ssml_tags: {str(e)}")
            traceback.print_exc()
            # Return original content if processing fails
            return ssml_content.replace('<speak>', '').replace('</speak>', '')
    
    def _restore_ssml_tags(self, original_ssml, translated_text):
        """
        Restore SSML tags in translated content.
        
        Args:
            original_ssml (str): Original SSML content with tags
            translated_text (str): Translated text without tags
            
        Returns:
            str: Translated text with SSML tags restored
        """
        try:
            print("Restoring SSML tags in translated text")
            # Restore mark tags from placeholders
            result = translated_text
            
            # Restore mark placeholders
            mark_count = 0
            for placeholder, tag in self.mark_replacements.items():
                if placeholder in result:
                    result = result.replace(placeholder, tag)
                    mark_count += 1
                else:
                    print(f"WARNING: Placeholder {placeholder} not found in translated text")
            
            print(f"Restored {mark_count} mark tags from placeholders")
            
            # Extract the prosody attributes from the original SSML
            prosody_match = re.search(r'<prosody([^>]+)>', original_ssml)
            prosody_attrs = prosody_match.group(1) if prosody_match else ''
            
            # Wrap the translated content with the same prosody tags
            result = f"<speak>\n<prosody{prosody_attrs}>\n{result}\n</prosody>\n</speak>"
            
            print(f"SSML tags fully restored, result (first 100 chars): {result[:100]}...")
            return result
            
        except Exception as e:
            print(f"ERROR in _restore_ssml_tags: {str(e)}")
            traceback.print_exc()
            # Create a valid SSML wrapper even if restoration fails
            return f"<speak>\n<prosody rate=\"95%\" volume=\"loud\">\n{translated_text}\n</prosody>\n</speak>"