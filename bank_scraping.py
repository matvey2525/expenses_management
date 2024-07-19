from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import glob


def get_latest_file(folder_path, extension):
    # Get a list of files with the given extension in the folder
    files = glob.glob(os.path.join(folder_path, f'*.{extension}'))

    # Check if the folder is empty or contains no files with the given extension
    if not files:
        return None

    # Get the latest file based on the modification time
    latest_file = max(files, key=os.path.getmtime)

    return latest_file


def osh_scraping(username, password):
    download_directory = "/Users/matveybernshtein/PycharmProjects/Flask Site/Data Files/"

    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Ensure GUI is off
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Configure download directory
    prefs = {
        "download.default_directory": download_directory,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Initialize the Chrome driver using webdriver-manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Open the website
        driver.get(
            "https://hb2.bankleumi.co.il/staticcontent/gate-keeper/he/?trackingCode=520c65da-b5b2-4b76-782c-0240245b2c5b&sysNum=23&langNum=1#/ts/BusinessAccountTrx")

        time.sleep(3)

        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "user"))
        )
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "password"))
        )

        username_field.send_keys(username)
        password_field.send_keys(password)

        time.sleep(2)
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[text()='כניסה לחשבון']"))
        )
        login_button.click()

        time.sleep(2)

        '''Export of Credit cards data'''
        # driver.get("https://hb2.bankleumi.co.il/ebanking/SO/SPA.aspx#/ts/CardsWorld")
        #
        # time.sleep(3)
        # export_all_cards_button = WebDriverWait(driver, 10).until(
        #     EC.element_to_be_clickable((By.XPATH, "//*[text()='ייצוא נתוני כל הכרטיסים']"))
        # )
        # export_all_cards_button.click()
        #
        # time.sleep(2)
        # export_button = WebDriverWait(driver, 10).until(
        #     EC.element_to_be_clickable((By.XPATH, "//*[text()='ייצוא']"))
        # )
        # export_button.click()
        #
        # time.sleep(2)

        '''Export of OSH data'''
        driver.get("https://hb2.bankleumi.co.il/ebanking/SO/SPA.aspx#/ts/BusinessAccountTrx")

        time.sleep(3)
        export_to_excel_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.tw-text-primary.excl2[title='יצוא לאקסל']"))
        )
        export_to_excel_button.click()

        time.sleep(1)
        export_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[text()='המשך']"))
        )
        export_button.click()

        time.sleep(2)

        page_source = driver.page_source

        print("OSH Extracted Successfully!")

        # Close the driver
        driver.quit()

        return get_latest_file(download_directory, 'xls')

    except Exception as e:
        print(f"An error occurred during the login process: {e}")


if __name__ == '__main__':
    print(osh_scraping())
