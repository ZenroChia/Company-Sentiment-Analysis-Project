# ----------------- GETTING YOUTUBE VIDEOID AND SAVED -----------------

import pandas as pd
from googleapiclient.discovery import build

# --- CONFIGURATION ---
API_KEY = 'AIzaSyDZJMXiCHwMrl5aOBcIyRKMWUS4PeQBsv0'  
OUTPUT_FILENAME = "amazon_YT_videoID.csv"

''' 
Since reviews will probably be bias based on the video,
(if video talking "why I hate Amazon", 
the comments will have more negative comments of the company too)

so we will try to balance the number of comments of each classes (positive, neutral, negative)
by searching videos with specific keywords as below:
'''
SEARCH_QUERIES = [
    "why i quit amazon",                    # Bucket A: Critics
    "amazon software engineer day in life", # Bucket B: Fans
    "working at amazon pros and cons",      # Bucket C: Neutrals
    "truth about amazon warehouse job"      # Specific Role
]

def GET_videos():
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    video_candidates = []
    video_ids_seen = set()

    print("Scouting for videos...")

    for query in SEARCH_QUERIES:
        print(f"  > Searching: '{query}'")
        
        request = youtube.search().list(
            q=query,
            type="video",
            part="id,snippet",
            maxResults=10, 
            relevanceLanguage="en"
        )
        response = request.execute()

        for item in response.get('items', []):
            vid_id = item['id']['videoId']
            title = item['snippet']['title']
            channel = item['snippet']['channelTitle']
            
            if vid_id not in video_ids_seen:
                video_candidates.append({
                    "Keep?": "YES", 
                    "Category": query,
                    "Video_ID": vid_id,
                    "Title": title,
                    "Channel": channel,
                    "URL": f"https://www.youtube.com/watch?v={vid_id}"
                })
                video_ids_seen.add(vid_id)

    # Save to CSV for manual checking
    # Manual check the comments balanced on each videoId
    # Only certain video's comments will be extracted, NOT ALL
    df = pd.DataFrame(video_candidates)
    df.to_csv(OUTPUT_FILENAME, index=False)
    print(f"\nDone! Found {len(video_candidates)} videos.")
    print(f"Open '{OUTPUT_FILENAME}', check the videos, and delete the rows you don't want.")


# ----------------- EXTRACT COMMENTS BASED ON VIDEOID CHOSEN -----------------

# --- CONFIGURATION ---
INPUT_FILENAME = "amazon_YT_videoID.csv"
FINAL_OUTPUT = "amazon_YT_reviews.csv"
TARGET_COMMENTS_PER_VIDEO = 200 

# FILTER SETTINGS
MIN_WORD_COUNT = 5 

def GET_comments():
    try:
        df_videos = pd.read_csv(INPUT_FILENAME)
        video_list = df_videos['Video_ID'].tolist()
        print(f"Loaded {len(video_list)} approved videos.")
    except FileNotFoundError:
        print("Error: 'review_these_videos.csv' not found.")
        return

    youtube = build('youtube', 'v3', developerKey=API_KEY)
    all_comments = []
    stats = {"scraped": 0, "saved": 0, "junk_removed": 0}

    for vid_id in video_list:
        print(f"  > Scraping Video ID: {vid_id}...")
        
        comments_collected_on_video = 0
        next_page_token = None
        
        while comments_collected_on_video < TARGET_COMMENTS_PER_VIDEO:
            try:
                request = youtube.commentThreads().list(
                    part="snippet",
                    videoId=vid_id,
                    maxResults=300, 
                    textFormat="plainText",
                    pageToken=next_page_token
                )
                response = request.execute()

                for item in response.get('items', []):
                    stats["scraped"] += 1

                    comment_data = item['snippet']['topLevelComment']['snippet']
                    text_content = str(comment_data['textDisplay'])
                    
                    # Word Count Check (Simple Filtering)
                    words = text_content.split()
                    if len(words) < MIN_WORD_COUNT:
                        stats["junk_removed"] += 1
                        continue 

                    # --- SAVE VALID COMMENT ---
                    all_comments.append({
                        "video_id": vid_id,
                        "author": comment_data['authorDisplayName'],
                        "date": comment_data['publishedAt'],
                        "likes": comment_data['likeCount'],
                        "full_text": text_content
                    })
                    comments_collected_on_video += 1
                    stats["saved"] += 1
                    
                    if comments_collected_on_video >= TARGET_COMMENTS_PER_VIDEO:
                        break
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break 

            except Exception as e:
                print(f"    ! Error: {e}")
                break

        print(f"    + Saved {comments_collected_on_video} relevant comments.")

    # Save
    if len(all_comments) > 0:
        df_final = pd.DataFrame(all_comments)
        df_final.to_csv(FINAL_OUTPUT, index=False)
        print("\n" + "="*40)
        print(f"FINAL REPORT")
        print(f"Total Scraped: {stats['scraped']}")
        print(f"Junk Removed:  {stats['junk_removed']} (Too short or irrelevant)")
        print(f"Valid Saved:   {stats['saved']}")
        print(f"Data saved to '{FINAL_OUTPUT}'")
        print("="*40)
    else:
        print("No comments collected.")

# GET_videos()
GET_comments()