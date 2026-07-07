import requests
import pandas as pd
from datetime import datetime
import time

def get_reddit_post_data(post_url):
    print(f"\nScraping: {post_url}")
    
    # Append .json to the URL to get JSON data
    if not post_url.endswith('.json'):
        json_url = post_url.rstrip('/') + '.json'
    else:
        json_url = post_url
    
    # Set headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Make request to Reddit
        response = requests.get(json_url, headers=headers)
        response.raise_for_status()
        
        # Parse JSON data
        data = response.json()
        
        # Extract post data (first item in the response)
        post_data_raw = data[0]['data']['children'][0]['data']
        
        # Extract comments data (second item in the response)
        comments_data_raw = data[1]['data']['children']
        
        all_data = []
        
        # Process the main post, flatten the post into the same row structure we use for comments
        post_info = {
            'type': 'post',
            'post_id': post_data_raw.get('id', ''),
            'title': post_data_raw.get('title', ''),
            'subreddit': post_data_raw.get('subreddit', ''),
            'author': post_data_raw.get('author', '[deleted]'),
            'created_utc': datetime.fromtimestamp(post_data_raw.get('created_utc', 0)).strftime('%Y-%m-%d %H:%M:%S'),
            'score': post_data_raw.get('score', 0),
            'upvote_ratio': post_data_raw.get('upvote_ratio', 0),
            'num_comments': post_data_raw.get('num_comments', 0),
            'selftext': post_data_raw.get('selftext', ''),
            'url': post_data_raw.get('url', ''),
            'permalink': f"https://reddit.com{post_data_raw.get('permalink', '')}",
            'comment_id': '',
            'comment_body': '',
            'comment_author': '',
            'comment_score': '',
            'comment_created_utc': '',
            'parent_id': '',
            'is_submitter': ''
        }
        
        all_data.append(post_info)
        print(f" Post: {post_info['title'][:60]}...")
        
        # Process all comments recursively
        comment_count = 0
        
        def extract_comments(comment_list, post_id, post_title, post_author, post_subreddit):
            nonlocal comment_count
            
            for comment_item in comment_list:
                if comment_item['kind'] == 't1':
                    comment_data = comment_item['data']
                    
                    # Skip "more comments" placeholders
                    if comment_data.get('body') in [None, '[deleted]', '[removed]']:
                        body = comment_data.get('body', '[deleted]')
                    else:
                        body = comment_data.get('body', '')
                    
                    comment_info = {
                        'type': 'comment',
                        'post_id': post_id,
                        'title': post_title,
                        'subreddit': post_subreddit,
                        'author': post_author,
                        'created_utc': datetime.fromtimestamp(comment_data.get('created_utc', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                        'selftext': '',
                        'url': '',
                        'permalink': f"https://reddit.com{comment_data.get('permalink', '')}",
                        'comment_id': comment_data.get('id', ''),
                        'comment_body': body,
                        'comment_author': comment_data.get('author', '[deleted]'),
                        'comment_score': comment_data.get('score', 0),
                        'comment_created_utc': datetime.fromtimestamp(comment_data.get('created_utc', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                        'parent_id': comment_data.get('parent_id', ''),
                        'is_submitter': comment_data.get('is_submitter', False)
                    }
                    
                    all_data.append(comment_info)
                    comment_count += 1
                    
                    # Process nested replies recursively, read through replies if there any.
                    if 'replies' in comment_data and comment_data['replies']:
                        if isinstance(comment_data['replies'], dict):
                            replies_list = comment_data['replies']['data']['children']
                            extract_comments(replies_list, post_id, post_title, post_author, post_subreddit)
        
        # Extract all comments
        extract_comments(
            comments_data_raw,
            post_info['post_id'],
            post_info['title'],
            post_info['author'],
            post_info['subreddit']
        )
        
        print(f" Scraped: 1 post + {comment_count} comments")
        return all_data
        
    except requests.exceptions.RequestException as e:
        print(f" Network error: {str(e)}")
        return []
    except (KeyError, IndexError, ValueError) as e:
        print(f" Parsing error: {str(e)}")
        return []
    except Exception as e:
        print(f" Unexpected error: {str(e)}")
        return []

# # Loops through a list of Reddit URLs one by one and collects all the data.
def scrape_multiple_posts(post_urls):
    all_posts_data = []
    successful_scrapes = 0
    failed_scrapes = 0
    
    print("=" * 70)
    print(f" Starting to scrape {len(post_urls)} Reddit posts...")
    print("=" * 70)
    
    for idx, url in enumerate(post_urls, 1):
        print(f"\n[{idx}/{len(post_urls)}] ", end="")
        
        post_data = get_reddit_post_data(url)
        
        if post_data:
            all_posts_data.extend(post_data)
            successful_scrapes += 1
        else:
            failed_scrapes += 1
        
        # Rate limiting 
        if idx < len(post_urls):
            wait_time = 10
            print(f" Waiting {wait_time} seconds before next post...")
            time.sleep(wait_time)
    
    print("\n" + "=" * 70)
    print("SCRAPING COMPLETE")
    print("=" * 70)
    print(f" Successful: {successful_scrapes}/{len(post_urls)}")
    print(f" Failed: {failed_scrapes}/{len(post_urls)}")
    print(f"Total data rows collected: {len(all_posts_data)}")
    
    return all_posts_data

def save_to_csv(data, filename='amazon_work_culture_merged.csv'):
    if not data:
        print("\n No data to save!")
        return None
    
    df = pd.DataFrame(data)
    
    # Reorder columns for better readability
    column_order = [
        'type', 'post_id', 'title', 'subreddit', 'author',
        'created_utc', 'score', 'upvote_ratio', 'num_comments',
        'selftext', 'comment_id', 'comment_author', 'comment_created_utc',
        'comment_body', 'comment_score', 'is_submitter', 'parent_id', 
        'permalink', 'url'
    ]
    
    df = df[column_order]
    
    # Save to CSV with UTF-8 encoding
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    
    print("\n" + "=" * 70)
    print(" CSV FILE SAVED SUCCESSFULLY")
    print("=" * 70)
    print(f" Filename: {filename}")
    print(f" Total rows: {len(df):,}")
    print(f" Posts: {len(df[df['type'] == 'post']):,}")
    print(f" Comments: {len(df[df['type'] == 'comment']):,}")
    
    # Show breakdown by subreddit
    print("\n Posts by Subreddit:")
    post_df = df[df['type'] == 'post']
    subreddit_counts = post_df['subreddit'].value_counts()
    for subreddit, count in subreddit_counts.items():
        print(f"  - r/{subreddit}: {count}")
    
    # Show top posts by score
    print("\n Top 3 Posts by Score:")
    top_posts = post_df.nlargest(3, 'score')[['title', 'score', 'num_comments']]
    for idx, row in top_posts.iterrows():
        print(f"  {row['score']:,} pts | {row['num_comments']} comments | {row['title'][:50]}...")
    
    return df

def main():
    print("\n" + "=" * 70)
    print("REDDIT SCRAPER - NO API KEY REQUIRED!")
    print("Scrapes using publicly available JSON data")
    print("=" * 70)
    print()
    
    # ============================================================
    # ADD YOUR REDDIT POST URLs HERE
    # ============================================================
    
    post_urls = [
        'https://www.reddit.com/r/careerguidance/comments/1of3bda/how_is_work_culture_at_amazon/',
        'https://www.reddit.com/r/amazonemployees/comments/1g014yh/anybody_actually_enjoy_working_at_amazon/',
        'https://www.reddit.com/r/cscareerquestions/comments/1dong7g/is_amazons_bad_reputation_based_on_reality/',
        'https://www.reddit.com/r/cscareerquestions/comments/1ckrqcw/whats_it_like_working_at_amazon_now_days/',
        'https://www.reddit.com/r/amazonemployees/comments/1n8u7fk/hey_folks_i_see_lot_on_amazon_majority_saying_its/',
        'https://www.reddit.com/r/womenintech/comments/1gqt50a/anyone_else_here_work_at_amazon_and_miserable/',
        'https://www.reddit.com/r/amazonemployees/comments/1pq077s/the_dark_reality_of_amazon_work_culture_from/',
        'https://www.reddit.com/r/cscareerquestions/comments/4fg44p/11_reasons_working_for_amazon_is_the_worst_ever/'
    ]
    
    # ============================================================
    
    print(f" {len(post_urls)} post(s) queued for scraping\n")
    
    # Scrape all posts
    all_data = scrape_multiple_posts(post_urls)
    
    # Save merged data to CSV
    if all_data:
        df = save_to_csv(all_data, 'amazon_work_culture_merged.csv')
        
        print("\n" + "=" * 70)
        print("ALL DONE! Your data is ready in: amazon_work_culture_merged.csv")
        print("=" * 70)
    else:
        print("\n No data was collected. Please check your URLs.")

if __name__ == "__main__":
    main()