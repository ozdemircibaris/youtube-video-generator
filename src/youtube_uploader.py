"""
YouTube video upload module for uploading videos to YouTube.
"""

import os
import time
import httplib2
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import traceback


class YouTubeUploader:
    """Handles uploading videos to YouTube using OAuth2 authentication."""
    
    def __init__(self):
        """Initialize the YouTube uploader."""
        self.youtube = None
        self.credentials_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "credentials",
            "youtube_credentials.json"
        )
        self.token_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "credentials",
            "token.json"
        )
        # Create credentials directory if it doesn't exist
        os.makedirs(os.path.dirname(self.credentials_path), exist_ok=True)
        
    def authenticate(self):
        """
        Authenticate with YouTube API using OAuth2.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # API scopes needed for uploading videos
            scopes = ["https://www.googleapis.com/auth/youtube.upload"]
            
            credentials = None
            
            # Check if token file exists
            if os.path.exists(self.token_path):
                try:
                    credentials = Credentials.from_authorized_user_info(
                        info=eval(open(self.token_path).read()),
                        scopes=scopes
                    )
                except Exception as e:
                    print(f"Error loading saved credentials: {e}")
                    credentials = None
            
            # If credentials don't exist or are invalid, get new ones
            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    try:
                        credentials.refresh(Request())
                    except:
                        # If refresh fails, need to get new credentials
                        credentials = None
                
                if not credentials:
                    # Check if credentials file exists
                    if not os.path.exists(self.credentials_path):
                        print(f"YouTube credentials file not found at {self.credentials_path}")
                        print("Please download OAuth client ID credentials from Google Cloud Console and save it as credentials/youtube_credentials.json")
                        return False
                    
                    # Get credentials from user
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, 
                        scopes,
                        redirect_uri="urn:ietf:wg:oauth:2.0:oob"
                    )
                    
                    # Run local server for authentication
                    credentials = flow.run_local_server(port=0)
                
                # Save credentials for future use
                with open(self.token_path, "w") as token_file:
                    token_file.write(str(credentials.to_json()))
            
            # Build YouTube service
            self.youtube = build("youtube", "v3", credentials=credentials)
            print("Successfully authenticated with YouTube API")
            return True
        
        except Exception as e:
            print(f"Authentication error: {e}")
            traceback.print_exc()
            return False
    
    def upload_video(self, video_path, title, description, tags, category_id="22", privacy_status="public", thumbnail_path=None):
        """
        Upload a video to YouTube.
        
        Args:
            video_path (str): Path to the video file
            title (str): Video title
            description (str): Video description
            tags (list): List of tags for the video
            category_id (str): YouTube category ID (default: 22 for Education)
            privacy_status (str): Privacy status (public, unlisted, private)
            thumbnail_path (str, optional): Path to thumbnail image
            
        Returns:
            str: YouTube video ID if successful, None otherwise
        """
        try:
            if not os.path.exists(video_path):
                print(f"Video file not found: {video_path}")
                return None
            
            if not self.youtube:
                if not self.authenticate():
                    return None
            
            # Process tags (convert comma-separated string to list if needed)
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(",")]
            
            # Convert tags to list of strings
            tags = [str(tag) for tag in tags]
            
            print(f"Uploading video: {title}")
            print(f"File: {video_path}")
            
            # Set video metadata
            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": category_id
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False
                }
            }
            
            # Create upload request
            media = MediaFileUpload(
                video_path,
                chunksize=1024 * 1024,
                resumable=True
            )
            
            # Execute upload request
            request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Upload the video
            print("Starting video upload, this may take some time...")
            response = None
            
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"Upload progress: {progress}%")
            
            video_id = response["id"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            print(f"Video uploaded successfully! URL: {video_url}")
            
            # Upload thumbnail if provided
            if thumbnail_path and os.path.exists(thumbnail_path):
                self.set_thumbnail(video_id, thumbnail_path)
            
            return video_id
        
        except Exception as e:
            print(f"Upload error: {e}")
            traceback.print_exc()
            return None
    
    def set_thumbnail(self, video_id, thumbnail_path):
        """
        Set a custom thumbnail for a YouTube video.
        
        Args:
            video_id (str): YouTube video ID
            thumbnail_path (str): Path to thumbnail image
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(thumbnail_path):
                print(f"Thumbnail image not found: {thumbnail_path}")
                return False
            
            if not self.youtube:
                if not self.authenticate():
                    return False
                    
            print(f"Uploading thumbnail for video ID: {video_id}")
            print(f"Thumbnail file: {thumbnail_path}")
            
            # Create upload request for thumbnail
            media = MediaFileUpload(
                thumbnail_path,
                mimetype='image/jpeg',
                resumable=True
            )
            
            # Execute thumbnail upload request
            request = self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=media
            )
            
            # Upload the thumbnail
            response = request.execute()
            
            print(f"Thumbnail uploaded successfully for video ID: {video_id}")
            return True
            
        except Exception as e:
            print(f"Thumbnail upload error: {e}")
            traceback.print_exc()
            return False
            
    def upload_videos_from_template(self, template_data, video_paths, language_code='en'):
        """
        Upload videos to YouTube using template data.
        
        Args:
            template_data (dict): Template data with metadata
            video_paths (dict): Dictionary with video paths
            language_code (str): Language code for the video
            
        Returns:
            dict: Dictionary with YouTube video IDs
        """
        try:
            results = {}
            
            # Get metadata from template
            title = template_data.get('title', 'Untitled Video')
            description = template_data.get('description', '')
            tags = template_data.get('tags', '')
            
            # CHANGED ORDER: First upload standard video, then shorts video
            # This allows us to include the standard video link in shorts description
            standard_video_id = None
            
            # Get standard video path (if it exists)
            if 'video' in video_paths and os.path.exists(video_paths['video']):
                # Get thumbnail path for standard video
                thumbnail_path = video_paths.get('thumbnail')
                if thumbnail_path and not os.path.exists(thumbnail_path):
                    print(f"Warning: Thumbnail file not found at {thumbnail_path}")
                    thumbnail_path = None
                    
                print(f"\n--- Uploading standard video for {language_code} ---")
                standard_video_id = self.upload_video(
                    video_paths['video'],
                    title,
                    description,
                    tags,
                    thumbnail_path=thumbnail_path
                )
                if standard_video_id:
                    results['standard'] = standard_video_id
                    print(f"Standard video uploaded with ID: {standard_video_id}")
            
            # Get shorts video path (if it exists)
            if 'shorts' in video_paths and os.path.exists(video_paths['shorts']):
                # Get thumbnail path for shorts video (same as standard video)
                thumbnail_path = video_paths.get('thumbnail')
                if thumbnail_path and not os.path.exists(thumbnail_path):
                    print(f"Warning: Thumbnail file not found at {thumbnail_path}")
                    thumbnail_path = None
                    
                print(f"\n--- Uploading Shorts video for {language_code} ---")
                # Add "#Shorts" to title for shorts videos
                shorts_title = f"{title} #Shorts"
                
                # Add #Shorts to tags
                shorts_tags = tags
                if isinstance(shorts_tags, str):
                    shorts_tags = shorts_tags + ", Shorts"
                else:
                    shorts_tags = shorts_tags + ["Shorts"]
                
                # Modify description to include link to standard video if available
                shorts_description = description
                if standard_video_id:
                    standard_video_url = f"https://www.youtube.com/watch?v={standard_video_id}"
                    
                    # Add link to full video at the end of description
                    shorts_description = shorts_description.rstrip() + "\n\n"
                    shorts_description += f"📺 Watch the full video: {standard_video_url}"
                
                video_id = self.upload_video(
                    video_paths['shorts'],
                    shorts_title,
                    shorts_description,
                    shorts_tags,
                    thumbnail_path=thumbnail_path
                )
                if video_id:
                    results['shorts'] = video_id
                    print(f"Shorts video uploaded with ID: {video_id}")
            
            return results
        
        except Exception as e:
            print(f"Error uploading videos: {e}")
            traceback.print_exc()
            return {} 