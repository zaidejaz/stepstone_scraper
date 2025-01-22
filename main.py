import os
import time
import requests
from bs4 import BeautifulSoup
import csv
import logging
import uuid
from datetime import datetime, timedelta
import re
import asyncio
from playwright.async_api import async_playwright

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# API Keys (ensure these are loaded from .env file)
SCRAPING_BEE_API_KEY = ""
BROWSERCAT_API_KEY = ""

BASE_URL = "https://www.stepstone.de"
START_URL = "https://www.stepstone.de/jobs/in-deutschland?radius=5&action=facet_selected%3bage%3bage_1&ag=age_1"

def fetch_with_retry(url, params, retries=3, delay=2):
    """Fetch a URL with retry mechanism."""
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if response.status_code == 500:
                attempt += 1
                logging.warning(f"500 Server Error on attempt {attempt}/{retries}. Retrying after {delay} seconds...")
                if attempt < retries:
                    time.sleep(delay)
            else:
                raise e  # Raise non-500 errors
        except Exception as e:
            logging.error(f"Error occurred: {e}")
            raise e
    logging.error(f"Failed to fetch {url} after {retries} attempts.")
    return None  # Return None if all retries fail

async def get_job_links(browser, url):
    job_links = []
    page = 1
    total_pages = None  # Variable to store total number of pages
    current_url = START_URL + f"&page={page}"
    
    while True:
        try:
            logging.info(f"Fetching page {page}")
            # Use ScrapingBee API for requests with retry
            response = fetch_with_retry(
                'https://app.scrapingbee.com/api/v1/',
                params={
                    'api_key': SCRAPING_BEE_API_KEY,
                    'url': current_url,
                    'render_js': 'false'
                }
            )
            
            if not response:
                logging.warning(f"Skipping page {page} due to repeated failures.")
                break
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract job links
            links = soup.find_all("a", class_="res-1foik6i")
            new_links = [BASE_URL + link["href"] for link in links if "href" in link.attrs]
            job_links.extend(new_links)
            logging.info(f"Found {len(new_links)} job links on page {page}")
            
            # Extract total pages on the first iteration
            if total_pages is None:
                pagination_nav = soup.find('nav', {'aria-label': 'pagination'})
                if pagination_nav:
                    last_page_link = pagination_nav.find_all('li')[-2]
                    if last_page_link:
                        total_pages = int(last_page_link.text)
                        logging.info(f"Total pages: {total_pages}")
            
            # Break loop if no more pages or total pages reached
            if total_pages and page >= total_pages:
                logging.info(f"Reached the last page: {total_pages}")
                break

            logging.info(f"Found {len(job_links)} jobs to scrape")
            
            # Scrape each job listing
            for index, job_url in enumerate(job_links, 1):
                logging.info(f"Processing job {index} of {len(job_links)}")
                await scrape_job_listing(browser, job_url)
                # Add a small delay between requests
                await asyncio.sleep(1)
            
            # Prepare URL for the next page
            page += 1
            current_url = START_URL + f"&page={page}"

        except Exception as e:
            logging.error(f"Error occurred while fetching job links: {e}")
            break
            
    logging.info(f"Total job links found: {len(job_links)}")
    return job_links

def get_company_contact_details(company_website):
    """Get company contact details using ScrapingBee with retry."""
    try:
        contact_url = company_website.replace("/jobs.html", "/kontakte.html#menu")
        logging.info(f"Fetching company contact details from: {contact_url}")
        
        response = fetch_with_retry(
            'https://app.scrapingbee.com/api/v1/',
            params={
                'api_key': SCRAPING_BEE_API_KEY,
                'url': contact_url,
                'render_js': 'false'
            }
        )
        
        if not response:
            logging.warning(f"Skipping contact details for {company_website} due to repeated failures.")
            return "N/A", "N/A", "N/A", "N/A", "N/A"

        soup = BeautifulSoup(response.text, "html.parser")
        ul = soup.find_all("ul")[0] if soup.find("ul") else None
        website = ul.find("a")["href"] if ul and ul.find("a") else "N/A"
        contact_name_tag = soup.find('span', class_="at-contact-name")
        contact_name = contact_name_tag.text.strip() if contact_name_tag else "N/A"
        contact_position_tag = soup.find('span', class_="at-contact-position")
        contact_position = contact_position_tag.text.strip() if contact_position_tag else "N/A"
        contact_phone_tag = soup.find('a', class_="at-contact-phone")
        contact_phone = contact_phone_tag.text.strip() if contact_phone_tag else "N/A"
        contact_email_tag = soup.find('a', class_="at-contact-email")
        contact_email = contact_email_tag['href'].replace("mailto:", "") if contact_email_tag else "N/A"

        return website, contact_name, contact_position, contact_phone, contact_email
    except Exception as e:
        logging.warning(f"Failed to fetch contact details: {e}")
        return "N/A", "N/A", "N/A", "N/A", "N/A"

async def get_additional_contact_details(page):
    """Get additional contact details using Playwright"""
    logging.info("Fetching additional contact information...")
    try:
        # Handle cookie acceptance if present
        try:
            accept_button = page.locator("#ccmgt_explicit_accept")
            await accept_button.click()
            await page.wait_for_timeout(1000)
        except Exception:
            logging.info("No cookie acceptance button found or already accepted.")

        # Handle login modal if present
        try:
            login_modal = page.locator(".lpca-login-registration-components-rgcrz1")
            if await login_modal.is_visible():
                await page.evaluate('(element) => element.style.display = "none"', await login_modal.element_handle())
        except Exception:
            logging.info("No login modal found or already hidden.")

        # Click more info button
        try:
            more_info = page.locator("[data-at='rebranded-version'] [role='button']")
            await more_info.click()
            logging.info("Clicked additional info button")
            
            additional_info = page.locator(".at-section-text-additionalInformation")
            content = await additional_info.inner_html()
            
            soup = BeautifulSoup(content, "html.parser")
            text_content = soup.get_text(separator="\n").strip()

            # Extract contact information
            phone_tag = soup.find('a', href=re.compile(r"tel:"))
            email_tag = soup.find('a', href=re.compile(r"mailto:"))
            website_tag = soup.find('a', href=re.compile(r"https?://"))

            phone = phone_tag.get_text(strip=True) if phone_tag else None
            email = email_tag.get_text(strip=True) if email_tag else None
            website = website_tag.get_text(strip=True) if website_tag else None

            # Fallback to regex patterns if needed
            if not email:
                email_match = re.search(r"[\w\.-]+@[\w\.-]+", text_content)
                email = email_match.group(0) if email_match else "N/A"

            if not website:
                website_match = re.search(r"https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text_content)
                website = website_match.group(0) if website_match else "N/A"

            return phone or "N/A", email, website
        except Exception as e:
            logging.warning(f"Failed to get additional contact details: {e}")
            return "N/A", "N/A", "N/A"
    except Exception as e:
        logging.error(f"Error in get_additional_contact_details: {e}")
        return "N/A", "N/A", "N/A"

async def scrape_job_listing(browser, url):
    """Scrape individual job listing using Playwright"""
    logging.info(f"Starting to scrape job listing from URL: {url}")

    try:
        page = await browser.new_page()
        await page.goto(url)
        logging.info("Page loaded successfully")
        
        # Extract basic job details
        job_title = await page.inner_text("h1")
        employment_type = await page.inner_text(".at-listing__list-icons_work-type")
        location = await page.inner_text(".at-listing__list-icons_location")
        
        company_element = await page.locator(".at-listing__list-icons_company-name").element_handle()
        company_name = await company_element.inner_text()
        company_link = await company_element.query_selector('a')
        company_page_href = await company_link.get_attribute('href') if company_link else None

        # Get company contact details
        if company_page_href:
            website, contact_name, contact_position, contact_phone, contact_email = get_company_contact_details(company_page_href)
            
            # Try to get additional contact details
            add_phone, add_email, add_website = await get_additional_contact_details(page)
            
            # Use additional details if main ones are not available
            contact_phone = contact_phone if contact_phone != "N/A" else add_phone
            contact_email = contact_email if contact_email != "N/A" else add_email
            website = website if website != "N/A" else add_website
        else:
            website, contact_name, contact_position, contact_phone, contact_email = "N/A", "N/A", "N/A", "N/A", "N/A"
        
        # Split contact name
        contact_first_name, contact_last_name = "N/A", "N/A"
        if contact_name != "N/A":
            name_parts = contact_name.split(" ")
            contact_first_name = name_parts[0]
            contact_last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "N/A"

        # Get timestamp
        job_listing_timestamp = await page.inner_text(".at-listing__list-icons_date")
        # Handle German format "Erschienen: vor X Stunden/Tagen"
        timestamp_match = re.search(r'vor (\d+) (Stunden|Tage|Tag)', job_listing_timestamp)
        
        if timestamp_match:
            amount = int(timestamp_match.group(1))
            unit = timestamp_match.group(2)
            
            if unit == 'Stunden':
                job_listing_timestamp = (datetime.now() - timedelta(hours=amount)).isoformat()
            elif unit in ['Tage', 'Tag']:
                job_listing_timestamp = (datetime.now() - timedelta(days=amount)).isoformat()
            else:
                job_listing_timestamp = datetime.now().isoformat()
        else:
            job_listing_timestamp = datetime.now().isoformat()

        # Save to CSV
        row = [
            job_title.strip(), employment_type.strip(), location.strip(), 
            company_name.strip(), website, contact_name, contact_first_name, 
            contact_last_name, contact_position, contact_phone, contact_email, 
            "Stepstone", job_listing_timestamp, datetime.now().isoformat(), 
            str(uuid.uuid4())
        ]
        write_to_csv(row)
        logging.info("Successfully saved job listing to CSV")

        await page.close()

    except Exception as e:
        logging.error(f"Failed to scrape job listing from {url}: {e}")
        try:
            await page.close()
        except:
            pass

def write_to_csv(data):
    """Write job data to CSV file"""
    try:
        file_exists = os.path.isfile('jobs.csv')
        mode = 'a' if file_exists else 'w'
        
        with open('jobs.csv', mode, newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow([
                    "Job Title", "Employment Type", "Location", "Company Name",
                    "Company Website", "Contact Full Name", "Contact First Name",
                    "Contact Last Name", "Contact Position", "Contact Phone",
                    "Contact Email", "Platform", "Job Listing Timestamp",
                    "Scraping Timestamp", "Job ID"
                ])
            writer.writerow(data)
            logging.info("Successfully wrote data to CSV")
    except Exception as e:
        logging.error(f"Error writing to CSV: {e}")

async def main():
    logging.info("Starting the scraping process")
    
    try:
        # Connect to BrowserCat with Playwright
        async with async_playwright() as pw:
            browser = await pw.chromium.connect(
                "wss://api.browsercat.com/connect",
                headers={'Api-Key': BROWSERCAT_API_KEY}
            )
            logging.info("Successfully connected to BrowserCat")
            
            # Get job links using ScrapingBee
            await get_job_links(browser, START_URL)
            
            await browser.close()
            logging.info("Scraping process completed")
            
    except Exception as e:
        logging.error(f"Main process error: {e}")

if __name__ == "__main__":
    asyncio.run(main())