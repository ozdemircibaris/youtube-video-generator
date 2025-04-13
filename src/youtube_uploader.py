import os
import pickle
import json
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    """Get an authenticated YouTube API service using OAuth2 flow"""
    credentials = None
    token_file = 'youtube-token.pickle'
    
    # Check if token file exists
    if os.path.exists(token_file):
        print("Loading credentials from token file...")
        with open(token_file, 'rb') as f:
            credentials = pickle.load(f)
    
    # Check if credentials need refresh
    if credentials and credentials.expired and credentials.refresh_token:
        print("Refreshing expired credentials...")
        credentials.refresh(Request())
    
    # If no valid credentials, we need to get new ones
    if not credentials or not credentials.valid:
        print("Getting new credentials through OAuth flow...")
        
        # Load client secrets from file
        client_config = {}
        with open('youtube-credentials.json') as f:
            client_config = json.load(f)
        
        # Create the flow using the client secrets file
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            'youtube-credentials.json',
            SCOPES
        )
        
        # Run the OAuth flow to get user credentials
        credentials = flow.run_local_server(port=0)
        
        # Save credentials for future use
        with open(token_file, 'wb') as f:
            pickle.dump(credentials, f)
        
        print("New credentials obtained and saved.")
    
    # Build the YouTube service
    youtube = googleapiclient.discovery.build(
        "youtube", "v3", credentials=credentials
    )
    
    return youtube

def upload_video(video_file, title="My Video", description="", tags=None, 
                category_id="22", privacy_status="public", is_shorts=False, 
                thumbnail_path=None):
    """Upload a video to YouTube
    
    Args:
        video_file (str): Path to the video file
        title (str): Video title
        description (str): Video description
        tags (list): List of tags
        category_id (str): YouTube category ID
        privacy_status (str): Privacy status (public, private, unlisted)
        is_shorts (bool): Whether this is a YouTube Shorts video
        thumbnail_path (str, optional): Path to custom thumbnail image
        
    Returns:
        str: YouTube video ID if successful, None otherwise
    """
    try:
        if not os.path.exists(video_file):
            print(f"Video file not found: {video_file}")
            return None
        
        # Get authenticated service
        youtube = get_authenticated_service()
        if not youtube:
            print("Failed to authenticate with YouTube API")
            return None
        
        # Default tags
        if tags is None:
            tags = ["YouTube", "API", "Python"]
        
        # Add Shorts tag for shorts videos
        if is_shorts:
            if "#Shorts" not in title:
                title = f"{title} #Shorts"
            if "Shorts" not in tags:
                tags.append("Shorts")
        
        # Build the request body
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id,
                "defaultLanguage": "en"
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False
            }
        }
        
        # Call the API to upload the video
        print(f"Uploading video to YouTube: {title}")
        media_file = MediaFileUpload(
            video_file, 
            mimetype="video/mp4", 
            resumable=True
        )
        
        # Create the videos.insert request
        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media_file
        )
        
        # Execute the request and get the response
        response = request.execute()
        
        # Return the video ID
        if 'id' in response:
            video_id = response['id']
            print(f"Video uploaded successfully. Video ID: {video_id}")
            
            # Upload thumbnail if provided
            if thumbnail_path and os.path.exists(thumbnail_path):
                upload_thumbnail(youtube, video_id, thumbnail_path)
                
            return video_id
        else:
            print("Video upload failed. No video ID in response.")
            return None
    
    except googleapiclient.errors.HttpError as e:
        print(f"YouTube API HttpError: {e}")
        return None
    except Exception as e:
        print(f"Error uploading video to YouTube: {e}")
        return None

def upload_thumbnail(youtube, video_id, thumbnail_path):
    """Upload a custom thumbnail for a YouTube video
    
    Args:
        youtube: Authenticated YouTube API service
        video_id (str): YouTube video ID
        thumbnail_path (str): Path to thumbnail image
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Uploading thumbnail for video ID {video_id}...")
        
        # Verify file exists and has valid extension
        if not os.path.exists(thumbnail_path):
            print(f"Thumbnail file not found: {thumbnail_path}")
            return False
            
        # Check file extension (YouTube only accepts JPG, PNG, GIF)
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        file_ext = os.path.splitext(thumbnail_path)[1].lower()
        
        if file_ext not in valid_extensions:
            print(f"Invalid thumbnail file format: {file_ext}. Must be JPG, PNG or GIF.")
            return False
            
        # Determine mime type based on extension
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif'
        }
        
        mime_type = mime_types.get(file_ext, 'image/jpeg')
        
        # Create media upload object
        media = MediaFileUpload(
            thumbnail_path,
            mimetype=mime_type,
            resumable=True
        )
        
        # Set the thumbnail
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=media
        ).execute()
        
        print(f"Thumbnail uploaded successfully for video ID: {video_id}")
        return True
        
    except googleapiclient.errors.HttpError as e:
        print(f"YouTube API HttpError while uploading thumbnail: {e}")
        return False
    except Exception as e:
        print(f"Error uploading thumbnail: {e}")
        return False

def get_video_details(video_id):
    """Get details of a specific video by its ID"""
    try:
        # Get authenticated service
        youtube = get_authenticated_service()
        if not youtube:
            print("Failed to authenticate with YouTube API")
            return None
        
        # Call the API to get video details
        request = youtube.videos().list(
            part="snippet,statistics",
            id=video_id
        )
        
        # Execute the request
        response = request.execute()
        
        # Check if there are items in the response
        if 'items' in response and len(response['items']) > 0:
            return response['items'][0]
        else:
            print(f"No video found with ID: {video_id}")
            return None
    
    except Exception as e:
        print(f"Error getting video details: {e}")
        return None 