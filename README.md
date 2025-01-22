# Job Scraping Script

This script is designed to scrape job listings from **Stepstone** and collect various details like job title, company information, contact details (email, phone), and more. The data is saved into a CSV file.

## Prerequisites

### Software Requirements:
- **Python 3.7+**
- **Poetry** (for managing dependencies)

### External Dependencies:
- **requests**: For making HTTP requests.
- **BeautifulSoup**: For parsing and extracting data from HTML.
- **Selenium**: For automating web browser interactions.
- **WebDriver Manager**: To manage and install the required web drivers for Selenium.

### System Requirements:
- **Google Chrome** (for Selenium to interact with)
- **Chromedriver**: The Chrome browser needs to be paired with an appropriate driver (managed automatically by `webdriver_manager`).

## Installation

### Step 1: Install Poetry
If you don't have Poetry installed, you can install it by following the instructions on the [Poetry website](https://python-poetry.org/docs/#installation).

For example, you can install it using pip:

```bash
pip install poetry
```

### Step 2: Install Dependencies
Run the following command to install the required dependencies via Poetry:

```bash
poetry install
```

Poetry will create a virtual environment and install all the dependencies specified in the `pyproject.toml` file.

If you install poetry using pip you might need to run this command

```bash
python -m poetry install
```

### Step 3: Activate the Virtual Environment
Activate the Poetry-managed virtual environment:

```bash
poetry shell
```

This ensures that you’re using the correct environment with the required dependencies.

If you install poetry using pip you might need to run this command

```bash
python -m poetry shell
```

## Usage

### Run the Script
To run the script, use the following command:

```bash
python main.py
```

### Step 3: Review Output
The script will save job listings into a CSV file called `jobs.csv`. If this file doesn't exist, it will be created. The CSV file contains the following columns:

- **Job Title**
- **Employment Type**
- **Location**
- **Company Name**
- **Company Website**
- **Contact Name**
- **Contact Position**
- **Contact Phone**
- **Contact Email**
- **Platform** (Stepstone)
- **Timestamp** (Job scrape timestamp)
- **Job ID** (Generated UUID)

### Step 4: Scraping Multiple Pages
The script scrapes the job listings from the URL set in the `START_URL` variable. Modify this URL if you want to scrape job listings from different pages or regions.

## Customization

- **User-Agent**: The script sends a custom `User-Agent` header with each request to mimic a real browser.
- **Error Handling and Retries**: The script includes basic error handling and logging to ensure reliable scraping.
- **Selenium WebDriver**: The script uses **Selenium** in headless mode to interact with the job listing pages that require JavaScript rendering. Ensure **Google Chrome** and **ChromeDriver** are available on your system.

## Troubleshooting

- **Missing Dependencies**: Ensure all required dependencies are installed by running `poetry install` again.
- **Chromedriver Issues**: The script uses **WebDriverManager** to install and manage the correct version of **Chromedriver**. If there’s an issue, make sure that your Chrome version is compatible with the WebDriver version being installed.
- **Job Listing Extraction Failures**: If job listings are not extracted as expected, make sure the structure of the website has not changed. You may need to update the CSS selectors used in the script to reflect any changes on the Stepstone website.
