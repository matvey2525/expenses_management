import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from bank_scraping import osh_scraping, get_latest_file
from max_scraping import credit_card_scraping
import numpy as np
import tkinter as tk
import sys
from LocalAuthentication import LAContext, LAPolicyDeviceOwnerAuthenticationWithBiometrics
import threading


def authenticate_with_touch_id(timeout=10):
    context = LAContext.new()
    reason = "Authentication required"

    can_evaluate = context.canEvaluatePolicy_error_(LAPolicyDeviceOwnerAuthenticationWithBiometrics, None)
    if not can_evaluate:
        print("Touch ID is not available on this device")
        return False

    auth_event = threading.Event()
    auth_result = [None]

    def callback(success, error):
        if success:
            auth_result[0] = True
        else:
            print(f"Touch ID authentication failed: {error}")
            auth_result[0] = False
        auth_event.set()

    context.evaluatePolicy_localizedReason_reply_(LAPolicyDeviceOwnerAuthenticationWithBiometrics, reason, callback)

    # Wait for the authentication to complete or timeout
    auth_event.wait(timeout)

    if auth_result[0] is None:
        print("Touch ID authentication timed out")
        return False

    return auth_result[0]


def get_credentials():
    def on_submit():
        nonlocal code
        code = entry_code.get()
        root.quit()
        root.destroy()

    # Initialize variables to store credentials
    code = None

    # Create the main window
    root = tk.Tk()
    root.title("Login")

    # Get the screen width and height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Set the desired width and height for the window
    window_width = 300
    window_height = 150

    # Calculate the position for centering the window
    position_x = (screen_width // 2) - (window_width // 2)
    position_y = (screen_height // 2) - (window_height // 2)

    # Set the geometry of the window
    root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

    # Create a frame for the login form
    frame = tk.Frame(root)
    frame.pack(pady=20, padx=20)

    # Code label and entry
    label_code = tk.Label(frame, text="Code")
    label_code.grid(row=0, column=0, pady=5)

    entry_code = tk.Entry(frame)
    entry_code.grid(row=0, column=1, pady=5)

    # Submit button
    button_submit = tk.Button(frame, text="Submit", command=on_submit)
    button_submit.grid(row=2, columnspan=2, pady=10)

    # Start the Tkinter event loop
    root.mainloop()

    return code

def extract_bank_data(file_path):
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all tables
    tables = soup.find_all('table')

    # Parse a tables into DataFrame
    df = pd.read_html(str(soup))[2]

    # Exclude the first row and set the second row as the column names
    df.columns = df.iloc[1]
    df = df[2:]

    # Reset the index
    df.reset_index(drop=True, inplace=True)
    return df


def extract_table_from_max_excel(file_path, start_row=4):
    xls = pd.ExcelFile(file_path)
    sheet_names = xls.sheet_names
    df_list = []

    for sheet_name in sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=start_row - 1)
        empty_row_index = df[df.isnull().all(axis=1)].index[0]
        table_df = df.iloc[:empty_row_index]

        # if sheet_name == 'עסקאות שאושרו וטרם נקלטו':
        for index, row in df.iterrows():
            if pd.isna(row['סכום חיוב']):
                if pd.notna(row['סכום עסקה מקורי']):
                    if row['מטבע עסקה מקורי'] == '₪':
                        df.at[index, 'סכום חיוב'] = row['סכום עסקה מקורי']
                    elif row['מטבע עסקה מקורי'] == '$':
                        df.at[index, 'סכום חיוב'] = row['סכום עסקה מקורי'] * 3.5
                    else:
                        pass

        df_list.append(table_df)

    return pd.concat(df_list, ignore_index=True)


def categorize_description(row):
    catalog = {
        'סופר': [
            'שופרסל',
            'יוחננוף',
            'קשת טעמים',
            'פירות וירקות',
            'CARREFOUR',
            'מזרח ומערב',
            'פיצוחי',
            'הנדלר רון',
            'עץ השדה',
            'רלפי חקלאות',
            'נועם החקלאי',
            'פירות',
            'מינימרקט',
            'דליקס',
            'שוק',
            'אושר עד',
            'רמי לוי',
            'עולם הממתקים',
            'דוכן גן שמואל',
            'אחים מרסל',
            'רמי אגיבייב'
        ],
        'דלק': [
            'פז אפליקציית יילו',
            'דלק',
            'סונול',
            'ספרינט מוטורס',
        ]
    }

    description = row['Description']
    max_category = row['max category']
    amount = row['Amount']

    if pd.isnull(description):
        return 'הוצאות משתנות'

    if max_category == 'מזון וצריכה':
        for term in catalog.get('סופר', []):
            if term in description:
                return 'סופר'
        return 'אוכל בחוץ'

    if not pd.isnull(max_category) and 'מסעדות' in max_category:
        return 'אוכל בחוץ'

    if 'אלקטרה' in description:
        return 'הוצאות קבועות-חשמל'

    if 'מ.תחבורה רב- פס' in description:
        return 'הוצאות קבועות-תחבורה'

    if 'שרותי בריאות כללית' in description:
        return 'הוצאות קבועות-ביטוח כללית'

    if 'בלינק' in description:
        return 'הוצאות קבועות-ועד בית'

    if 'סלקום' in description:
        return 'הוצאות קבועות-אינטרנט'

    if 'וויקום' in description:
        return 'הוצאות קבועות-חבילות טלפון'

    if 'מנורה' in description:
        return 'הוצאות קבועות-ביטוח שיניים'

    if 'ביטוח דירה' in description:
        return 'הוצאות קבועות-ביטוח דירה'

    if 'איילון בריאות' in description:
        return 'הוצאות קבועות-ביטוח בריאות'

    if 'ביטוח חיים' in description:
        return 'הוצאות קבועות-ביטוח חיים'

    if 'לאומי למשכנת' in description:
        return 'הוצאות קבועות-משכנתא'

    if 'מועצה מקומית אור עקיבא' in description:
        return 'הוצאות קבועות-ארנונה ומים'

    if 'בינה טבעית' in description:
        return 'הכנסות-הכנסות קבועות'

    if 'רשות לנירות' in description:
        return 'הכנסות-הכנסות קבועות'

    if pd.isnull(max_category) and amount > 0:
        return 'הכנסות-הכנסות משתנות'

    for term in catalog.get('דלק', []):
        if term in description:
            return 'דלק'

    return 'הוצאות משתנות'

def week_of_month(dt, latest_month, latest_year):
    # Check if the month or year does not match the latest month and year
    if dt.month != latest_month or dt.year != latest_year:
        return 1
    # Find the first day of the month
    first_day = dt.replace(day=1)
    # Calculate the week number
    dom = dt.day
    adjusted_dom = dom + (first_day.weekday() - 6) % 7
    return int(np.ceil(adjusted_dom / 7.0))

def prepare_excel_file():

    code = get_credentials()
    if not code:
        sys.exit()
    bank_username = code.split(' ')[0]
    bank_password = code.split(' ')[1]
    max_username = code.split(' ')[2]
    max_password = code.split(' ')[3]

    # if authenticate_with_touch_id():
    #     print('you pass')
    # sys.exit()



    # file_path_osh = 'Data Files/תנועות בחשבון 20_6_2024.xls'
    # file_path_max_credit_card = 'Data Files/transaction-details_export_1718900627538.xlsx'
    file_path_osh = osh_scraping(bank_username, bank_password)
    file_path_max_credit_card = credit_card_scraping(max_username, max_password)

    df_osh = extract_bank_data(file_path_osh)
    df_credit_cards = extract_table_from_max_excel(file_path_max_credit_card)

    df_credit_cards.rename(
        columns={'תאריך עסקה': 'Date', 'שם בית העסק': 'Description', 'סכום חיוב': 'Amount', 'קטגוריה': 'max category'},
        inplace=True)
    df_credit_cards['Description'] = df_credit_cards['Description'] + ' כרטיס ' + df_credit_cards[
        '4 ספרות אחרונות של כרטיס האשראי'].astype(int).astype(str)
    df_credit_cards = df_credit_cards[['Date', 'Description', 'Amount', 'max category']]
    df_credit_cards['Date'] = pd.to_datetime(df_credit_cards['Date'], format='%d-%m-%Y')

    df_osh['בחובה'] = pd.to_numeric(df_osh['בחובה'])
    df_osh['בזכות'] = pd.to_numeric(df_osh['בזכות'])
    df_osh['Amount'] = df_osh.apply(lambda row: -row['בחובה'] if row['בחובה'] != 0 else row['בזכות'], axis=1)
    df_osh.rename(columns={'תאריך': 'Date', 'תיאור': 'Description'}, inplace=True)
    df_osh = df_osh[['Date', 'Description', 'Amount']]
    df_osh = df_osh[~df_osh['Description'].str.contains('לאומי ויזה', case=False)]
    df_osh['Date'] = pd.to_datetime(df_osh['Date'], format='%d/%m/%y')

    # Extract the latest month and year
    latest_date = df_osh['Date'].max()
    latest_month = latest_date.month
    # latest_month = 1
    latest_year = latest_date.year

    # Filter for the latest month and year
    df_osh_filtered = df_osh[(df_osh['Date'].dt.month == latest_month) & (df_osh['Date'].dt.year == latest_year)]

    # Get last 5 days of the previous month
    previous_month = latest_month - 1 if latest_month > 1 else 12
    previous_year = latest_year if latest_month > 1 else latest_year - 1
    last_5_days_previous_month = df_osh[(df_osh['Date'].dt.year == previous_year) &
                                        (df_osh['Date'].dt.month == previous_month) &
                                        (df_osh['Date'].dt.day > (df_osh['Date'].dt.days_in_month - 5)) &
                                        (df_osh['Description'].str.contains('קסלמן|רשות לנירות|בינה טבעית'))]

    # Exclude rows from the filtered month from day 25 until the end with specific terms
    excluded_days_filtered_month = df_osh_filtered[(df_osh_filtered['Date'].dt.day >= 25) &
                                                   (df_osh_filtered['Description'].str.contains(
                                                       'קסלמן|רשות לנירות|בינה טבעית'))]
    df_osh_filtered = df_osh_filtered[~df_osh_filtered.isin(excluded_days_filtered_month).all(axis=1)]

    # Combine the filtered DataFrame
    df_osh = pd.concat([df_osh_filtered, last_5_days_previous_month]).sort_values(by='Date').reset_index(
        drop=True)

    df = pd.concat([df_credit_cards, df_osh])

    # Sort the DataFrame by the Date column
    df = df.sort_values(by='Date', ascending=False)
    df['Amount'] = round(df['Amount'], 1)

    # Apply the function to create a new Category column
    df['Category'] = df.apply(lambda row: categorize_description(row), axis=1)

    split_columns = df['Category'].str.split('-', expand=True)

    # Assign the first part to 'Category' and the second part to 'SubCategory'
    df['Category'] = split_columns[0]
    df['SubCategory'] = split_columns[1]

    df['Amount'] = df.apply(lambda row: abs(row['Amount']) if pd.isnull(row['max category']) else row['Amount'], axis=1)
    df = df.drop(columns=['max category'])
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Week Number'] = df['Date'].apply(lambda x: week_of_month(x, latest_month, latest_year))
    # df['Week Number'] = df['Date'].apply(
    #     lambda x: (x.day - 1) // 7 + 1 if (x.month == latest_month and x.year == latest_year) else 1
    # )
    # Create a dictionary to map weekday numbers to Hebrew names with the word 'יום'
    hebrew_weekdays = {
        0: 'יום שני',
        1: 'יום שלישי',
        2: 'יום רביעי',
        3: 'יום חמישי',
        4: 'יום שישי',
        5: 'יום שבת',
        6: 'יום ראשון'
    }

    # Add a new column with the weekday names in Hebrew
    df['Hebrew_Weekday'] = df['Date'].dt.weekday.map(hebrew_weekdays)
    df['Date'] = df['Date'].dt.date

    # Make values in 'Amount (₪)' positive where 'Category' is הוצאות קבועות
    df.loc[df['Category'] == 'הוצאות קבועות', 'Amount'] = df.loc[
        df['Category'] == 'הוצאות קבועות', 'Amount'].abs()

    # df = df.fillna('NO DESCRIPTION')

    timestamp = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
    df.to_excel(f'United_Data_Files/United_Data_{timestamp}.xlsx', index=False)

    # return get_latest_file('United_Data_Files/', 'xlsx')
    return f'United_Data_Files/United_Data_{timestamp}.xlsx'


if __name__ == '__main__':
    prepare_excel_file()
