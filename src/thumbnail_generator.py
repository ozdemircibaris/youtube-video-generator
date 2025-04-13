import os
import torch
from diffusers import StableDiffusionPipeline
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import random
from src.config import OUTPUT_DIR, ASSETS_DIR

# Constants
THUMBNAIL_DIR = os.path.join(OUTPUT_DIR, 'thumbnails')
os.makedirs(THUMBNAIL_DIR, exist_ok=True)

# Default model ID
DEFAULT_MODEL_ID = "stabilityai/stable-diffusion-2-base"

class ThumbnailGenerator:
    def __init__(self, model_id=DEFAULT_MODEL_ID, low_memory=True):
        """Initialize the thumbnail generator with specified model.
        
        Args:
            model_id (str): HuggingFace model ID for Stable Diffusion
            low_memory (bool): If True, enable optimizations for low memory environments
        """
        self.model_id = model_id
        self.pipe = None
        self.low_memory = low_memory
        
    def _load_model(self):
        """Load the Stable Diffusion model if not already loaded"""
        if self.pipe is not None:
            return True
        
        try:
            print("Initializing Stable Diffusion model...")
            
            # Check for available hardware acceleration
            if torch.cuda.is_available():
                print("CUDA is available. Using GPU acceleration.")
                self.pipe = StableDiffusionPipeline.from_pretrained(
                    self.model_id, 
                    torch_dtype=torch.float16
                )
                self.pipe = self.pipe.to("cuda")
                
                # Apply memory optimizations if requested
                if self.low_memory:
                    self.pipe.enable_attention_slicing()
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                # For Apple Silicon (M1/M2/M3)
                # Set MPS memory limits to avoid OOM errors
                os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.5'
                os.environ['PYTORCH_MPS_LOW_WATERMARK_RATIO'] = '0.3'
                
                print("MPS is available. Using Apple Silicon acceleration with memory limits.")
                try:
                    # Simple approach - load on CPU first
                    self.pipe = StableDiffusionPipeline.from_pretrained(self.model_id)
                    
                    # Keep on CPU until inference
                    print("Model loaded. Will move to MPS only during inference to save memory.")
                except Exception as e:
                    print(f"Error loading model: {e}")
                    print("Falling back to CPU only mode...")
                    self.pipe = StableDiffusionPipeline.from_pretrained(self.model_id)
            else:
                # CPU fallback (much slower)
                print("No GPU acceleration available. Using CPU (this will be slow).")
                self.pipe = StableDiffusionPipeline.from_pretrained(self.model_id)
                
                # Enable CPU offloading for low memory
                if self.low_memory:
                    print("Enabling sequential CPU offload for low memory usage.")
                    self.pipe.enable_sequential_cpu_offload()
            
            print(f"Stable Diffusion model {self.model_id} loaded successfully")
            return True
        except Exception as e:
            print(f"Error loading Stable Diffusion model: {e}")
            return False
        
    def generate_from_template(self, title, language=None):
        """Generate a thumbnail based on a template with title overlay
        
        Args:
            title (str): The video title to use for prompt generation
            language (str, optional): Language of the video content
            
        Returns:
            str: Path to the generated thumbnail
        """
        # Create a prompt based on the title
        prompt_prefix = "Professional YouTube thumbnail, "
        
        # Add language context if provided
        if language and language.lower() != 'english':
            prompt_suffix = f"for {language} language learning video, educational, high quality"
        else:
            prompt_suffix = "for English language learning video, educational, high quality"
        
        # Clean title to use as part of the prompt
        cleaned_title = title.replace('#', '').replace('|', '').strip()
        prompt = f"{prompt_prefix}{cleaned_title}, {prompt_suffix}"
        
        # Generate the image
        return self.generate(prompt, title)
    
    def generate(self, prompt, title=None, height=720, width=1280, thumbnail_path=None):
        """Generate a thumbnail image using Stable Diffusion
        
        Args:
            prompt (str): The text prompt to generate the image from
            title (str, optional): Title text to overlay on the thumbnail
            height (int): Height of the generated image
            width (int): Width of the generated image
            thumbnail_path (str, optional): Path to save the thumbnail
            
        Returns:
            str: Path to the generated thumbnail
        """
        # Load model if not loaded
        if not self._load_model():
            print("Failed to load model")
            return None
        
        try:
            # Generate the image
            print(f"Generating thumbnail with prompt: {prompt}")
            
            # If using MPS (Apple Silicon), temporarily move to device for inference
            using_mps = hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
            
            if using_mps:
                print("Moving model to MPS for inference...")
                try:
                    # Force garbage collection before inference
                    import gc
                    gc.collect()
                    
                    # Safe cache emptying
                    try:
                        torch.mps.empty_cache()
                    except RuntimeError as e:
                        print(f"Warning: Could not empty MPS cache: {e}")
                        print("Continuing without emptying cache...")
                    
                    # Move to MPS for inference
                    self.pipe.to("mps")
                except Exception as e:
                    print(f"Error moving model to MPS: {e}")
                    print("Falling back to CPU inference...")
                    using_mps = False
            
            # Use lower resolution for initial generation to save memory
            gen_height = min(height, 512)
            gen_width = min(width, 512)
            
            # Generate at lower resolution
            image = self.pipe(
                prompt,
                height=gen_height,
                width=gen_width,
                guidance_scale=7.5,
                num_inference_steps=30  # Reduced steps to save memory
            ).images[0]
            
            # Move back to CPU after inference if using MPS
            if using_mps:
                print("Moving model back to CPU to free MPS memory...")
                try:
                    self.pipe.to("cpu")
                    
                    # Safe cache emptying
                    try:
                        torch.mps.empty_cache()
                    except RuntimeError as e:
                        print(f"Warning: Could not empty MPS cache while moving back to CPU: {e}")
                except Exception as e:
                    print(f"Warning: Error while moving back to CPU: {e}")
            
            # Resize to target resolution
            if gen_height != height or gen_width != width:
                image = image.resize((width, height), Image.LANCZOS)
            
            # Add title overlay if provided
            if title:
                image = self._add_title_overlay(image, title)
            
            # Save the image
            if thumbnail_path is None:
                # Create a filename based on the title if provided, otherwise use timestamp
                if title:
                    safe_title = "".join([c if c.isalnum() else "_" for c in title]).lower()
                    safe_title = safe_title[:30]  # Limit length
                else:
                    import time
                    safe_title = f"thumbnail_{int(time.time())}"
                
                thumbnail_path = os.path.join(THUMBNAIL_DIR, f"{safe_title}.jpg")
            
            # Save the image with high quality
            image.save(thumbnail_path, format="JPEG", quality=95)
            print(f"Thumbnail saved to {thumbnail_path}")
            
            return thumbnail_path
        
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            # Free up memory in case of error
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                try:
                    self.pipe.to("cpu")
                    try:
                        torch.mps.empty_cache()
                    except RuntimeError as e2:
                        print(f"Warning: Could not empty MPS cache during error cleanup: {e2}")
                except Exception as e2:
                    print(f"Warning: Error during cleanup: {e2}")
            return None
    
    def _add_title_overlay(self, image, title, max_length=30):
        """Add title text overlay to the thumbnail
        
        Args:
            image (PIL.Image): The base image
            title (str): Title text to overlay
            max_length (int): Maximum length of each line
            
        Returns:
            PIL.Image: Image with text overlay
        """
        # Make a copy of the image to avoid modifying the original
        img = image.copy()
        draw = ImageDraw.Draw(img)
        
        # Get image dimensions
        img_width, img_height = img.size
        
        # Try to load a font
        font_size = 70  # Daha büyük font (önceki 60'tan)
        font = None
        try:
            # Try to load fonts with better Unicode support
            font_paths = [
                os.path.join(ASSETS_DIR, "fonts", "NotoSerifKR-VariableFont_wght.ttf"),  # Project font with good Unicode support
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",  # macOS Unicode font
                "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",  # Linux Noto (good Unicode support)
                "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",  # Linux
                "C:\\Windows\\Fonts\\arial.ttf",  # Windows
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"  # Linux alternative
            ]
            
            for path in font_paths:
                if os.path.exists(path):
                    font = ImageFont.truetype(path, font_size)
                    break
                    
            if font is None:
                font = ImageFont.load_default()
                font_size = 30
        except Exception as e:
            print(f"Error loading font: {e}")
            font = ImageFont.load_default()
            font_size = 30
            
        # Clean title by removing special characters that cause rendering issues
        # Comprehensive special character and emoji cleaning
        clean_title = title
        # Special characters and emojis for explicit removal
        special_chars = ['□', '■', '▪', '▫', '◻', '◼', '◽', '◾', '⬛', '⬜', '|', '🗣️', 
                          '👋', '🎧', '✅', '🔍', '🔎', '🌍', '🌏', '🤔', '🗨', '💭',
                          '#', '🎵', '🎶', '🔊', '🎫', '📊', '📈', '🎯', '⭐', '✨', 
                          '✓', '✔️', '✘', '✗', '☑️', '☑', '☒', '☐', '🔵', '🟡', '🔴',
                          '❤️', '✎', '✏️', '✐', '📝', '✍️', '📖']
                          
        # General emoji and symbol character ranges - these include a wide variety of emojis and symbols
        for char in clean_title:
            # Emoji and special symbol ranges
            if ((ord(char) >= 0x2600 and ord(char) <= 0x27BF) or  # Dingbats
               (ord(char) >= 0x1F300 and ord(char) <= 0x1F9FF) or  # Miscellaneous Symbols, Emoticons, etc.
               (ord(char) >= 0x2300 and ord(char) <= 0x23FF) or  # Miscellaneous Technical
               (ord(char) >= 0x25A0 and ord(char) <= 0x25FF) or  # Geometric Shapes
               (ord(char) == 0x00A9) or (ord(char) == 0x00AE) or  # Copyright, Registered marks
               char in special_chars):
                clean_title = clean_title.replace(char, ' ')
        
        # Remove multiple spaces
        import re
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        # Prepare the title (limit to 2 lines)
        # Preserve special characters by not modifying them
        if len(clean_title) > max_length:
            # Find a space near the middle to split the title
            mid_point = len(clean_title) // 2
            split_point = clean_title.rfind(" ", 0, max_length)
            if split_point == -1:
                split_point = max_length
            
            line1 = clean_title[:split_point].strip()
            line2 = clean_title[split_point:].strip()
            
            # If second line is too long, truncate it
            if len(line2) > max_length:
                line2 = line2[:max_length-3] + "..."
            
            lines = [line1, line2]
        else:
            lines = [clean_title]
        
        # Equal padding for top and bottom to ensure vertical centering
        padding_y = 40  # Increased padding for better visual balance
        
        # Calculate text block total height
        line_height = font_size * 1.2  # Add some line spacing (20% of font size)
        total_text_height = len(lines) * line_height
        
        # Calculate overlay height (text height + top and bottom padding)
        overlay_height = total_text_height + (padding_y * 2)
        
        # Calculate vertical position of overlay (center on screen)
        overlay_y_start = (img_height - overlay_height) // 2
        overlay_y_end = overlay_y_start + overlay_height
        
        # Create a semi-transparent overlay
        overlay = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Define the rounded rectangle coordinates
        rect_left = 50
        rect_top = overlay_y_start
        rect_right = img_width - 50
        rect_bottom = overlay_y_end
        rect_radius = 16  # Border radius
        
        # Create a rounded rectangle mask
        try:
            # Try to use rounded rectangle if PIL version supports it
            overlay_draw.rounded_rectangle([rect_left, rect_top, rect_right, rect_bottom], 
                                          radius=rect_radius, fill=(0, 0, 0, 180))
        except AttributeError:
            # If rounded_rectangle is not available, use normal rectangle
            overlay_draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], 
                                  fill=(0, 0, 0, 180))
        
        # Convert overlay to RGB and paste onto main image
        overlay_rgb = overlay.convert('RGB')
        mask = overlay.split()[3]  # Use alpha channel as mask
        img.paste(overlay_rgb, (0, 0), mask)
        
        # Calculate exact vertical center for perfect alignment
        text_block_height = total_text_height
        overlay_center_y = overlay_y_start + (overlay_height / 2)
        
        # Draw each line centered
        for i, line in enumerate(lines):
            # Calculate position (centered horizontally, within the overlay)
            try:
                text_width = draw.textlength(line, font=font)
            except:
                # Fallback for older PIL versions or if textlength is not available
                try:
                    text_width = font.getsize(line)[0]
                except:
                    # Very basic fallback - estimate width
                    text_width = len(line) * (font_size // 2)
                    
            # Calculate x position for horizontal centering
            x_position = img_width // 2  # Center horizontally

            # Calculate y position for the center of this specific line
            # Start from the overlay's vertical center, adjust for total block height,
            # then adjust for the current line's position within the block.
            line_center_y = overlay_center_y - (text_block_height / 2) + (line_height / 2) + (i * line_height)
            position = (x_position, line_center_y)

            # Draw text with shadow for better visibility using anchor='mm'
            shadow_offset = 2
            shadow_position = (position[0] + shadow_offset, position[1] + shadow_offset)
            draw.text(shadow_position, line, font=font, fill=(0, 0, 0), anchor="mm")
            draw.text(position, line, font=font, fill=(255, 255, 255), anchor="mm")
        
        return img


def generate_thumbnail(title, language=None, prompt=None, use_simple=False):
    """
    Convenience function to generate a thumbnail for a video.
    
    Args:
        title (str): The video title
        language (str, optional): Language of the video content
        prompt (str, optional): Custom prompt for image generation
        use_simple (bool, optional): If True, skip Stable Diffusion and use simple thumbnail directly
        
    Returns:
        str: Path to the generated thumbnail
    """
    # If requested, skip Stable Diffusion and use simple method directly
    if use_simple:
        print("Using simple thumbnail generator as requested...")
        return generate_simple_thumbnail(title, language)
    
    # Otherwise try Stable Diffusion first
    generator = ThumbnailGenerator()
    
    if prompt:
        thumbnail_path = generator.generate(prompt, title)
    else:
        thumbnail_path = generator.generate_from_template(title, language)
    
    # If Stable Diffusion fails, fall back to simple thumbnail
    if not thumbnail_path:
        print("Falling back to simple thumbnail generation...")
        thumbnail_path = generate_simple_thumbnail(title, language)
    
    return thumbnail_path

def generate_simple_thumbnail(title, language=None):
    """
    Generate a simple thumbnail using PIL when Stable Diffusion fails.
    
    Args:
        title (str): The video title
        language (str, optional): Language of the video content
        
    Returns:
        str: Path to the generated thumbnail
    """
    try:
        # Create output directory if it doesn't exist
        thumbnail_dir = os.path.join(OUTPUT_DIR, 'thumbnails')
        os.makedirs(thumbnail_dir, exist_ok=True)
        
        # Create a filename based on the title
        safe_title = "".join([c if c.isalnum() else "_" for c in title]).lower()[:30]
        thumbnail_path = os.path.join(thumbnail_dir, f"{safe_title}_simple.jpg")
        
        # Create a blank image with a gradient background
        width, height = 1280, 720
        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)
        
        # Choose colors based on language
        colors = {
            'english': [(25, 55, 109), (87, 108, 188)],
            'french': [(0, 35, 149), (237, 41, 57)],
            'spanish': [(198, 11, 30), (241, 191, 0)],
            'german': [(0, 0, 0), (255, 0, 0), (255, 204, 0)],
            'korean': [(0, 71, 160), (205, 46, 58)]
        }
        
        bg_colors = colors.get(language.lower() if language else 'english', 
                              [(25, 55, 109), (87, 108, 188)])
        
        # Create gradient background
        for y in range(height):
            # Calculate ratio (0 to 1) based on y-coordinate
            ratio = y / height
            
            # Get colors for the gradient
            if len(bg_colors) == 2:
                # Simple linear gradient between two colors
                r = int(bg_colors[0][0] * (1 - ratio) + bg_colors[1][0] * ratio)
                g = int(bg_colors[0][1] * (1 - ratio) + bg_colors[1][1] * ratio)
                b = int(bg_colors[0][2] * (1 - ratio) + bg_colors[1][2] * ratio)
            else:
                # For more than two colors, do a segmented gradient
                segments = len(bg_colors) - 1
                segment_idx = min(int(ratio * segments), segments - 1)
                segment_ratio = (ratio * segments) - segment_idx
                
                r = int(bg_colors[segment_idx][0] * (1 - segment_ratio) + bg_colors[segment_idx + 1][0] * segment_ratio)
                g = int(bg_colors[segment_idx][1] * (1 - segment_ratio) + bg_colors[segment_idx + 1][1] * segment_ratio)
                b = int(bg_colors[segment_idx][2] * (1 - segment_ratio) + bg_colors[segment_idx + 1][2] * segment_ratio)
            
            # Draw a horizontal line with the calculated color
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Try to find a background image or pattern
        try:
            # Check if background_videos directory exists for potential frame capture
            bg_videos_dir = os.path.join(ASSETS_DIR, 'background_videos')
            if os.path.exists(bg_videos_dir):
                # Get list of video files
                video_files = [f for f in os.listdir(bg_videos_dir) 
                              if f.endswith('.mp4') and os.path.isfile(os.path.join(bg_videos_dir, f))]
                
                if video_files:
                    # Choose a random video file to use as background
                    from moviepy.editor import VideoFileClip
                    bg_video = os.path.join(bg_videos_dir, random.choice(video_files))
                    
                    # Extract a frame from the middle of the video
                    with VideoFileClip(bg_video) as clip:
                        # Get a frame from around the middle of the video
                        frame_time = clip.duration / 2
                        bg_frame = clip.get_frame(frame_time)
                        bg_image = Image.fromarray(bg_frame)
                        
                        # Resize to fit
                        bg_image = bg_image.resize((width, height), Image.LANCZOS)
                        
                        # Apply slight transparency to blend with gradient
                        image = Image.blend(image, bg_image, 0.5)
                        draw = ImageDraw.Draw(image)
        except Exception as e:
            print(f"Could not use video frame as background: {e}")
        
        # Try to load a font
        font_size = 70  # Daha büyük font (önceki 60'tan)
        font = None
        try:
            # Try to load fonts with better Unicode support
            font_paths = [
                os.path.join(ASSETS_DIR, "fonts", "NotoSerifKR-VariableFont_wght.ttf"),  # Project font with good Unicode support
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",  # macOS Unicode font
                "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",  # Linux Noto (good Unicode support)
                "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",  # Linux
                "C:\\Windows\\Fonts\\arial.ttf",  # Windows
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"  # Linux alternative
            ]
            
            for path in font_paths:
                if os.path.exists(path):
                    font = ImageFont.truetype(path, font_size)
                    break
                    
            if font is None:
                font = ImageFont.load_default()
                font_size = 30
        except Exception as e:
            print(f"Error loading font: {e}")
            font = ImageFont.load_default()
            font_size = 30
        
        # Add language flag or icon if available
        icon_added = False
        flag_path = os.path.join(ASSETS_DIR, "flags", f"{language.lower() if language else 'english'}.png")
        if os.path.exists(flag_path):
            try:
                flag_img = Image.open(flag_path)
                flag_size = 100
                flag_img = flag_img.resize((flag_size, flag_size), Image.LANCZOS)
                image.paste(flag_img, (width - flag_size - 50, 50), flag_img if 'A' in flag_img.getbands() else None)
                icon_added = True
            except Exception as e:
                print(f"Error adding flag: {e}")
                
        # Clean title by removing special characters that cause rendering issues
        # Comprehensive special character and emoji cleaning
        clean_title = title
        # Special characters and emojis for explicit removal
        special_chars = ['□', '■', '▪', '▫', '◻', '◼', '◽', '◾', '⬛', '⬜', '|', '🗣️', 
                          '👋', '🎧', '✅', '🔍', '🔎', '🌍', '🌏', '🤔', '🗨', '💭',
                          '#', '🎵', '🎶', '🔊', '🎫', '📊', '📈', '🎯', '⭐', '✨', 
                          '✓', '✔️', '✘', '✗', '☑️', '☑', '☒', '☐', '🔵', '🟡', '🔴',
                          '❤️', '✎', '✏️', '✐', '📝', '✍️', '📖']
                          
        # General emoji and symbol character ranges - these include a wide variety of emojis and symbols
        for char in clean_title:
            # Emoji and special symbol ranges
            if ((ord(char) >= 0x2600 and ord(char) <= 0x27BF) or  # Dingbats
               (ord(char) >= 0x1F300 and ord(char) <= 0x1F9FF) or  # Miscellaneous Symbols, Emoticons, etc.
               (ord(char) >= 0x2300 and ord(char) <= 0x23FF) or  # Miscellaneous Technical
               (ord(char) >= 0x25A0 and ord(char) <= 0x25FF) or  # Geometric Shapes
               (ord(char) == 0x00A9) or (ord(char) == 0x00AE) or  # Copyright, Registered marks
               char in special_chars):
                clean_title = clean_title.replace(char, ' ')
        
        # Remove multiple spaces
        import re
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        # Prepare and draw the title text
        draw = ImageDraw.Draw(image)
        
        # Split title into multiple lines if needed
        max_chars_per_line = 30
        words = clean_title.split()
        lines = []
        current_line = ""
        
        # Özel karakterlere dikkat ederek title'ı bölümlere ayıralım
        for word in words:
            # Eğer bu kelime eklendiğinde maksimum karakter sayısını aşıyorsa, yeni satıra geç
            if len(current_line + " " + word) <= max_chars_per_line:
                current_line += " " + word if current_line else word
            else:
                lines.append(current_line)
                current_line = word
        
        # Add the last line
        if current_line:
            lines.append(current_line)
        
        # Equal padding for top and bottom to ensure vertical centering
        padding_y = 40  # Increased padding for better visual balance
        
        # Calculate text block total height
        line_height = font_size * 1.2  # Add some line spacing (20% of font size)
        total_text_height = len(lines) * line_height
        
        # Calculate overlay height (text height + top and bottom padding)
        overlay_height = total_text_height + (padding_y * 2)
        
        # Calculate vertical position of overlay (center on screen)
        overlay_y_start = (height - overlay_height) // 2
        overlay_y_end = overlay_y_start + overlay_height
        
        # Create a semi-transparent overlay
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Define the rounded rectangle coordinates
        rect_left = 50
        rect_top = overlay_y_start
        rect_right = width - 50
        rect_bottom = overlay_y_end
        rect_radius = 16  # Border radius
        
        # Create a rounded rectangle mask
        try:
            # Try to use rounded rectangle if PIL version supports it
            overlay_draw.rounded_rectangle([rect_left, rect_top, rect_right, rect_bottom], 
                                         radius=rect_radius, fill=(0, 0, 0, 180))
        except AttributeError:
            # If rounded_rectangle is not available, use normal rectangle
            overlay_draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], 
                                  fill=(0, 0, 0, 180))
        
        # Convert overlay to RGB and paste onto main image
        overlay_rgb = overlay.convert('RGB')
        mask = overlay.split()[3]  # Use alpha channel as mask
        image.paste(overlay_rgb, (0, 0), mask)
        
        # Calculate exact vertical center for perfect alignment
        text_block_height = total_text_height
        overlay_center_y = overlay_y_start + (overlay_height / 2)
        
        # Draw each line centered
        for i, line in enumerate(lines):
            # Calculate position (centered horizontally, within the overlay)
            try:
                text_width = draw.textlength(line, font=font)
            except:
                # Fallback for older PIL versions or if textlength is not available
                try:
                    text_width = font.getsize(line)[0]
                except:
                    # Very basic fallback - estimate width
                    text_width = len(line) * (font_size // 2)
                    
            # Calculate x position for horizontal centering
            x_position = width // 2 # Center horizontally

            # Calculate y position for the center of this specific line
            # Start from the overlay's vertical center, adjust for total block height,
            # then adjust for the current line's position within the block.
            line_center_y = overlay_center_y - (text_block_height / 2) + (line_height / 2) + (i * line_height)
            position = (x_position, line_center_y)

            # Draw text with shadow for better visibility using anchor='mm'
            shadow_offset = 2
            shadow_position = (position[0] + shadow_offset, position[1] + shadow_offset)
            draw.text(shadow_position, line, font=font, fill=(0, 0, 0), anchor="mm")
            draw.text(position, line, font=font, fill=(255, 255, 255), anchor="mm")
        
        # Add "World of Languages" text at the bottom
        brand_text = "WORLD OF LANGUAGES"
        lang_font_size = 40
        try:
            lang_font = ImageFont.truetype(font_paths[0] if os.path.exists(font_paths[0]) else None, lang_font_size)
        except:
            lang_font = font
            lang_font_size = 30
            
        # Calculate brand text width with error handling
        try:
            brand_width = draw.textlength(brand_text, font=lang_font)
        except:
            # Fallback for older PIL versions or if textlength is not available
            try:
                brand_width = lang_font.getsize(brand_text)[0]
            except:
                # Very basic fallback - estimate width
                brand_width = len(brand_text) * (lang_font_size // 2)
        
        brand_position = ((width - brand_width) // 2, height - lang_font_size - 50)
        
        # Draw brand text with shadow
        draw.text((brand_position[0] + 2, brand_position[1] + 2), brand_text, font=lang_font, fill=(0, 0, 0))
        draw.text(brand_position, brand_text, font=lang_font, fill=(255, 255, 255))
        
        # Save the image with high quality
        image.save(thumbnail_path, format="JPEG", quality=95)
        print(f"Simple thumbnail saved to {thumbnail_path}")
        
        return thumbnail_path
    
    except Exception as e:
        print(f"Error generating simple thumbnail: {e}")
        return None 