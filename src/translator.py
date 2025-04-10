import os
import json
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure OpenAI credentials
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2023-05-15')
AZURE_OPENAI_COMPLETION_DEPLOYMENT = os.getenv('AZURE_OPENAI_COMPLETION_DEPLOYMENT', 'gpt-4o-new')

# Supported languages and their Polly voice configurations
LANGUAGE_VOICES = {
    'english': {
        'code': 'en',
        'voice': 'Matthew',  # Default English male voice
        'gender': 'male'
    },
    'korean': {
        'code': 'ko',
        'voice': 'Seoyeon',
        'gender': 'female'
    },
    'german': {
        'code': 'de',
        'voice': 'Daniel',
        'gender': 'male'
    },
    'spanish': {
        'code': 'es',
        'voice': 'Lucia',
        'gender': 'female'
    },
    'french': {
        'code': 'fr',
        'voice': 'Remi',
        'gender': 'male'
    }
}

def setup_azure_openai():
    """Setup Azure OpenAI client configuration"""
    if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION]):
        raise ValueError("Azure OpenAI credentials are not properly configured. Please check your .env file.")
    
    # Configure OpenAI API to use Azure OpenAI
    openai.api_type = "azure"
    openai.api_base = AZURE_OPENAI_ENDPOINT
    openai.api_version = AZURE_OPENAI_API_VERSION
    openai.api_key = AZURE_OPENAI_API_KEY
    
    print(f"Azure OpenAI API configured with endpoint: {AZURE_OPENAI_ENDPOINT}")
    print(f"Using deployment: {AZURE_OPENAI_COMPLETION_DEPLOYMENT}")

def translate_text(text, target_language):
    """
    Translate text from English to the target language using Azure OpenAI
    
    Args:
        text (str): The text to translate
        target_language (str): Target language ('korean', 'german', 'spanish', 'french')
        
    Returns:
        str: Translated text
    """
    if target_language.lower() not in LANGUAGE_VOICES:
        raise ValueError(f"Unsupported language: {target_language}. Supported languages are: {', '.join(LANGUAGE_VOICES.keys())}")
    
    # If target language is English, return the original text
    if target_language.lower() == 'english':
        return text
    
    # Setup Azure OpenAI client
    setup_azure_openai()
    
    try:
        response = openai.ChatCompletion.create(
            deployment_id=AZURE_OPENAI_COMPLETION_DEPLOYMENT,
            messages=[
                {"role": "system", "content": f"""You are a professional translator specialized in translating from English to {target_language}.
Provide an accurate, natural-sounding translation without adding any explanations or additional text.
Maintain the same formatting, including line breaks, as the source text."""},
                {"role": "user", "content": f"Translate the following English text to {target_language}:\n\n{text}"}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        
        translated_text = response.choices[0].message.content.strip()
        return translated_text
        
    except Exception as e:
        print(f"Translation error: {e}")
        return None

def translate_template_file(template_path, target_language):
    """
    Translate the values in a template file from English to the target language
    
    Args:
        template_path (str): Path to the template file
        target_language (str): Target language ('korean', 'german', 'spanish', 'french')
        
    Returns:
        dict: Dictionary containing the translated template values
        str: The file path of the saved translated template
    """
    if target_language.lower() not in LANGUAGE_VOICES:
        raise ValueError(f"Unsupported language: {target_language}. Supported languages are: {', '.join(LANGUAGE_VOICES.keys())}")
    
    # If target language is English, return the original template
    if target_language.lower() == 'english':
        return None, template_path
    
    try:
        # Read the template file
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split the content by lines
        lines = content.split('\n')
        
        # Extract parameters and content
        parameters = {}
        content_text = ""
        in_content_block = False
        
        for line in lines:
            if line.startswith('#'):
                # Parameter line
                param_parts = line[1:].split(':', 1)
                if len(param_parts) == 2:
                    key = param_parts[0].strip()
                    value = param_parts[1].strip()
                    
                    if key == 'content':
                        in_content_block = True
                        content_text = value if value else ""
                    else:
                        parameters[key] = value
            elif in_content_block:
                # Content lines
                content_text += "\n" + line
        
        # For title and description, replace "English" with target language but keep in English
        english_replacement_params = ['title', 'description', 'tags']
        target_lang_capitalized = target_language.capitalize()
        
        for param in english_replacement_params:
            if param in parameters:
                # Simply replace English with target language
                parameters[param] = parameters[param].replace("English", target_lang_capitalized)
                parameters[param] = parameters[param].replace("english", target_language.lower())
                print(f"Modified {param} for {target_language} (kept in English)")
        
        # Translate content only
        translated_content = translate_text(content_text.strip(), target_language)
        print(f"Translated content to {target_language}")
        
        # Update voice parameter for the target language
        language_voice = LANGUAGE_VOICES[target_language.lower()]['voice']
        parameters['voice'] = language_voice
        
        # Create translated template file
        base_name = os.path.basename(template_path)
        dir_name = os.path.dirname(template_path)
        translated_file_path = os.path.join(
            dir_name, 
            f"{os.path.splitext(base_name)[0]}_{target_language.lower()}.txt"
        )
        
        with open(translated_file_path, 'w', encoding='utf-8') as f:
            # Write the parameters first
            for key, value in parameters.items():
                f.write(f"#{key}: {value}\n")
            
            # Write the content with proper formatting
            f.write("\n#content: ")
            if translated_content:
                f.write(translated_content)
        
        print(f"Translated template saved to: {translated_file_path}")
        return parameters, translated_file_path
        
    except Exception as e:
        print(f"Translation template error: {e}")
        return None, None

def get_language_voice(language):
    """
    Get the appropriate Amazon Polly voice for a given language
    
    Args:
        language (str): Language name ('english', 'korean', 'german', 'spanish', 'french')
        
    Returns:
        str: Amazon Polly voice name for the language
    """
    language = language.lower()
    if language not in LANGUAGE_VOICES:
        print(f"Warning: Unsupported language '{language}'. Using default English voice.")
        return LANGUAGE_VOICES['english']['voice']
    
    return LANGUAGE_VOICES[language]['voice'] 