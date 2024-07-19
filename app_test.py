from flask import Flask, render_template, redirect, url_for
import pandas as pd
import calendar
import math
import webbrowser
import time
import threading
from data_preprocess import prepare_excel_file


# Create a Flask app
app = Flask(__name__)


# Global variables
files_list = [
    '/Users/matveybernshtein/PycharmProjects/Flask Site/test files/United_Data_01.xlsx',
    '/Users/matveybernshtein/PycharmProjects/Flask Site/test files/United_Data_02.xlsx',
    '/Users/matveybernshtein/PycharmProjects/Flask Site/test files/United_Data_03.xlsx'
    ]
current_file_index = 0

def open_browser():
    time.sleep(1)
    webbrowser.open('http://127.0.0.1:5000')


# Function to read Excel data
def read_excel_data(file_path):
    df = pd.read_excel(file_path)
    return df


def format(number):
    if number % 1 == 0:
        return "{:,.0f}".format(round(number, 1))
    return "{:,.1f}".format(number)


# File paths
goals_file_path = '/Users/matveybernshtein/PycharmProjects/Flask Site/test files/Goals test.xlsx'


def get_month_name_hebrew(month_number):
    months = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]
    return months[month_number - 1]


@app.route('/')
def display_expenses():
    global current_file_index
    actuals_file_path = files_list[current_file_index]
    actuals_df = read_excel_data(actuals_file_path)
    goals_df = read_excel_data(goals_file_path)

    categories = goals_df['Category'].tolist()
    recommended_values = dict(zip(goals_df['Category'], goals_df['Goal Amount (₪)']))


    # Parse dates with the correct format
    actuals_df['Date'] = pd.to_datetime(actuals_df['Date'], dayfirst=True)
    month = actuals_df['Date'].dt.month.iloc[0]
    year = actuals_df['Date'].dt.year.iloc[0]
    month_to_display = get_month_name_hebrew(month) + ' ' + str(year)

    # Calculate the number of weeks in the month
    num_days_in_month = calendar.monthrange(year, month)[1]

    # Calculate the day of the week the month starts on (0 is Monday, 6 is Sunday)
    start_day_of_month = (calendar.monthrange(year, month)[0] + 1) % 7

    num_weeks = (num_days_in_month + calendar.monthrange(year, month)[0]) // 7 + 1

    # Create a mapping of days in each week
    days_in_week = {}
    day = 1
    for week in range(1, num_weeks + 1):
        start_date = day
        end_date = min(day + 6 - (start_day_of_month if week == 1 else 0), num_days_in_month)
        days_in_week[week] = end_date - start_date + 1
        day = end_date + 1

    data = []

    for category in ['הוצאות משתנות','סופר','דלק','אוכל בחוץ','הוצאות קבועות','הכנסות']:
        category_data = actuals_df[actuals_df['Category'] == category]
        actuals_df = actuals_df.sort_values(by='Date', ascending=True)
        recommended = recommended_values.get(category, 0)

        if category == 'הוצאות קבועות' or category == 'הכנסות':
            # Week here is a category
            if category == 'הוצאות קבועות':
                sub_categories = ['חשמל', 'ביטוח דירה', 'ביטוח חיים', 'ביטוח בריאות', 'תחבורה', 'ביטוח שיניים',
                                      'אינטרנט', 'חבילות טלפון', 'ביטוח כללית', 'משכנתא', 'ועד בית',
                                     'ארנונה ומים']
            if category == 'הכנסות':
                sub_categories = ['הכנסות קבועות', 'הכנסות משתנות']

            spent_per_week = category_data.groupby('SubCategory')['Amount'].sum().to_dict()
            for sub_category in sub_categories:
                if sub_category not in spent_per_week.keys():
                    spent_per_week[sub_category] = 0
            recommended_per_week = {
                sub_category: recommended_values.get(sub_category, 0)
                for sub_category in sub_categories
            }
            actions = {
                sub_category: actuals_df[(actuals_df['Category'] == category) & ((actuals_df['SubCategory'] == sub_category))] for sub_category in sub_categories
            }

        else:
            spent_per_week = category_data.groupby('Week Number')['Amount'].sum().to_dict()
            for week in range(1, num_weeks + 1):
                if week not in spent_per_week.keys():
                    spent_per_week[week] = 0.0
            spent_per_week = dict(sorted(spent_per_week.items()))
            recommended_per_week = {
                week: round(
                    max((recommended - category_data['Amount'].sum()), 0) * (days_in_week[week] / num_days_in_month), 1)
                for week in range(1, num_weeks + 1)
            }

            actions = {
                week: actuals_df[(actuals_df['Category'] == category) & ((actuals_df['Week Number'] == week))] for week
                in range(1, num_weeks + 1)
            }

        percentage_spent = sum(spent_per_week.values()) / recommended * 100 if recommended else 0

        data.append({
            'category': category,
            'spent': spent_per_week,
            'recommended': recommended,
            'recommended_per_week': recommended_per_week,
            'percentage_spent': percentage_spent,
            'actions': actions
        })

    total_expenses = 0
    for item in data:
        if item['category'] in ['אוכל בחוץ', 'סופר', 'הוצאות משתנות', 'דלק']:
            total_expenses += sum(item['spent'].values())
        elif item['category'] == 'הוצאות קבועות':
            for sub_category in ['חשמל','ביטוח דירה','ביטוח חיים','ביטוח בריאות','תחבורה','ביטוח שיניים','אינטרנט','חבילות טלפון','ביטוח כללית','משכנתא','ועד בית','ארנונה ומים']:
                if current_file_index == 0:
                    if sub_category in item['spent'].keys() and item['spent'][sub_category] >= recommended_values.get(sub_category, 0):
                        total_expenses += item['spent'][sub_category]
                    else:
                        total_expenses += recommended_values.get(sub_category, 0)
                else:
                    total_expenses += item['spent'][sub_category]


    variable_amount_to_spent = recommended_values.get('הכנסות', 0) - total_expenses

    # Update the percentage_spent value for the specified category
    for entry in data:
        if entry['category'] == 'הוצאות משתנות':
            if variable_amount_to_spent < 0:
                entry['percentage_spent'] = 100
            else:
                entry['percentage_spent'] = (sum(spent_per_week.values()) - variable_amount_to_spent) / sum(spent_per_week.values()) * 100

            entry['recommended_per_week'] = {
                week: round(
                    max((variable_amount_to_spent - category_data['Amount'].sum()), 0) * (days_in_week[week] / num_days_in_month), 1)
                for week in range(1, num_weeks + 1)
            }

    # Define the desired order
    order = {
        'הוצאות משתנות': 1,
        'סופר': 2,
        'אוכל בחוץ': 3,
        'דלק': 4,
        'הוצאות קבועות': 5,
        'הכנסות': 6
    }

    # Sort the list
    data.sort(key=lambda x: order.get(x['category'], float('inf')))

    return render_template('expenses.html', data=data, total_expenses=total_expenses, num_weeks=num_weeks, sum=sum, round=round, round_up=math.ceil, format=format, month_to_display=month_to_display, variable_amount_to_spent=variable_amount_to_spent, current_file_index=current_file_index, files_count=len(files_list))

@app.route('/next')
def next_file():
    global current_file_index
    if current_file_index < len(files_list) - 1:
        current_file_index += 1
    return redirect(url_for('display_expenses'))

@app.route('/previous')
def previous_file():
    global current_file_index
    if current_file_index > 0:
        current_file_index -= 1
    return redirect(url_for('display_expenses'))


if __name__ == '__main__':

    threading.Thread(target=open_browser).start()
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)

    # How to start from terminal -  python app.py
