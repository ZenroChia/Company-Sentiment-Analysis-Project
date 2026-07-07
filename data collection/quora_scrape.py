# ========================================================
# IMPORTS & LIBRARIES
# ========================================================
import time
import random
import shutil
import os
import re # For date extraction
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ========================================================
# CONFIGURATION & TARGET URLS
# ========================================================
COMPANY_NAME = "Amazon"
TARGET_URLS = [
    "https://www.quora.com/How-do-Amazon-employees-feel-about-their-work-culture",
    "https://www.quora.com/Is-Amazon-a-good-company",
    "https://www.quora.com/What-are-peoples-experiences-with-working-for-Amazon-Are-there-more-negative-or-positive-reviews-Why",
    "https://www.quora.com/Is-being-an-Amazon-employee-as-bad-as-some-people-say-it-is",
    "https://www.quora.com/Is-Amazon-a-bad-place-to-work-or-is-it-certain-jobs-that-make-it-bad",
    "https://www.quora.com/What-are-the-pros-and-cons-of-working-at-Amazon",
    "https://www.quora.com/As-an-Amazon-warehouse-worker-what-is-your-experience-of-working-there",
    "https://www.quora.com/Is-Amazon-an-unpleasant-place-to-work-Why-or-why-not",
    "https://www.quora.com/What-is-it-really-like-to-work-in-an-Amazon-warehouse-Is-it-as-bad-as-some-folks-say-it-is",
    "https://www.quora.com/How-is-your-experience-of-working-for-Amazon-India-as-a-present-employee-or-in-the-past?topAns=110354130",
    "https://www.quora.com/If-the-culture-at-Amazon-is-so-cutthroat-why-do-so-many-people-still-choose-to-work-there",
    "https://www.quora.com/How-is-the-work-culture-at-Amazon-com",
    "https://www.quora.com/Why-do-so-many-people-dislike-working-at-Amazon",
    "https://www.quora.com/unanswered/What-do-you-think-of-your-job-at-Amazon-for-those-of-you-who-work-there",
    "https://www.quora.com/How-are-Amazon-TRMS-jobs",
    "https://www.quora.com/What-has-been-your-experience-working-at-Amazon-and-what-was-your-work-level",
    "https://www.quora.com/What-is-it-like-to-work-at-Amazon-in-India",
    "https://www.quora.com/What-it-is-like-to-work-as-a-customer-service-associate-at-Amazon-India",
    "https://www.quora.com/Are-the-horrible-work-life-balance-rumors-at-Amazon-India-engineering-teams-true",
    "https://www.quora.com/What-is-it-like-to-be-a-software-engineer-at-Amazon",
    "https://www.quora.com/Is-Amazon-probably-one-of-the-worst-tech-places-to-work-due-to-the-excessive-work-hours-and-stress",
    "https://www.quora.com/What-is-it-like-to-work-at-Amazon-Hyderabad-India",
    "https://www.quora.com/Is-the-work-life-balance-at-Amazon-as-a-software-engineer-really-that-bad"
]

ANSWER_CSS_SELECTOR = 'div.spacing_log_answer_content'

# ========================================================
# SELENIUM DRIVER SETUP
# ========================================================
def setup_driver():
    """Initializes a Chrome browser with a temp profile."""
    print("Setting up driver...")

    original_user_data_dir = r"YOUR_CHROME_USER_DATA_DIRECTORY_ON_YOUR_LOCAL_MACHINE"
    temp_user_data_dir = os.path.join(os.getcwd(), "temp_chrome_profile")

    if os.path.exists(temp_user_data_dir):
        try:
            shutil.rmtree(temp_user_data_dir)
            print("Cleaned up old temp profile.")
        except Exception as e:
            print(f"Warning: Could not clean up temp profile: {e}")

    print("Cloning Chrome profile... (This may take 10-20 seconds)")

    os.makedirs(os.path.join(temp_user_data_dir, "Default"), exist_ok=True)
    src_default = os.path.join(original_user_data_dir, "Default")
    dst_default = os.path.join(temp_user_data_dir, "Default")

    try:
        shutil.copytree(src_default, dst_default, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("Cache*", "Code Cache", "Service Worker"))
    except Exception as e:
        print(f"Non-critical copy error: {e}")

    print("Profile cloned. Launching Selenium...")

    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={temp_user_data_dir}")
    chrome_options.add_argument("--profile-directory=Default")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(60)
    return driver

# ========================================================
# MAIN SCRAPING LOGIC
# ========================================================
def scrape_quora():
    print("Initializing Driver...")
    driver = setup_driver()
    print("Driver initialized successfully.")

    all_comments = []

    for url in TARGET_URLS:
        print(f"--- Scraping: {url} ---")
        try:
            driver.get(url)
            time.sleep(3)

            # ========================================================
            # FILTER SWITCHER
            # ========================================================
            try:
                # Nudge to trigger rendering
                driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(1)

                wait = WebDriverWait(driver, 15)
                filter_xpath = "//*[contains(text(), 'Answers (') or contains(text(), 'All related (')]"
                filter_text_element = wait.until(EC.presence_of_element_located((By.XPATH, filter_xpath)))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", filter_text_element)

                current_text = filter_text_element.text
                print(f"DEBUG: Found filter element -> '{current_text}'")

                if "Answers (" in current_text:
                    print("Status: Already on 'Answers' view.")

                    try:
                        num_answers = int(current_text.split('(')[1].split(')')[0])
                    except:
                        num_answers = 80
                else:
                    print("Status: Switching view...")
                    driver.execute_script("arguments[0].click();", filter_text_element)

                    answers_menu_option = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Answers (')]")))
                    driver.execute_script("arguments[0].click();", answers_menu_option)

                    print("Status: Clicked 'Answers'. Waiting for reload...")
                    time.sleep(3)

                    # Re-fetch count after reload
                    try:
                        updated_filter_btn = driver.find_element(By.XPATH, filter_xpath)
                        new_text = updated_filter_btn.text
                        if "Answers (" in new_text:
                            num_answers = int(new_text.split('(')[1].split(')')[0])
                            print(f"DEBUG: Exact Answer Count Updated -> {num_answers}")
                    except:
                        num_answers = 80

            except Exception as e:
                print(f"Filter Info: Standard filter not found. Using default scroll settings.")
                num_answers = 80

            # ========================================================
            # SCROLLING
            # ========================================================
            scroll_count = (num_answers // 10) + 2

            print(f"Plan: Scrolling {scroll_count} times...")
            for i in range(scroll_count):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                print(f"Scrolling... ({i+1}/{scroll_count})")
                time.sleep(random.uniform(2, 4))

            # ========================================================
            # EXPAND COMMENTS (READ MORE BUTTON)
            # ========================================================
            try:
                more_buttons = driver.find_elements(By.CSS_SELECTOR, ".qt_read_more")
                print(f"Clicking {len(more_buttons)} 'Read More' buttons...")
                for btn in more_buttons:
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.1)
                    except: pass
            except Exception as e:
                print("Read More Warning:", e)

            # ========================================================
            # HTML PARSING & METADATA EXTRACTION
            # ========================================================
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            answers = soup.select(ANSWER_CSS_SELECTOR)
            print(f"Found {len(answers)} potential comments on this page.")

            for div in answers:
                try:
                    # 1. FIND HEADER
                    # The header sits immediately before the content div in the DOM structure
                    header = div.find_previous(class_="spacing_log_answer_header")

                    # 2. FILTER PROMOTED/ADS
                    # Check text in the header/parent for "Promoted" or "Sponsored"
                    parent_text = div.find_parent().find_parent().find_parent().get_text()
                    if "Promoted" in parent_text or "Sponsored" in parent_text:
                        print("Skipping Promoted/Ad content...")
                        continue

                    # 3. FILTER AI ASSISTANT
                    # Check for the Bot profile image
                    profile_img = div.find_previous('img', attrs={'alt': True})
                    if profile_img and "Assistant" in profile_img['alt']:
                        print("Skipping AI Assistant answer...")
                        continue

                    # 4. EXTRACT METADATA
                    # -- Name --
                    name = "Anonymous"
                    if header:
                        name_tag = header.select_one("span.qu-bold")
                        if name_tag:
                            name = name_tag.get_text(strip=True)

                    # -- Position --
                    position = "Null"
                    if header:
                        pos_tag = header.select_one("span.qu-borderBottom")
                        if pos_tag:
                            position = pos_tag.get_text(strip=True)

                    # -- Date --
                    date = ""
                    if header:
                        date_tag = header.select_one("a.answer_timestamp")
                        if date_tag:
                            raw_date = date_tag.get_text(strip=True)
                            date_match = re.search(r'\d.*', raw_date)
                            if date_match:
                                date = date_match.group(0)
                            else:
                                date = raw_date

                    # 5. EXTRACT COMMENT TEXT
                    paragraphs = div.find_all('p')
                    if paragraphs:
                        text = " ".join([p.get_text(strip=True) for p in paragraphs])
                    else:
                        text = div.get_text(strip=True)

                    text = text.replace("(more)", "").strip()

                    all_comments.append({
                        "Source": "Quora",
                        "Company": COMPANY_NAME,
                        "Name": name,
                        "Position": position,
                        "Date": date,
                        "Comment_Text": text,
                        "Sentiment_Label": ""
                    })

                except Exception as e:
                    # pass silently on individual row errors to keep scraping
                    pass

        except Exception as e:
            print(f"CRITICAL ERROR scraping {url}: {e}")

    driver.quit()

    # ========================================================
    # CLEANUP & SAVE
    # ========================================================
    if all_comments:
        df = pd.DataFrame(all_comments)
        df.drop_duplicates(subset=["Comment_Text"], inplace=True)

        output_filename = "/content/drive/MyDrive/F20AA - Coursework datasets/quora_reviews_detailed.csv"
        df.to_csv(output_filename, index=False)
        print(f"SUCCESS: Scraped {len(df)} unique comments with metadata. Saved to {output_filename}")
        print(df.head())
    else:
        print("FAILED: No comments collected.")

if __name__ == "__main__":
    scrape_quora()