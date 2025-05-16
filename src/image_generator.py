"""
Image generator module for creating thumbnails using Azure Stable Diffusion.
"""

import os
import requests
import json
import base64
from PIL import Image
import io
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ImageGenerator:
    def __init__(self):
        """Initialize the image generator with Azure Stable Diffusion credentials."""
        self.api_key = os.getenv('SD_API_KEY')
        self.endpoint = os.getenv('SD_AZURE_ENDPOINT')
        
        # Verify credentials are available
        if not self.api_key or not self.endpoint:
            raise ValueError("Azure Stable Diffusion credentials are missing from environment variables")
            
        print(f"Image Generator initialized with API endpoint: {self.endpoint}")
    
    def generate_thumbnail(self, prompt, output_path, language_code='en'):
        """
        Generate a thumbnail image based on the given prompt.
        
        Args:
            prompt (str): Stable Diffusion prompt for image generation
            output_path (str): Path to save the generated image
            language_code (str): Language code for output path naming
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Map language code to language name
            language_names = {
                'en': 'English',
                'de': 'German',
                'es': 'Spanish',
                'fr': 'French',
                'ko': 'Korean'
            }
            
            # Get language name
            language_name = language_names.get(language_code, 'English')
            
            # Replace {language} in prompt with actual language name
            if '{language}' in prompt:
                prompt = prompt.replace('{language}', language_name)
                print(f"Replaced {{language}} with {language_name} in prompt")
            
            print(f"Generating thumbnail for {language_code}")
            print(f"Prompt (first 100 chars): {prompt[:100]}...")
            
            # Configure the headers for Azure Stable Diffusion API
            headers = {
                "Content-Type": "application/json",
                "Authorization": self.api_key,  # Using Authorization header as required by the API
                "accept": "application/json"
            }
            
            # Use a supported size from the API (closest to 16:9 aspect ratio)
            # Based on error message, only these sizes are supported: 
            # '672x1566', '768x1366', '836x1254', '916x1145', '1024x1024', '1145x916', '1254x836', '1366x768', '1566x672'
            thumbnail_size = "1366x768"  # Using this size as it's closest to YouTube's 16:9 ratio
            
            # Prepare request body
            body = {
                "prompt": prompt,
                "n": 1,  # Number of images to generate
                "size": thumbnail_size
                # Removed response_format parameter as it's not supported
            }
            
            # Send request to the Azure Stable Diffusion endpoint
            print(f"Sending request to Stable Diffusion API...")
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=body,
                timeout=90  # Increased timeout for image generation
            )
            
            # Check if the request was successful
            if response.status_code != 200:
                print(f"API request failed with status code {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
            # Parse the response
            result = response.json()
            
            print("Response received successfully")
            
            # Extract the image data from the response
            image_data = None
            
            # Handle various response formats from Azure Stable Diffusion
            if 'image' in result:
                # Direct image field (seems to be the format your API uses)
                image_data = result['image']
            elif 'data' in result and isinstance(result['data'], list) and len(result['data']) > 0:
                if 'b64_json' in result['data'][0]:
                    image_data = result['data'][0]['b64_json']
                elif 'url' in result['data'][0]:
                    # If URL is provided instead of base64 data
                    image_url = result['data'][0]['url']
                    img_response = requests.get(image_url)
                    if img_response.status_code == 200:
                        image_data = base64.b64encode(img_response.content).decode('utf-8')
            elif 'images' in result and isinstance(result['images'], list) and len(result['images']) > 0:
                image_data = result['images'][0]  # Some APIs return direct base64 in images array
            elif 'generated_images' in result and isinstance(result['generated_images'], list) and len(result['generated_images']) > 0:
                if 'b64_json' in result['generated_images'][0]:
                    image_data = result['generated_images'][0]['b64_json']
                elif 'url' in result['generated_images'][0]:
                    image_url = result['generated_images'][0]['url']
                    img_response = requests.get(image_url)
                    if img_response.status_code == 200:
                        image_data = base64.b64encode(img_response.content).decode('utf-8')
            
            # Check if we were able to extract image data
            if not image_data:
                print("Could not find image data in API response")
                print(f"Response structure: {json.dumps(list(result.keys()), indent=2)}")
                return False
            
            # Convert base64 to image
            try:
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
            except Exception as e:
                print(f"Error decoding image data: {e}")
                return False
            
            # Ensure the image is in the correct dimensions for YouTube thumbnails
            if image.width != 1280 or image.height != 720:
                print(f"Resizing image from {image.width}x{image.height} to 1280x720")
                image = image.resize((1280, 720), Image.LANCZOS)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save the image
            image.save(output_path, quality=95)
            
            print(f"Thumbnail saved to {output_path}")
            return True
            
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            traceback.print_exc()
            return False

    # Yeni eklenen generate_section_image metodu
    def generate_section_image(self, prompt, output_path, section_name):
        """
        Generate an image for a specific section based on the given prompt.
        
        Args:
            prompt (str): Stable Diffusion prompt for image generation
            output_path (str): Path to save the generated image
            section_name (str): Name of the section (for output path naming)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"Generating image for section: {section_name}")
            print(f"Prompt (first 100 chars): {prompt[:100]}...")
            
            # Configure the headers for Azure Stable Diffusion API
            headers = {
                "Content-Type": "application/json",
                "Authorization": self.api_key,  # Using Authorization header as required by the API
                "accept": "application/json"
            }
            
            # Use a supported size from the API (closest to 16:9 aspect ratio)
            section_image_size = "1366x768"
            
            # Prepare request body
            body = {
                "prompt": prompt,
                "n": 1,  # Number of images to generate
                "size": section_image_size
            }
            
            # Send request to the Azure Stable Diffusion endpoint
            print(f"Sending request to Stable Diffusion API for section {section_name}...")
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=body,
                timeout=90  # Increased timeout for image generation
            )
            
            # Check if the request was successful
            if response.status_code != 200:
                print(f"API request failed with status code {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
            # Parse the response
            result = response.json()
            
            print("Response received successfully")
            
            # Extract the image data from the response
            image_data = None
            
            # Handle various response formats from Azure Stable Diffusion
            if 'image' in result:
                # Direct image field (seems to be the format your API uses)
                image_data = result['image']
            elif 'data' in result and isinstance(result['data'], list) and len(result['data']) > 0:
                if 'b64_json' in result['data'][0]:
                    image_data = result['data'][0]['b64_json']
                elif 'url' in result['data'][0]:
                    # If URL is provided instead of base64 data
                    image_url = result['data'][0]['url']
                    img_response = requests.get(image_url)
                    if img_response.status_code == 200:
                        image_data = base64.b64encode(img_response.content).decode('utf-8')
            elif 'images' in result and isinstance(result['images'], list) and len(result['images']) > 0:
                image_data = result['images'][0]  # Some APIs return direct base64 in images array
            elif 'generated_images' in result and isinstance(result['generated_images'], list) and len(result['generated_images']) > 0:
                if 'b64_json' in result['generated_images'][0]:
                    image_data = result['generated_images'][0]['b64_json']
                elif 'url' in result['generated_images'][0]:
                    image_url = result['generated_images'][0]['url']
                    img_response = requests.get(image_url)
                    if img_response.status_code == 200:
                        image_data = base64.b64encode(img_response.content).decode('utf-8')
            
            # Check if we were able to extract image data
            if not image_data:
                print("Could not find image data in API response")
                print(f"Response structure: {json.dumps(list(result.keys()), indent=2)}")
                return False
            
            # Convert base64 to image
            try:
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
            except Exception as e:
                print(f"Error decoding image data: {e}")
                return False
            
            # Ensure the image is in the correct dimensions for the video (16:9 aspect ratio)
            # We'll use 1920x1080 for high-quality video
            if image.width != 1920 or image.height != 1080:
                print(f"Resizing image from {image.width}x{image.height} to 1920x1080")
                image = image.resize((1920, 1080), Image.LANCZOS)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save the image
            image.save(output_path, quality=95)
            
            print(f"Section image saved to {output_path}")
            return True
            
        except Exception as e:
            print(f"Error generating section image: {e}")
            traceback.print_exc()
            return False

    # If your API specifically requires API version parameter, you can use this method
    def _ensure_api_version(self, endpoint):
        """Ensure the endpoint has the API version parameter if needed."""
        if 'api-version=' not in endpoint:
            separator = '&' if '?' in endpoint else '?'
            return f"{endpoint}{separator}api-version=2023-06-01-preview"
        return endpoint