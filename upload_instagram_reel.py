import cloudinary
import cloudinary.api
import os
import requests
import random
import time

# --- Cloudinary Configuration ---
# Fetch Cloudinary credentials from environment variables (GitHub Secrets)
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

# --- Instagram Configuration ---
# Fetch Instagram credentials from environment variables (GitHub Secrets)
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_PAGE_ID = os.environ.get("INSTAGRAM_PAGE_ID")

def get_videos_from_cloudinary_folder(folder_name="Quotes_Videos"):
    """
    Fetches video URLs from a specified Cloudinary folder.
    """
    try:
        # Check if Cloudinary credentials are set
        if not cloudinary.config().cloud_name or \
           not cloudinary.config().api_key or \
           not cloudinary.config().api_secret:
            print("Error: Cloudinary credentials not set in environment variables.")
            return []

        # Use Cloudinary API to list resources
        result = cloudinary.api.resources(
            type="upload",
            resource_type="video",
            prefix=f"{folder_name}/", # This filters by the folder path
            max_results=500 # Adjust this to fetch more or fewer videos for random selection
        )
        # Extract secure URLs of the videos
        video_urls = [resource['secure_url'] for resource in result.get('resources', [])]
        print(f"Successfully fetched {len(video_urls)} videos from Cloudinary folder '{folder_name}'.")
        return video_urls
    except Exception as e:
        print(f"Error fetching videos from Cloudinary: {e}")
        return []

def upload_video_to_instagram(video_url, caption):
    """
    Uploads a video to Instagram via the Facebook Graph API.
    Requires a Page Access Token and the associated Facebook Page ID.
    """
    if not INSTAGRAM_ACCESS_TOKEN:
        print("Error: Instagram access token not configured in environment variables.")
        return False
    if not INSTAGRAM_PAGE_ID:
        print("Error: Instagram page ID not configured in environment variables.")
        return False

    try:
        # Step 1: Create a media container on Instagram (via Facebook Graph API)
        container_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_PAGE_ID}/media"
        container_payload = {
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption,
            'access_token': INSTAGRAM_ACCESS_TOKEN,
            'share_to_feed': True
        }
        print(f"Creating Instagram media container for video: {video_url}")
        container_response = requests.post(container_url, data=container_payload)
        container_data = container_response.json()

        if 'id' not in container_data:
            print(f"Error creating Instagram container. Response: {container_data}")
            if 'error' in container_data and 'error_user_msg' in container_data['error']:
                print(f"Instagram API Error Message: {container_data['error']['error_user_msg']}")
            return False

        creation_id = container_data['id']
        print(f"Instagram media container created with ID: {creation_id}.")

        # --- Polling for media status ---
        status_check_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code&access_token={INSTAGRAM_ACCESS_TOKEN}"
        
        max_retries = 30 # Increased retries slightly for GitHub Actions, as network might vary
        sleep_interval = 10 # Increased sleep to 10 seconds, common for video processing
        
        print("Waiting for video to be processed by Instagram...")
        for i in range(max_retries):
            time.sleep(sleep_interval)
            status_response = requests.get(status_check_url).json()
            status_code = status_response.get('status_code')

            print(f"Attempt {i+1}/{max_retries}: Media status code: {status_code}")

            if status_code == 'FINISHED':
                print("Video processing finished. Ready to publish.")
                break
            elif status_code == 'ERROR':
                print(f"Error during video processing on Instagram's side. Response: {status_response}")
                return False
            elif i == max_retries - 1:
                print("Max retries reached. Video did not finish processing in time.")
                return False
        else:
            print("Polling loop completed without 'FINISHED' status. Could not publish.")
            return False

        # Step 2: Publish the created media container to Instagram
        publish_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_PAGE_ID}/media_publish"
        publish_payload = {
            'creation_id': creation_id,
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        print(f"Publishing video with creation ID: {creation_id}")
        publish_response = requests.post(publish_url, data=publish_payload)
        publish_data = publish_response.json()

        if 'id' in publish_data:
            print(f"Video successfully uploaded to Instagram! Post ID: {publish_data['id']}")
            return True
        else:
            print(f"Error publishing video to Instagram. Response: {publish_data}")
            if 'error' in publish_data and 'error_user_msg' in publish_data['error']:
                print(f"Instagram API Error Message: {publish_data['error']['error_user_msg']}")
            return False

    except requests.exceptions.RequestException as req_err:
        print(f"Network or API request error during Instagram upload: {req_err}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during Instagram upload: {e}")
        return False

def main():
    folder_name = "Quotes_Videos"
    video_urls = get_videos_from_cloudinary_folder(folder_name)

    if not video_urls:
        print(f"No videos found in Cloudinary folder: '{folder_name}'. Exiting.")
        return

    # --- Pick a random video from the fetched list ---
    selected_video_url = random.choice(video_urls)
    print(f"\n--- Selected a random video for upload: {selected_video_url} ---")

    # Customize your caption here. You can make this more dynamic if needed.
    # For a GitHub Action, consider if you want this caption to be static or fetched/generated.
    caption = f"Here's your daily dose of inspiration! ✨ #quotes #motivation #inspiration #dailyquotes #randomvideo"
    
    success = upload_video_to_instagram(selected_video_url, caption)
    if success:
        print(f"\nRandom video upload process completed successfully!")
    else:
        print(f"\nFailed to upload the random video.")

if __name__ == "__main__":
    main()
