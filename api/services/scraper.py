# scraper.py
import time
import logging
import os
import shutil
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import traceback

from api.services.ai_engine.parser import extract_text_from_pdf
from api.services.ai_engine.summarizer import summarize_text
from api.services.ai_engine.scorer import score_tender

# Define directory paths
BASE_DIR = os.getcwd()
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')
DATA_DIR = os.path.join(BASE_DIR, 'data')
TEMP_DOWNLOAD_DIR = os.path.join(BASE_DIR, 'temp_downloads')

# Ensure directories exist
for directory in [LOGS_DIR, DOWNLOADS_DIR, DATA_DIR, TEMP_DOWNLOAD_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'scraper.log')),
        logging.StreamHandler()
    ]
)

class ETendersScraper:
    def __init__(self):
        print("Initializing scraper...")
        self.base_dir = BASE_DIR
        print(f"Base dir: {self.base_dir}")
        self.temp_download_dir = TEMP_DOWNLOAD_DIR
        self.final_download_dir = DOWNLOADS_DIR
        self.data_dir = DATA_DIR
        
        # Clean temp directory on startup
        self.clean_temp_dir()

        # Chrome Options
        chrome_options = Options()
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        chrome_options.add_experimental_option('prefs', {
            'download.default_directory': self.temp_download_dir,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing.enabled': True,
            'plugins.always_open_pdf_externally': True
        })

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)
        
        # Strict Keywords
        self.keywords = {
            'CONSTRUCTION': [
                'build',
                'building',
                'construction',
                'construct',
                'civil',
                'civil works',
                'maintenance',
                'repair',
                'repairs',
                'renovation',
                'upgrade',
                'upgrading',
                'facility',
                'facilities',
                'infrastructure',
                'road',
                'roads',
                'stormwater',
                'water',
                'sewer',
                'pipeline',
                'plumbing',
                'electrical',
                'painting',
                'roof',
                'roofing',
                'tiling',
                'carpentry',
                'flooring',
                'concrete',
                'brick',
                'paving',
                'contractor'
            ],
            'CLEANING': [
                'clean', 'cleaner', 'hygiene', 'sanitize', 'janitor', 'housekeep', 'waste', 
                'refuse', 'garbage', 'rubbish', 'litter', 'recycle', 'pest', 'fumigate', 
                'window wash', 'pressure wash', 'carpet clean', 'deep clean'
            ],
            'SUPPLY': [
                'supply', 'deliver', 'provide', 'procure', 'purchase', 'material', 'equipment', 
                'tool', 'machinery', 'cement', 'brick', 'pipe', 'cable', 'fitting', 'steel', 
                'timber', 'wood', 'glass'
            ]
        }
        
        self.all_keywords = set()
        for cat_list in self.keywords.values():
            self.all_keywords.update(cat_list)

    def clean_temp_dir(self):
        """Remove all files from temp download directory."""
        for filename in os.listdir(self.temp_download_dir):
            file_path = os.path.join(self.temp_download_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logging.error(f'Failed to delete {file_path}. Reason: {e}')

    def remove_overlays(self):
        """Remove modal backdrops and specific popups."""
        try:
            self.driver.execute_script("""
                document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                document.body.classList.remove('modal-open');
                
                var popup = document.getElementById('educationalPopup');
                if (popup) { popup.remove(); }
            """)
        except Exception as e:
            logging.warning(f"Error removing overlays: {e}")

    def sanitize_filename(self, filename):
        """Sanitize string to be used as filename."""
        # Replace invalid chars with underscore, strip whitespace
        return re.sub(r'[<>:"/\\|?*]', '_', filename).strip()

    def wait_for_download(self, timeout=60):
        """Wait for a file to appear in the temp folder and return its path."""
        end_time = time.time() + timeout
        while time.time() < end_time:
            files = os.listdir(self.temp_download_dir)
            completed_files = [f for f in files if not f.endswith('.crdownload') and not f.endswith('.tmp')]
            
            if completed_files:
                # Return the most recent file
                latest_file = max([os.path.join(self.temp_download_dir, f) for f in completed_files], key=os.path.getmtime)
                # Wait a tiny bit to ensure file handle is released
                time.sleep(1)
                return latest_file
            
            time.sleep(1)
        return None

    def check_relevance(self, text):
        """Check if tender is relevant."""
    
        text_lower = text.lower()

        # convert ALL keywords to lowercase
        keywords = [k.lower() for k in self.all_keywords]

        # broader matching
        return any(keyword in text_lower for keyword in keywords)

    def get_tender_category(self, text):
        """Determine broad category based on keywords (for folder naming/logging)."""
        text_lower = text.lower()
        found_cats = []
        for cat, keywords in self.keywords.items():
            if any(k in text_lower for k in keywords):
                found_cats.append(cat)
        return "_".join(found_cats) if found_cats else "General"

    def process_tenders(self):

        tenders_data = []

        try:
            print("Starting navigation...")
            self.driver.get("https://www.etenders.gov.za/Home/opportunities?id=1")
            logging.info("Navigated to eTenders opportunities page.")
            print("Navigated successfully.")
            time.sleep(5)  # Wait for page load
            
            tenders_data = []
            max_pages = 5
            page_num = 1

            while page_num <= max_pages:
                logging.info(f"Processing page {page_num}...")
                
                # Wait for table rows
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
                current_rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                
                i = 0
                while i < len(current_rows):
                    try:
                        # Re-fetch rows to avoid stale element issues after DOM changes
                        current_rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                        
                        if i >= len(current_rows):
                            break
                        
                        row = current_rows[i]
                        
                        # Extract basic info BEFORE clicking anything
                        cells = row.find_elements(By.TAG_NAME, "td")

                        # DEBUG
                        print(f"FOUND {len(cells)} CELLS")

                        for idx, cell in enumerate(cells):
                            print(f"CELL {idx}: {cell.text}")

                        if len(cells) < 4:
                            continue

                        # safer extraction
                        tender_ref = cells[0].text.strip() if len(cells) > 0 else ""
                        category_text = cells[1].text.strip() if len(cells) > 1 else ""
                        title = cells[2].text.strip() if len(cells) > 2 else ""
                        closing_date = cells[3].text.strip() if len(cells) > 3 else ""

                        full_text = f"{tender_ref} {category_text} {title} {closing_date}"

                        print("FULL TEXT:", full_text)
                        
                        full_text = f"{title} {category_text} {tender_ref}"
                        
                        # STRICT FILTER
                        if not self.check_relevance(full_text):
                            logging.info(f"Skipping irrelevant tender: {tender_ref}")
                            i += 1
                            continue
                            
                        logging.info(f"Processing RELEVANT tender: {tender_ref}")
                        
                        # Determine category for folder structure
                        tender_cat = self.get_tender_category(full_text)
                        
                        # Expand Row
                        expand_btn = row.find_element(By.CSS_SELECTOR, "td.details-control")
                        expand_btn.click()
                        time.sleep(2) # Wait for expansion
                        
                        # Find expanded content
                        try:
                            # Try to find the new row inserted after the current row
                            # It usually shares the same parent or is a sibling
                            # But specifically the one related to THIS row. 
                            # Since we are iterating strictly, the newly opened child row should be immediately following the current row in DOM.
                            expanded_row = row.find_element(By.XPATH, "following-sibling::tr[@class='child']")
                        except:
                            # Fallback: search for any visible child row (assuming only one is open at a time if we close them)
                            # Or just the next sibling
                            try:
                                expanded_row = row.find_element(By.XPATH, "following-sibling::tr")
                            except Exception as e:
                                logging.warning(f"Could not find expanded row for {tender_ref}: {e}")
                                i += 1
                                continue

                        # Find PDF links
                        pdf_links = expanded_row.find_elements(By.CSS_SELECTOR, "a[href$='.pdf'], a[href*='Download'], a[href*='.PDF']")
                        
                        document_paths = []
                        
                        # Create organized folder: downloads/{tender_ref}_{Category}/
                        folder_name = self.sanitize_filename(f"{tender_ref}_{tender_cat}")
                        # Fallback if tender_ref is empty
                        if not tender_ref:
                            folder_name = self.sanitize_filename(f"{title[:20]}_{tender_cat}")
                            
                        tender_download_path = os.path.join(self.final_download_dir, folder_name)
                        
                        if pdf_links:
                            if not os.path.exists(tender_download_path):
                                os.makedirs(tender_download_path)
                                
                            for link in pdf_links:
                                try:
                                    pdf_url = link.get_attribute('href')
                                    if not pdf_url:
                                        continue
                                    
                                    # Skip if not a download link (sometimes they are mailto or other)
                                    if 'mailto:' in pdf_url:
                                        continue

                                    self.clean_temp_dir()
                                    logging.info(f"Downloading: {pdf_url}")
                                    
                                    # Scroll to element to ensure clickability
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                                    time.sleep(1)
                                    link.click()
                                    
                                    downloaded_file = self.wait_for_download(timeout=30)
                                    
                                    if downloaded_file:
                                        filename = os.path.basename(downloaded_file)
                                        final_path = os.path.join(tender_download_path, filename)
                                        
                                        # Handle duplicates
                                        if os.path.exists(final_path):
                                            base, ext = os.path.splitext(filename)
                                            final_path = os.path.join(tender_download_path, f"{base}_{int(time.time())}{ext}")
                                            
                                        shutil.move(downloaded_file, final_path)
                                        document_paths.append(final_path)
                                        logging.info(f"Saved: {final_path}")

                                        # --- AI Engine: Extract, Summarize, Score ---
                                        try:
                                            text = extract_text_from_pdf(final_path)
                                            summary = summarize_text(text)
                                            score = score_tender(text)

                                            print("SUMMARY:", summary)
                                            print("SCORE:", score)

                                            logging.info(f"AI Summary for {filename}: {summary}")
                                            logging.info(f"AI Score for {filename}: {score}")
                                        except Exception as ai_error:
                                            logging.error(f"AI processing failed for {final_path}: {ai_error}")
                                        # -----------------------------------------

                                    else:
                                        logging.error(f"Download timed out for {pdf_url}")
                                        
                                except Exception as e:
                                    logging.error(f"Failed to download link: {e}")
                        
                        # Collapse row to keep DOM clean
                        try:
                            expand_btn.click()
                            time.sleep(1)
                        except:
                            pass
                            
                        # Save Data
                        tenders_data.append({
                            'tender_ref': tender_ref,
                            'title': title,
                            'category': category_text,
                            'closing_date': closing_date,
                            'num_documents': len(document_paths),
                            'downloaded_paths': "; ".join(document_paths)
                        })

                        i += 1
                        
                    except Exception as e:
                        logging.error(f"Error processing row {i}: {e}")
                        i += 1
                        continue
                
                # Pagination
                if page_num >= max_pages:
                    logging.info("Max pages reached.")
                    break
                    
                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, "a.paginate_button.next:not(.disabled)")
                    if next_btn:
                        logging.info("Moving to next page...")
                        # Scroll to bottom to ensure next button is visible and not covered
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1)
                        next_btn.click()
                        time.sleep(15)
                        self.wait.until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "table tbody tr")
                            )
                        )

                        # EXTRA WAIT FOR AJAX DATA
                        time.sleep(10)
                        page_num += 1
                    else:
                        logging.info("No next button or disabled. Finished.")
                        break
                except:
                    logging.info("Pagination end reached.")
                    break

            # Save CSV
            if tenders_data:
                df = pd.DataFrame(tenders_data)
                csv_path = os.path.join(self.data_dir, 'relevant_tenders_summary.csv')
                df.to_csv(csv_path, index=False)
                logging.info(f"Saved summary to {csv_path}")
            else:
                logging.info("No relevant tenders found.")

            
                
        except Exception as e:
            logging.error(f"Fatal error: {e}")
            traceback.print_exc()

        finally:
            print("Quitting driver...")
            self.driver.quit()

        return tenders_data

def scrape_tenders():

    scraper = ETendersScraper()

    return scraper.process_tenders()

    csv_path = os.path.join(DATA_DIR, 'relevant_tenders_summary.csv')

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        return df.to_dict(orient="records")

    return []

if __name__ == "__main__":
    scraper = ETendersScraper()
    scraper.process_tenders()