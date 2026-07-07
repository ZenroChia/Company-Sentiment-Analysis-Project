import time
import pandas as pd
import random
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime

# --- CONFIGURATION ---
START_PAGE = 1504 # <--- Adjust based on progress
TARGET_VALID_REVIEWS = 5000
MIN_WORD_COUNT = 15
CSV_FILENAME = "amazon_glassdoor_reviews2.csv"

# --- CONNECT TO EXISTING CHROME ---
print("Connecting to existing Chrome window...")
options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=options)

current_page = START_PAGE
reviews_collected = 4004 # <--- Adjust based on progress

# --- HELPER FUNCTIONS ---
def is_blocked(driver):
    page_text = driver.page_source.lower()
    return "help us protect glassdoor" in page_text or "verify you are human" in page_text

def human_scroll(driver):
    total_height = int(driver.execute_script("return document.body.scrollHeight"))
    current = 0
    while current < total_height:
        step = random.randint(200, 500)
        current += step
        driver.execute_script(f"window.scrollTo(0, {current});")
        time.sleep(random.uniform(0.3, 0.6))

# The reviews' XPATH structure of Glassdoor is changing once a specific time, 
# below structure is the most common structure Glassdoor uses.
# (Might not working, need to check on the spot during scrapping)
def find_reviews(driver):
    """Tries multiple different XPath selectors to find reviews"""
    possible_selectors = [
        "//div[contains(@id, 'empReview_')]",            
        "//li[contains(@class, 'empReview')]",            
        "//div[@data-test='review-details-container']",   
        "//div[contains(@class, 'gdReview')]",             
        "//div[contains(@class, 'review-module')]"         
    ]
    
    for selector in possible_selectors:
        reviews = driver.find_elements(By.XPATH, selector)
        if len(reviews) > 0:
            return reviews
            
    return [] # Found nothing

try:
    print(f"Resuming Scrape at Page {START_PAGE}. Target: {TARGET_VALID_REVIEWS}")
    
    # Check if file exists to determine header mode
    file_exists = os.path.isfile(CSV_FILENAME)
    
    while reviews_collected < TARGET_VALID_REVIEWS:
        # Standard URL structure for recent reviews
        url = f"https://www.glassdoor.com/Reviews/Amazon-Reviews-E6036_P{current_page}.htm?sort.sortType=RD&sort.ascending=false&filter.iso3Language=eng&filter.employmentStatus=REGULAR&filter.employmentStatus=PART_TIME"
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Navigate: Page {current_page} | Collected: {reviews_collected}")
        driver.get(url)

        # BLOCK CHECK
        if is_blocked(driver):
            print("\n!!! BLOCK DETECTED !!! Pausing 20 min...")
            for i in range(20, 0, -1):
                print(f"Resuming in {i} minutes...", end='\r')
                time.sleep(60)
            driver.refresh()
            time.sleep(10)

        # HUMAN WAIT
        # To prevent getting detected as bot and get blocked by the page
        wait_time = random.uniform(10, 20) 
        print(f"  Reading page... (Waiting {wait_time:.1f}s)")
        human_scroll(driver)
        time.sleep(wait_time/2) # Extra pause after scroll

        # --- SELECTOR STRATEGY ---
        reviews = find_reviews(driver)

        if len(reviews) == 0:
            print("  [!] No reviews found. Trying one refresh...")
            driver.refresh()
            time.sleep(15)
            reviews = find_reviews(driver)
            
            if len(reviews) == 0:
                print("  [!] Still 0 reviews. Skipping page (Glassdoor glitch or end of list).")
                current_page += 1
                continue

        new_rows = []
        
        for review in reviews:
            if reviews_collected >= TARGET_VALID_REVIEWS: break
            
            try:
                # EXTRACT (Using relative XPaths that act as wildcards)
                # We use .// to search INSIDE the review block regardless of its tag type
                
                try: pros = review.find_element(By.XPATH, ".//*[@data-test='review-text-PROS']").text
                except: pros = ""
                
                try: cons = review.find_element(By.XPATH, ".//*[@data-test='review-text-CONS']").text
                except: cons = ""

                # FILTER
                if (len(str(pros).split()) + len(str(cons).split())) < MIN_WORD_COUNT:
                    continue 

                # DETAILS
                try: job_title = review.find_element(By.XPATH, ".//*[@data-test='review-avatar-label']").text
                except: job_title = "N/A"

                try: headline = review.find_element(By.XPATH, ".//*[@data-test='review-details-title']").text
                except: headline = "N/A"

                try: rating = review.find_element(By.XPATH, ".//*[@data-test='review-rating-label']").text
                except: rating = "N/A"

                try: date_text = review.find_element(By.XPATH, ".//span[contains(@class, 'reviewDate')]").text
                except: date_text = "N/A"
                
                full_text = f"{headline}. Pros: {pros}. Cons: {cons}"
                
                row = {
                    "date": date_text,
                    "job_title": job_title,
                    "rating": rating,
                    "headline": headline,
                    "pros": pros,
                    "cons": cons,
                    "full_text": full_text
                }
                
                new_rows.append(row)
                reviews_collected += 1
                
            except Exception:
                continue

        print(f"  + Added {len(new_rows)} valid reviews.")

        if len(new_rows) > 0:
            df_page = pd.DataFrame(new_rows)
            # Append mode
            df_page.to_csv(CSV_FILENAME, mode='a', header=not os.path.isfile(CSV_FILENAME), index=False)
            print("  [Saved to CSV]")

        current_page += 1

except KeyboardInterrupt:
    print("\nScript stopped by user.")

except Exception as e:
    print(f"Error: {e}")

finally:
    print(f"Done. Total Collected: {reviews_collected}")