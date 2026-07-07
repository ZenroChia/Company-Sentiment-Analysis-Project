from seleniumbase import SB
import pandas as pd
import time
import random
import os
import re

# CONFIGURATION
TARGET_COMPANY_URL = "https://www.indeed.com/cmp/Amazon.com/reviews"
MIN_CHAR_LIMIT = 100
MAX_REVIEWS = 5000 

def scrape_indeed_reviews():
    results = []
    local_profile = "C:\\indeed_collector_2026"
    
    with SB(uc=True, user_data_dir=local_profile, headless=False) as sb:
        try:
            print("Step 1: Initializing Undetected Chrome...")
            sb.open(TARGET_COMPANY_URL)

            print("\n[!] MANUAL ACTION REQUIRED:")
            print("1. Scroll down to verify reviews are visible.")
            print("2. Solve any 'Are you human' checks immediately.")
            input(">>> Press ENTER in this terminal once page 1 is loaded...")

            while len(results) < MAX_REVIEWS:
                # JS EXTRACTOR
                js_script = """
                (function() {
                    let data = [];
                    let cards = document.querySelectorAll('div[data-testid="reviews[]"]');
                    
                    cards.forEach(card => {
                        let titleEl = card.querySelector('[data-testid="titleSpan"]');
                        let bodyEl = card.querySelector('[data-testid="review-text"]');
                        let ratingEl = card.querySelector('div[role="img"][aria-label*="stars"]');
                        let dateEl = card.querySelector('span.css-18clrlu'); 
                        let jobEl = card.querySelector('h4');
                        let locEl = card.querySelector('div.css-1uyfi54 span.css-1ekqr9') || 
                                    card.querySelector('div.css-s9rn75 div.css-1uyfi54 span');
                        
                        if(bodyEl) {
                            data.push({
                                'title': titleEl ? titleEl.innerText : 'N/A',
                                'comment': bodyEl.innerText,
                                'star_rating': ratingEl ? ratingEl.getAttribute('aria-label') : 'N/A',
                                'job_position': jobEl ? jobEl.innerText : 'N/A',
                                'date': dateEl ? dateEl.innerText : 'N/A',
                                'location': locEl ? locEl.innerText : 'N/A'
                            });
                        }
                    });
                    return data;
                })();
                """
                
                page_data = sb.execute_script(js_script)
                
                new_added = 0
                for entry in page_data:
                    if len(entry['comment']) >= MIN_CHAR_LIMIT:
                        if entry['comment'] not in [x['comment'] for x in results]:
                            results.append(entry)
                            new_added += 1
                    if len(results) >= MAX_REVIEWS: break

                print(f"Added {new_added} new. Total: {len(results)}/{MAX_REVIEWS}")

                # PERIODIC SAVE (Safety for long runs)
                if len(results) > 0 and len(results) % 100 == 0:
                    pd.DataFrame(results).to_csv("amazon_reviews_backup.csv", index=False)
                    print("--- Backup saved ---")

                # PAGINATION FIX: Wrapped in IIFE to avoid Illegal Return Error
                try:
                    sb.scroll_to_bottom()
                    time.sleep(2)
                    
                    click_next_js = """
                    (function() {
                        let buttons = document.querySelectorAll('button');
                        let nextBtn = Array.from(buttons).find(b => 
                            b.innerText.includes('Next') || 
                            (b.getAttribute('aria-label') && b.getAttribute('aria-label').includes('Next'))
                        );
                        if (nextBtn) {
                            nextBtn.click();
                            return true;
                        }
                        return false;
                    })();
                    """
                    
                    success = sb.execute_script(click_next_js)
                    
                    if success:
                        print("Navigating to next page...")
                        time.sleep(random.uniform(7, 12)) 
                    else:
                        print("Next button not found via JS. Attempting URL jump...")
                        curr = sb.get_current_url()
                        if "start=" in curr:
                            val = int(re.search(r'start=(\d+)', curr).group(1))
                            new_url = re.sub(r'start=\d+', f'start={val+20}', curr)
                        else:
                            separator = "&" if "?" in curr else "?"
                            new_url = f"{curr}{separator}start=20"
                        sb.open(new_url)
                        time.sleep(10)
                except Exception as e:
                    print(f"Pagination error handled: {e}")
                    # If we can't find the button, the loop usually ends
                    break

        except Exception as e:
            print(f"Critical error: {e}")

    # FINAL EXPORT
    if results:
        df = pd.DataFrame(results)
        # Regex updated to handle both "5" and "5.0"
        df['star_rating'] = df['star_rating'].str.extract(r'(\d+\.?\d*)').astype(float)
        df.to_csv("indeed_amazon_5000.csv", index=False)
        print(f"\nSUCCESS! {len(df)} reviews saved to indeed_amazon_5000.csv")
    else:
        print("No data collected.")

if __name__ == "__main__":
    scrape_indeed_reviews()