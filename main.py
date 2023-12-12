from flask import Flask, render_template, request, redirect, url_for, session,jsonify
from flask_uploads import UploadSet, configure_uploads, IMAGES

import pandas as pd
import re
import os
import openpyxl
from webdav3.client import Client
import jsons



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

# Load the entities Excel file for column selection
entities_file_path = 'entities.xlsx'
df_entities = pd.read_excel(entities_file_path)

# Get the column names for the entities file dropdown
column_names_entities = df_entities.columns.tolist()

# Initialize column_names_uploaded as an empty list
column_names_uploaded = []

@app.route('/index')
def index():
    print("Accessing index page")
    return render_template('index.html', column_names_entities=column_names_entities)

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

# Configure file uploads
uploads = UploadSet("uploads", IMAGES)
app.config["UPLOADED_UPLOADS_DEST"] = "uploads"
configure_uploads(app, uploads)

webdav_url = "https://ogi.teracloud.jp/dav/"  # Replace with your WebDAV server URL
webdav_user = "triniredman"
webdav_password = "9JRTsQxCoVcgBUh4"
webdav_path = "Documents/"
documents_path = os.path.expanduser("~/Documents")

def ensure_upload_directory():
    upload_path = app.config["UPLOADED_UPLOADS_DEST"]
    if not os.path.exists(upload_path):
        os.makedirs(upload_path)

def upload_to_webdav(local_file, webdav_url, webdav_path, username, password):
    options = {
        "webdav_hostname": webdav_url,
        "webdav_login": username,
        "webdav_password": password,
        "webdav_root": webdav_path,
    }

    client = Client(options)
    try:
        client.upload_sync(remote_path=os.path.basename(local_file), local_path=local_file)
        return True
    except Exception as e:
        print(f"Error uploading file: {e}")
        return False

def save_columns_to_json(selected_columns, filename='columns.json'):
    try:
        with open(filename, 'w') as file:
            json.dump(selected_columns, file)  # Use JSON module to save as JSON
        print(f"Columns saved to {filename}")
    except Exception as e:
        print(f"Error saving columns to file: {e}")

def load_columns_from_json(filename='columns.json'):
    try:
        with open(filename, 'r') as file:
            columns = json.load(file)  # Use JSON module to load from JSON
        return columns
    except Exception as e:
        print(f"Error loading columns from file: {e}")
        return []
    


def save_columns_to_file(selected_columns_uploaded, selected_columns_entities, filename='columns.txt'):
    try:
        with open(filename, 'w') as file:
            # Write selected columns from the uploaded file
            #file.write("Uploaded File Columns:\n")
            for column in selected_columns_uploaded:
                file.write(f"{column}")

            # Add a separator between sections
            #file.write("\nEntities File Columns:\n")

            # Write selected columns from the entities file
            for column in selected_columns_entities:
                file.write(f"{column}\n")
                #file.write(f"{column}\n")

        print(f"Columns saved to {filename}")
    except Exception as e:
        print(f"Error saving columns to file: {e}")
     

@app.route('/bulk_upload')
def bulk_upload():
    return render_template("index2.html")

@app.route("/", methods=["GET", "POST"])
def index2():
    if request.method == "POST" and "uploads" in request.files:
        file = request.files["uploads"]
        if file:
            # Save the uploaded file
            file_path = os.path.join(app.config["UPLOADED_UPLOADS_DEST"], file.filename)
            file.save(file_path)

            # Get the selected columns from the form
            selected_columns = request.form.getlist("selected_columns")

            # Save the selected columns to a JSON file
            save_columns_to_json(selected_columns)

            # Upload the updated columns file to WebDAV
            upload_to_webdav('columns.json', webdav_url, webdav_path, webdav_user, webdav_password)

            # Check if the file has a .xlsx extension before uploading
            if file.filename.endswith('.xlsx'):
                # Upload the uploaded Excel file to WebDAV
                upload_to_webdav(file_path, webdav_url, webdav_path, webdav_user, webdav_password)

                # Redirect to the comparison page with the uploaded file name and selected columns
                return redirect(url_for("compare", filename=file.filename, columns_file='columns.json'))
            
            else:
                return render_template("index2.html", error="Please upload a valid Excel file.")

    return render_template("index2.html")

# ...

@app.route("/compare/<filename>", methods=["GET", "POST"])
def compare(filename):
    # Load the selected columns from the JSON file if it exists
    columns_file = 'columns.json'
    columns_file_path = os.path.join(app.config["UPLOADED_UPLOADS_DEST"], columns_file)
    
    if os.path.exists(columns_file_path):
        selected_columns = load_columns_from_json(columns_file_path)
    else:
        # Set default value if the file doesn't exist
        selected_columns = []

    # Initialize selected_column_uploaded and selected_column_entities outside the if block
    selected_column_uploaded = None
    selected_column_entities = None

    # Check if selected_columns is not empty before accessing its elements
    if selected_columns:
        # Separate the selected columns for the uploaded file and the entities file
        selected_column_uploaded = selected_columns[0]
        selected_column_entities = selected_columns[1] if len(selected_columns) > 1 else None

        # Update column_names_uploaded
        column_names_uploaded = [selected_column_uploaded]
    else:
        # If no selected columns, default to an empty list
        column_names_uploaded = []

    if request.method == "POST":
        # Get selected columns from the form
        selected_column_uploaded = request.form["selected_column"]
        selected_column_entities = request.form["selected_column_entities"]

        # Update the selected columns list
        selected_columns = [selected_column_uploaded, selected_column_entities]

        # Save the updated columns to the JSON file
        save_columns_to_json(selected_columns, columns_file_path)

        # Upload the updated columns file to WebDAV
        upload_to_webdav(columns_file, webdav_url, webdav_path, webdav_user, webdav_password)

        # Upload the selected columns to WebDAV
        save_columns_to_file([selected_column_uploaded], 'selected_columns.txt')
        upload_to_webdav('selected_columns.txt', webdav_url, webdav_path, webdav_user, webdav_password)

        # Update column_names_uploaded
        column_names_uploaded = [selected_column_uploaded]

    try:
        # Load the uploaded Excel file for column selection
        df_uploaded = pd.read_excel(os.path.join(app.config["UPLOADED_UPLOADS_DEST"], filename))
    except FileNotFoundError:
        # Handle the case where the file is not found
        print(f"File not found: {filename}")
        df_uploaded = pd.DataFrame()  # Create an empty DataFrame

    # Get the column names for the uploaded file dropdown
    column_names_uploaded = df_uploaded.columns.tolist()

    # Load the entities Excel file for column selection
    entities_file_path = 'entities.xlsx'
    df_entities = pd.read_excel(entities_file_path)

    # Get the column names for the entities file dropdown
    column_names_entities = df_entities.columns.tolist()

    return render_template("compare.html", filename=filename, column_names_uploaded=column_names_uploaded, column_names_entities=column_names_entities,
                           selected_column_uploaded=selected_column_uploaded, selected_column_entities=selected_column_entities)


if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
