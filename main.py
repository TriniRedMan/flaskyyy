from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import re
import os
import openpyxl

def print_files_in_current_folder():
    current_folder = os.getcwd()  # Get the current working directory
    files = [f for f in os.listdir(current_folder) if os.path.isfile(os.path.join(current_folder, f))]

    if files:
        print("Files in the current folder:")
        for file in files:
            print(file)
    else:
        print("No files found in the current folder.")

# Call the function to print files
print_files_in_current_folder()

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure secret key

@app.route('/')
def default_page():
    return render_template('login.html')

# Dummy user for demonstration purposes
class User:
    def __init__(self, id):
        self.id = id

# Replace this with your actual user authentication logic
def authenticate(username, password):
    if username == 'user' and password == 'password':
        return User(1)
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = authenticate(username, password)
        if user:
            # Store user ID in the session
            session['user_id'] = user.id
            print(f"User {username} logged in successfully")
            return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    # Clear the user ID from the session
    session.pop('user_id', None)
    print("User logged out")
    return redirect(url_for('login'))

@app.before_request
def check_authentication():
    if 'user_id' not in session and request.endpoint != 'login':
        print("Redirecting to login page")
        return redirect(url_for('login'))

# Load the Excel file
excel_file_path = 'entities.xlsx'
df = pd.read_excel(excel_file_path)

# Get the column names for the dropdown
column_names = df.columns.tolist()

@app.route('/index')
def index():
    print("Accessing index page")
    return render_template('index.html', column_names=column_names)

@app.route('/search', methods=['POST'])
def search():
    search_text = request.form['search_text']
    selected_column = request.form['selected_column']

    if not search_text or not selected_column:
        return render_template('index.html', column_names=column_names, error="Please enter a name and select a column.")

    search_result = search_name_in_database(search_text, selected_column)

    return render_template('index.html', column_names=column_names, search_result=search_result)

def search_name_in_database(name, column):
    search_name_normalized = re.sub(r'\s+', ' ', name.strip()).lower()

    if column not in df.columns:
        return f"Column '{column}' not found in the database."

    column_data = df[column].fillna('').str.lower()
    matching_results = df[column_data.str.contains(search_name_normalized)]

    return matching_results.to_html(index=False)

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
