import cloudinary
import cloudinary.api
import cloudinary.uploader
import random
import os
import requests
import json
import subprocess
import time # Instagram API polling ke liye

# --- Cloudinary Configuration (Using GitHub Secrets) ---
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

# --- Instagram API Configuration ---
# Instagram API base URL
INSTAGRAM_GRAPH_API_URL = "https://graph.facebook.com/v19.0/" # Current Graph API version
# Instagram Business Account ID (GitHub Secret se aayega)
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
# Instagram Long-Lived Access Token (GitHub Secret se aayega)
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")

# Google API authentication ab zaroori nahi hai.
def get_instagram_access_token():
    """
    Instagram API access token ko environment variable se fetch karta hai.
    """
    if not INSTAGRAM_ACCESS_TOKEN:
        raise ValueError("INSTAGRAM_ACCESS_TOKEN GitHub Secret is missing or empty.")
    print("Instagram Access Token loaded from secrets.")
    return INSTAGRAM_ACCESS_TOKEN

def download_file(url, local_path):
    """Downloads a file from a URL to a local path."""
    print(f"Downloading {url} to {local_path}...")
    with requests.get(url, stream=True) as r:
        r.raise_for_status() # HTTP errors (4xx, 5xx) ko handle karein
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print("Download complete.")

def merge_video_audio_ffmpeg(video_input_path, audio_input_path, output_path):
    """
    Merges video (muting original audio) with background music using FFmpeg.
    Ensures video is trimmed to the shortest duration (video or audio).
    """
    print(f"Merging video: {video_input_path} with audio: {audio_input_path} into {output_path}...")
    
    ffmpeg_command = [
        "ffmpeg",
        "-i", video_input_path,
        "-i", audio_input_path,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-shortest",
        "-y", # Overwrite output file if it exists
        output_path
    ]

    try:
        # Run FFmpeg command
        result = subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
        print("FFmpeg stdout:")
        print(result.stdout)
        print("FFmpeg stderr:")
        print(result.stderr)
        print(f"Video and audio merged successfully to {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg command failed with error code {e.returncode}")
        print("FFmpeg stdout:")
        print(e.stdout)
        print("FFmpeg stderr:")
        print(e.stderr)
        raise Exception(f"Video/audio merging failed: {e}")
    except FileNotFoundError:
        print("FFmpeg not found. Please ensure FFmpeg is installed and accessible in your PATH.")
        raise Exception("FFmpeg not found.")

def upload_video_to_instagram(access_token, business_account_id, video_file_path, caption, tags):
    """
    Local file se Instagram Business Account par video upload karta hai.
    Instagram Graph API ka two-step process follow karta hai: Container Creation -> Publishing.
    """
    if not business_account_id:
        raise ValueError("INSTAGRAM_BUSINESS_ACCOUNT_ID is not set. Please set it as a GitHub Secret.")
    if not access_token:
        raise ValueError("INSTAGRAM_ACCESS_TOKEN is not set. Please set it as a GitHub Secret.")

    print(f"Starting Instagram upload for video: {video_file_path}")

    # Step 1: Upload merged video to Cloudinary temporarily for Instagram consumption
    # Instagram API requires video_url to be publicly accessible.
    print("Uploading merged video to Cloudinary for Instagram consumption...")
    upload_response = cloudinary.uploader.upload(
        video_file_path,
        resource_type="video",
        folder="instagram_temp_uploads", # Naya folder for temporary Instagram uploads
        overwrite=True,
        invalidate=True
    )
    cloudinary_video_url = upload_response.get("secure_url")
    if not cloudinary_video_url:
        raise Exception("Failed to upload merged video to Cloudinary for Instagram. Check Cloudinary credentials/upload limits.")
    print(f"Merged video uploaded to Cloudinary: {cloudinary_video_url}")

    # Instagram API ke requirements ke hisaab se caption aur tags
    # Instagram tags (hashtags) caption ke andar hi hote hain.

    container_creation_url = f"{INSTAGRAM_GRAPH_API_URL}{business_account_id}/media"
    container_params = {
        'access_token': access_token,
        'media_type': 'VIDEO',
        'video_url': cloudinary_video_url, # Cloudinary URL use kar rahe hain
        'caption': caption,
        'thumb_offset': 0, # Optional: Video start se thumbnail (0 seconds)
    }

    print("Creating Instagram media container...")
    response = requests.post(container_creation_url, data=container_params)
    response.raise_for_status() # HTTP errors ko handle karein (4xx, 5xx)
    container_id = response.json().get('id')
    if not container_id:
        raise Exception(f"Failed to create Instagram media container: {response.json()}")
    print(f"Media container created with ID: {container_id}")

    # Step 2: Poll for container status until it's finished processing
    status_url = f"{INSTAGRAM_GRAPH_API_URL}{container_id}"
    params = {
        'fields': 'status,status_code', # status_code for detailed error
        'access_token': access_token
    }
    
    print("Polling container status...")
    max_retries = 30 # 30 retries * 10 seconds = 300 seconds (5 minutes)
    retry_count = 0
    while retry_count < max_retries:
        status_response = requests.get(status_url, params=params)
        status_response.raise_for_status()
        status_data = status_response.json()
        status = status_data.get('status')
        status_code = status_data.get('status_code')

        print(f"Container status: {status} (Code: {status_code if status_code else 'N/A'})")

        if status == 'FINISHED':
            print("Container processing finished.")
            break
        elif status == 'ERROR':
            raise Exception(f"Instagram container processing failed: {status_data.get('status_code')} - {status_data.get('error_message', 'No error message provided.')}")
        else:
            time.sleep(10) # Wait for 10 seconds before polling again
            retry_count += 1
    else: # Loop exhausted without finishing
        raise Exception("Instagram container processing timed out after 5 minutes.")

    # Step 3: Publish the media
    publish_url = f"{INSTAGRAM_GRAPH_API_URL}{business_account_id}/media_publish"
    publish_params = {
        'creation_id': container_id,
        'access_token': access_token
    }

    print("Publishing video to Instagram...")
    publish_response = requests.post(publish_url, data=publish_params)
    publish_response.raise_for_status() # HTTP errors ko handle karein
    post_id = publish_response.json().get('id')
    if not post_id:
        raise Exception(f"Failed to publish video to Instagram: {publish_response.json()}")
    print(f"Video successfully posted to Instagram! Post ID: {post_id}")
    return post_id # Return Instagram post ID (useful for logging)


def main():
    """
    Main function jo Cloudinary se video aur music fetch karke merge karta hai,
    aur phir merged video ko Instagram par upload karta hai.
    """
    # Define temporary file paths
    temp_video_path = "temp_video.mp4"
    temp_music_path = "temp_music.mp3" # Keep .mp3 extension for music
    merged_output_path = "merged_output.mp4"

    # Initialize access_token
    instagram_access_token = None

    try:
        # --- Authentication Service ko Yahan Call Karein ---
        instagram_access_token = get_instagram_access_token()

        # --- 1. Cloudinary se random video fetch karein ('Quotes_Videos' folder se, jo upload nahi hui ho) ---
        print("Searching for un-uploaded videos in Cloudinary 'Quotes_Videos' folder...")
        search_results = cloudinary.Search()\
            .expression("resource_type:video AND folder:Quotes_Videos AND -tags:uploaded_to_instagram")\
            .sort_by("public_id", "asc")\
            .max_results(500)\
            .execute()
        
        videos = search_results.get('resources', [])
        
        if not videos:
            print("No un-uploaded videos found in Cloudinary 'Quotes_Videos' folder. Exiting.")
            return

        random_video = random.choice(videos)
        video_url = random_video.get('secure_url')
        video_public_id = random_video.get('public_id')
        print(f"Selected random video: {video_public_id}, URL: {video_url}")

        # --- 2. Direct Background Music URL ka upyog karein ---
        # Aapne jo link diya hai use yahan hardcode kar dein.
        music_url = "https://res.cloudinary.com/decqrz2gm/video/upload/v1750532138/backmusic/Control_isn_t_....mp3"
        music_title_for_desc = "Control isn't..." # Music title for caption
        print(f"Using fixed background music URL: {music_url}")

        # --- 3. Video aur Music Files Download Karein ---
        download_file(video_url, temp_video_path)
        download_file(music_url, temp_music_path)
        
        # --- 4. Video aur Audio ko Merge Karein (FFmpeg ka upyog karke) ---
        merged_video_path = merge_video_audio_ffmpeg(temp_video_path, temp_music_path, merged_output_path)

        # --- 5. Instagram Caption and Hashtags (Motivational Content) ---
        motivational_captions = [
            "Unleash Your Inner Power: A Motivational Journey! 💪",
            "Believe in Yourself: The Path to Success Starts Now! ✨",
            "Never Give Up: Find Your Drive & Conquer Your Goals! 🔥",
            "Daily Dose of Motivation: Fuel Your Dreams! 🚀",
            "Inspire Your Day: Positive Vibes & Strong Mindset! 🌟",
            "Push Your Limits: Transform Your Life Today! 💯",
            "The Power of Positive Thinking: Achieve Anything! 💡",
            "Wake Up & Win: Your Morning Motivation Boost! ☀️",
            "Success Mindset: Build Your Empire! 👑",
            "Stay Focused, Stay Strong: Your Ultimate Motivation! 🙌"
        ]
        
        selected_caption_prefix = random.choice(motivational_captions) 

        # Instagram tags caption ke andar hi hote hain.
        insta_tags = [
            "motivation", "inspiration", "success", "believeinyourself", 
            "nevergiveup", "positivevibes", "mindset", "goalsetting", 
            "dreambig", "selfimprovement", "motivationalvideo", 
            "dailymotivation", "inspirationalquotes", "focus",
            "personalgrowth", "achievegoals", "productivitytips", "shortsvideo", "reels", "dailyquotes" # Add Instagram specific tags
        ]

        # Full caption with copyright and social links
        full_insta_caption = (
            f"{selected_caption_prefix}\n\n"
            "This video is designed to ignite your inner fire and keep you motivated on your journey to success. "
            "Remember, every challenge is an opportunity in disguise. Believe in yourself, stay consistent, and never stop chasing your dreams.\n\n"
            "--- Music & Copyright --- \n"
            f"🎵 Background Music: {music_title_for_desc} by [**Artist Name of Background Music**]\n"
            "🎶 Music License: [**If applicable, include license details or link**]\n"
            "I do not claim ownership of the background music used in this video. This video is for motivational and entertainment purposes only.\n\n"
            "--- Connect With Us --- \n"
            "[Your Instagram Handle, e.g., @YourChannelNameHere]\n"
            "[Your Website/Other Social Media Links Here]\n\n"
            "#" + " #".join(insta_tags) # Hashtags
        )
        
        # --- 6. Instagram par merged video upload karein ---
        instagram_post_id = upload_video_to_instagram(
            instagram_access_token,
            INSTAGRAM_BUSINESS_ACCOUNT_ID, # Global variable
            merged_video_path,
            full_insta_caption,
            insta_tags # Tags are included in caption for Instagram
        )
        
        # --- 7. Cloudinary mein video ko 'uploaded_to_instagram' tag karein ---
        if instagram_post_id:
            print(f"Tagging Cloudinary video '{video_public_id}' as 'uploaded_to_instagram'...")
            # Tag change karein: 'uploaded_to_youtube' se 'uploaded_to_instagram'
            cloudinary.uploader.add_tag("uploaded_to_instagram", video_public_id, resource_type="video")
            print("Cloudinary video tagged successfully.")

    except Exception as e:
        print(f"Ek error aa gaya: {e}")
        raise # Error hone par GitHub Action job ko fail karein
    finally:
        # --- 8. Temporary files ko delete karein (cleanup) ---
        for f_path in [temp_video_path, temp_music_path, merged_output_path]:
            if os.path.exists(f_path):
                try:
                    os.remove(f_path)
                    print(f"Cleaned up temporary file: {f_path}")
                except OSError as e:
                    print(f"Error cleaning up file {f_path}: {e}")

if __name__ == "__main__":
    main()
