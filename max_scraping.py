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


def credit_card_scraping(username, password):
    download_directory = "/Users/matveybernshtein/PycharmProjects/Flask Site/Data Files/"

    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
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

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(
            "https://www.max.co.il/transaction-details/personal")

        # password_tab = WebDriverWait(driver, 10).until(
        #     EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'כניסה עם סיסמה')]"))
        # )
        password_tab = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "login-password-link"))
        )
        password_tab.click()

        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "user-name"))
        )
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "password"))
        )

        username_field.send_keys(username)
        password_field.send_keys(password)

        # Find and click the login button
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'לכניסה לאזור האישי')]"))
        )
        login_button.click()

        expenses_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'ייצא לאקסל')]"))
        )
        expenses_button.click()
        time.sleep(2)

        print("Credit Card Data Extracted Successfully!")

        # Close the driver
        driver.quit()

        return get_latest_file(download_directory, 'xlsx')

    except Exception as e:
        print(f"An error occurred during the login process: {e}")


if __name__ == '__main__':
    print(credit_card_scraping())
