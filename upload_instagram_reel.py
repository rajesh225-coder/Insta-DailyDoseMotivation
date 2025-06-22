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
# INSTAGRAM_PAGE_ID is your Instagram Business Account ID
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_PAGE_ID = os.environ.get("INSTAGRAM_PAGE_ID")

# --- Facebook Configuration ---
# Fetch Facebook credentials from environment variables (GitHub Secrets)
# FACEBOOK_PAGE_ID is your actual numeric Facebook Page ID (e.g., from me/accounts)
FACEBOOK_PAGE_ACCESS_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID")


def get_videos_from_cloudinary_folder(folder_name="Quotes_Videos"):
    """
    Fetches video URLs from a specified Cloudinary folder.
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
            resource_type="video",
            prefix=f"{folder_name}/",
            max_results=500 # Adjust as needed
        )
        video_urls = [resource['secure_url'] for resource in result.get('resources', [])]
        print(f"Successfully fetched {len(video_urls)} videos from Cloudinary folder '{folder_name}'.")
        return video_urls
    except Exception as e:
        print(f"Error fetching videos from Cloudinary: {e}")
        return []

# def upload_video_to_instagram(video_url, caption):
#     """
#     Uploads a video to Instagram via the Facebook Graph API (as a Reel).
#     Requires an Instagram Business Account ID and its associated Page Access Token.
#     """
#     if not INSTAGRAM_ACCESS_TOKEN:
#         print("Error: Instagram access token not configured in environment variables.")
#         return False
#     if not INSTAGRAM_PAGE_ID:
#         print("Error: Instagram page ID (Instagram Business Account ID) not configured in environment variables.")
#         return False

#     try:
#         # Step 1: Create a media container on Instagram (via Facebook Graph API)
#         container_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_PAGE_ID}/media"
#         container_payload = {
#             'media_type': 'REELS', # Use REELS for video uploads to Instagram feed
#             'video_url': video_url,
#             'caption': caption,
#             'access_token': INSTAGRAM_ACCESS_TOKEN,
#             'share_to_feed': True # Makes sure the Reel also appears on your main profile grid
#         }
#         print(f"\n--- Starting Instagram Upload Process ---")
#         print(f"Creating Instagram media container for video: {video_url}")
#         container_response = requests.post(container_url, data=container_payload)
#         container_data = container_response.json()

#         if 'id' not in container_data:
#             print(f"Error creating Instagram container. Response: {container_data}")
#             if 'error' in container_data and 'error_user_msg' in container_data['error']:
#                 print(f"Instagram API Error Message: {container_data['error']['error_user_msg']}")
#             return False

#         creation_id = container_data['id']
#         print(f"Instagram media container created with ID: {creation_id}.")

#         # --- Polling for media status (CRITICAL for videos) ---
#         status_check_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code&access_token={INSTAGRAM_ACCESS_TOKEN}"
        
#         max_retries = 30 # Max attempts to check status
#         sleep_interval = 10 # Seconds to wait between checks
        
#         print("Waiting for Instagram video to be processed...")
#         for i in range(max_retries):
#             time.sleep(sleep_interval)
#             status_response = requests.get(status_check_url).json()
#             status_code = status_response.get('status_code')

#             print(f"Attempt {i+1}/{max_retries}: Instagram Media status code: {status_code}")

#             if status_code == 'FINISHED':
#                 print("Instagram video processing finished. Ready to publish.")
#                 break
#             elif status_code == 'ERROR':
#                 print(f"Error during Instagram video processing. Response: {status_response}")
#                 return False
#             elif i == max_retries - 1:
#                 print("Max retries reached. Instagram video did not finish processing in time.")
#                 return False
#         else: # This 'else' executes if the loop completes without a 'break'
#             print("Instagram polling loop completed without 'FINISHED' status. Could not publish.")
#             return False

#         # Step 2: Publish the created media container to Instagram
#         publish_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_PAGE_ID}/media_publish"
#         publish_payload = {
#             'creation_id': creation_id,
#             'access_token': INSTAGRAM_ACCESS_TOKEN
#         }
#         print(f"Publishing video to Instagram with creation ID: {creation_id}")
#         publish_response = requests.post(publish_url, data=publish_payload)
#         publish_data = publish_response.json()

#         if 'id' in publish_data:
#             print(f"Video successfully uploaded to Instagram! Post ID: {publish_data['id']}")
#             return True
#         else:
#             print(f"Error publishing video to Instagram. Response: {publish_data}")
#             if 'error' in publish_data and 'error_user_msg' in publish_data['error']:
#                 print(f"Instagram API Error Message: {publish_data['error']['error_user_msg']}")
#             return False

#     except requests.exceptions.RequestException as req_err:
#         print(f"Network or API request error during Instagram upload: {req_err}")
#         return False
#     except Exception as e:
#         print(f"An unexpected error occurred during Instagram upload: {e}")
#         return False

def upload_video_to_facebook_page(video_url, title, description):
    """
    Uploads a video to a Facebook Page.
    Requires a Facebook Page ID and a Page Access Token with publish_video or pages_manage_posts permission.
    """
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        print("Error: Facebook Page access token not configured in environment variables.")
        return False
    if not FACEBOOK_PAGE_ID:
        print("Error: Facebook Page ID not configured in environment variables.")
        return False

    try:
        # Facebook Page video upload endpoint
        # The 'file_url' parameter is used for external URLs for Facebook videos.
        upload_url = f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/videos"
        upload_payload = {
            'file_url': video_url, # The URL of the video hosted on Cloudinary
            'title': title,
            'description': description,
            'access_token': FACEBOOK_PAGE_ACCESS_TOKEN,
            'published': True, # Set to True to publish immediately
            'embeddable': True # Allows the video to be embedded
        }
        
        print(f"\n--- Starting Facebook Upload Process ---")
        print(f"Attempting to upload video to Facebook Page: {video_url}")
        response = requests.post(upload_url, data=upload_payload)
        response_data = response.json()

        if 'id' in response_data:
            print(f"Video upload initiated for Facebook! Video ID: {response_data['id']}")
            # Facebook video uploads are asynchronous. The 'id' means the request was accepted.
            # For robust production use, you might poll for the video's status on Facebook.
            return True
        else:
            print(f"Error uploading video to Facebook. Response: {response_data}")
            if 'error' in response_data and 'message' in response_data['error']:
                print(f"Facebook API Error Message: {response_data['error']['message']}")
            return False

    except requests.exceptions.RequestException as req_err:
        print(f"Network or API request error during Facebook upload: {req_err}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during Facebook upload: {e}")
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

    # --- Customize your captions/titles/descriptions ---
    # Instagram Caption
    instagram_caption = f"Here's your daily dose of inspiration! ✨ #quotes #motivation #inspiration #dailyquotes #randomvideo"
    
    # Facebook Title and Description
    # You can make these dynamic (e.g., from a list of titles, or extract from video metadata)
    facebook_title = "Daily Motivational Quote Video"
    facebook_description = f"Get inspired with today's random quote video. #motivation #quotes #inspiration\n\nVideo source: {selected_video_url}"
    
    # --- Execute Uploads ---
    
    # Upload to Instagram
    # instagram_success = upload_video_to_instagram(selected_video_url, instagram_caption)
    # if instagram_success:
    #     print(f"\nRandom video upload process to Instagram completed successfully!")
    # else:
    #     print(f"\nFailed to upload the random video to Instagram.")

    # Upload to Facebook
    # We proceed with Facebook upload even if Instagram failed, unless you want to stop on Instagram failure.
    facebook_success = upload_video_to_facebook_page(selected_video_url, facebook_title, facebook_description)
    if facebook_success:
        print(f"\nRandom video upload process to Facebook completed successfully!")
    else:
        print(f"\nFailed to upload the random video to Facebook.")


if __name__ == "__main__":
    main()
