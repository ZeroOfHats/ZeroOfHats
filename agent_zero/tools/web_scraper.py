# agent_zero/tools/web_scraper.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
# webdriver_manager can be useful for local dev but avoided in Docker if chromedriver is in PATH
# from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
from typing import Optional # Added for type hinting

# Path to chromedriver if not in system PATH (Docker should install it to a common location)
# If chromedriver is installed via apt and is in /usr/bin/chromedriver or /usr/local/bin/chromedriver,
# Selenium should find it automatically.
CHROMEDRIVER_PATH = None # Or specify path like '/usr/bin/chromedriver' if known and fixed

def get_headless_driver() -> webdriver.Chrome:
    """Initializes and returns a headless Chrome WebDriver instance."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")  # Important for running as root in Docker
    chrome_options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
    chrome_options.add_argument("--disable-gpu") # Usually recommended for headless, even if host has GPU
    chrome_options.add_argument("--window-size=1920x1080") # Can help with some page layouts
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")


    try:
        if CHROMEDRIVER_PATH:
            service = ChromeService(executable_path=CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            # Assumes chromedriver is in PATH
            driver = webdriver.Chrome(options=chrome_options)
        print("Headless Chrome WebDriver initialized successfully.")
        return driver
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        # Attempt with webdriver_manager as a local dev fallback (won't work in restricted Docker build)
        # try:
        #     print("Attempting WebDriver initialization with webdriver_manager...")
        #     driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        #     print("WebDriver initialized with webdriver_manager successfully.")
        #     return driver
        # except Exception as e_manager:
        #     print(f"Error initializing WebDriver with webdriver_manager: {e_manager}")
        raise  # Re-raise the original exception if all attempts fail


def scrape_url_content(driver: webdriver.Chrome, url: str, load_wait_time: int = 3) -> Optional[str]:
    """Fetches a URL and returns its page source. Waits for dynamic content."""
    try:
        print(f"Attempting to scrape URL: {url}")
        driver.get(url)
        # Wait for JavaScript to load, adjust time as needed
        time.sleep(load_wait_time)
        page_source = driver.page_source
        print(f"Successfully fetched content from {url} (length: {len(page_source)})")
        return page_source
    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def extract_main_text(html_content: str) -> str:
    """
    Extracts the main text content from HTML using BeautifulSoup.
    This is a basic implementation and might need refinement for complex pages.
    """
    if not html_content:
        return ""

    print("Parsing HTML content with BeautifulSoup...")
    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove script and style elements
    for script_or_style in soup(["script", "style", "header", "footer", "nav", "aside", "form"]):
        script_or_style.decompose()

    # Try to find common main content containers
    # This order can be important. 'article' is often most specific.
    main_content_tags = ['article', 'main', '[role="main"]'] # CSS selector for role
    text_parts = []

    for tag_selector in main_content_tags:
        if '[role="main"]' == tag_selector: # BeautifulSoup needs explicit selector for attribute
             main_elements = soup.select(tag_selector)
        else:
            main_elements = soup.find_all(tag_selector)

        if main_elements:
            for element in main_elements:
                # Get text, strip leading/trailing whitespace from each line, then join lines.
                lines = (line.strip() for line in element.get_text(separator='\n').splitlines())
                text_parts.extend(line for line in lines if line) # Collect non-empty lines
            if text_parts: break # Found content in one of the main tags

    if not text_parts:
        # Fallback: get all text from the body if specific tags didn't yield much
        print("No specific main content tags found or they were empty. Falling back to body text.")
        body = soup.find('body')
        if body:
            lines = (line.strip() for line in body.get_text(separator='\n').splitlines())
            text_parts.extend(line for line in lines if line)
        else: # If no body tag, just get all text (very unlikely for valid HTML)
             lines = (line.strip() for line in soup.get_text(separator='\n').splitlines())
             text_parts.extend(line for line in lines if line)


    extracted_text = "\n".join(text_parts)
    print(f"Extracted text length: {len(extracted_text)}")
    return extracted_text

def get_text_from_url(url: str, load_wait_time: int = 3) -> Optional[str]:
    """High-level function to get cleaned text content from a URL."""
    driver = None
    try:
        driver = get_headless_driver()
        html_source = scrape_url_content(driver, url, load_wait_time)
        if html_source:
            text_content = extract_main_text(html_source)
            return text_content
        return None
    except Exception as e:
        print(f"Overall error in get_text_from_url for {url}: {e}")
        return None
    finally:
        if driver:
            print("Closing WebDriver.")
            driver.quit()

if __name__ == '__main__':
    # Example Usage (requires internet connection for the test URL)
    # Ensure chromedriver is in your PATH or CHROMEDRIVER_PATH is set if running locally.
    # In Docker, this should work if Dockerfile setup was correct.

    # test_url = "https://www.artificialintelligence-news.com/2024/03/08/google-introduces-genie-ai-can-generate-video-games-text-prompts/"
    # print(f"Attempting to scrape and extract text from: {test_url}")

    # extracted_text = get_text_from_url(test_url)

    # if extracted_text:
    #     print("\n--- Extracted Text (first 500 chars) ---")
    #     print(extracted_text[:500] + "...")
    #     print("\n--- End of Extracted Text ---")
    # else:
    #     print("Failed to extract text.")

    # Test with a simpler page if the above is too complex or blocked
    # test_url_simple = "http://info.cern.ch/hypertext/WWW/TheProject.html" # Very old, simple HTML
    # print(f"\nAttempting to scrape and extract text from simple page: {test_url_simple}")
    # extracted_text_simple = get_text_from_url(test_url_simple)
    # if extracted_text_simple:
    #     print("\n--- Extracted Text (simple page) ---")
    #     print(extracted_text_simple)
    #     print("\n--- End of Extracted Text ---")
    # else:
    #     print("Failed to extract text from simple page.")
    pass
