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


def get_resources_from_cloudinary_folder(folder_name, resource_type):
    """
    Fetches resource URLs (videos or images) from a specified Cloudinary folder.
    """
    try:
        # Check if Cloudinary credentials are set from environment variables
        if not cloudinary.config().cloud_name or \
           not cloudinary.config().api_key or \
           not cloudinary.config().api_secret:
            print("Error: Cloudinary credentials not set in environment variables.")
            return []

        result = cloudinary.api.resources(
            type="upload",
            resource_type=resource_type,
            prefix=f"{folder_name}/",
            max_results=500  # Adjust as needed
        )
        resource_urls = [resource['secure_url'] for resource in result.get('resources', [])]
        print(f"Successfully fetched {len(resource_urls)} {resource_type}s from Cloudinary folder '{folder_name}'.")
        return resource_urls
    except Exception as e:
        print(f"Error fetching {resource_type}s from Cloudinary: {e}")
        return []


def upload_video_to_instagram(video_url, caption, thumbnail_url=None):
    """
    Uploads a video to Instagram via the Facebook Graph API (as a Reel) with an optional thumbnail.
    Requires an Instagram Business Account ID and its associated Page Access Token.
    """
    if not INSTAGRAM_ACCESS_TOKEN:
        print("Error: Instagram access token not configured in environment variables.")
        return False
    if not INSTAGRAM_PAGE_ID:
        print("Error: Instagram page ID (Instagram Business Account ID) not configured in environment variables.")
        return False

    try:
        # Step 1: Create a media container on Instagram (via Facebook Graph API)
        container_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_PAGE_ID}/media"
        container_payload = {
            'media_type': 'REELS',  # Use REELS for video uploads to Instagram feed
            'video_url': video_url,
            'caption': caption,
            'access_token': INSTAGRAM_ACCESS_TOKEN,
            'share_to_feed': True,  # Makes sure the Reel also appears on your main profile grid
        }
        if thumbnail_url:
            container_payload['thumb_url'] = thumbnail_url  # Add thumbnail URL

        print(f"\n--- Starting Instagram Video Upload Process ---")
        print(f"Creating Instagram media container for video: {video_url}")
        if thumbnail_url:
            print(f"Using thumbnail: {thumbnail_url}")

        container_response = requests.post(container_url, data=container_payload)
        container_data = container_response.json()

        if 'id' not in container_data:
            print(f"Error creating Instagram container. Response: {container_data}")
            if 'error' in container_data and 'error_user_msg' in container_data['error']:
                print(f"Instagram API Error Message: {container_data['error']['error_user_msg']}")
            return False

        creation_id = container_data['id']
        print(f"Instagram media container created with ID: {creation_id}.")

        # --- Polling for media status (CRITICAL for videos) ---
        status_check_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code&access_token={INSTAGRAM_ACCESS_TOKEN}"

        max_retries = 30  # Max attempts to check status
        sleep_interval = 10  # Seconds to wait between checks

        print("Waiting for Instagram video to be processed...")
        for i in range(max_retries):
            time.sleep(sleep_interval)
            status_response = requests.get(status_check_url).json()
            status_code = status_response.get('status_code')

            print(f"Attempt {i+1}/{max_retries}: Instagram Media status code: {status_code}")

            if status_code == 'FINISHED':
                print("Instagram video processing finished. Ready to publish.")
                break
            elif status_code == 'ERROR':
                print(f"Error during Instagram video processing. Response: {status_response}")
                return False
            elif i == max_retries - 1:
                print("Max retries reached. Instagram video did not finish processing in time.")
                return False
        else:  # This 'else' executes if the loop completes without a 'break'
            print("Instagram polling loop completed without 'FINISHED' status. Could not publish.")
            return False

        # Step 2: Publish the created media container to Instagram
        publish_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_PAGE_ID}/media_publish"
        publish_payload = {
            'creation_id': creation_id,
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        print(f"Publishing video to Instagram with creation ID: {creation_id}")
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
    video_folder_name = "DailyDose"
    thumbnail_folder_name = "thumbnail"

    # Fetch resources from Cloudinary
    video_urls = get_resources_from_cloudinary_folder(video_folder_name, "video")
    thumbnail_urls = get_resources_from_cloudinary_folder(thumbnail_folder_name, "image")

    # --- Video Posting Logic ---
    if not video_urls:
        print(f"No videos found in Cloudinary folder: '{video_folder_name}'. Skipping video upload.")
        return # Exit if no videos to post

    # Pick a random video
    selected_video_url = random.choice(video_urls)
    print(f"\n--- Selected a random video for upload: {selected_video_url} ---")

    # Pick a random thumbnail if available
    selected_thumbnail_url = None
    if thumbnail_urls:
        selected_thumbnail_url = random.choice(thumbnail_urls)
        print(f"--- Selected thumbnail: {selected_thumbnail_url} ---")
    else:
        print(f"Warning: No thumbnails found in '{thumbnail_folder_name}'. Video will be posted without a custom thumbnail.")

    # Customize Instagram caption for video
    instagram_video_caption = f"✨ #quotes #couple #quotes #love #randomvideo #reels"

    # Upload video to Instagram
    instagram_video_success = upload_video_to_instagram(selected_video_url, instagram_video_caption, selected_thumbnail_url)
    if instagram_video_success:
        print(f"\nRandom video upload process to Instagram completed successfully!")
    else:
        print(f"\nFailed to upload the random video to Instagram.")


if __name__ == "__main__":
    main()
