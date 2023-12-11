from flask import Flask, render_template, request, redirect, url_for, session
from flask_uploads import UploadSet, configure_uploads, IMAGES

import pandas as pd
import re
import os
import openpyxl
from webdav3.client import Client

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
excel_file_path = os.path.join('static', 'entities.xlsx')
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

# Configure file uploads
uploads = UploadSet("uploads", IMAGES)
app.config["UPLOADED_UPLOADS_DEST"] = "uploads"
configure_uploads(app, uploads)

webdav_url = "http://127.0.0.1:4443/dS0kAACD/megastuff"  # Replace with your WebDAV server URL
webdav_user = "rabbitmasterjohnny@gmail.com"
webdav_password = "Rabbit123"
webdav_path = "/dS0kAACD/megastuff"
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

def download_from_webdav(remote_file, webdav_url, webdav_path, username, password, local_path):
    options = {
        "webdav_hostname": webdav_url,
        "webdav_login": username,
        "webdav_password": password,
        "webdav_root": webdav_path,
    }

    client = Client(options)
    try:
        client.download_sync(remote_path=remote_file, local_path=local_path)
        print(f"File downloaded to {local_path}")
    except Exception as e:
        print(f"Error downloading file: {e}")

def save_columns_to_file(selected_columns, filename='columns.txt'):
    try:
        with open(filename, 'w') as file:
            for column in selected_columns:
                file.write(f"{column}\n")
        print(f"Columns saved to {filename}")
    except Exception as e:
        print(f"Error saving columns to file: {e}")
     

@app.route('/bulk_upload')
def bulk_upload():
    return render_template("index2.html")
    #return redirect(url_for('uploadpg'))
    

@app.route("/", methods=["GET", "POST"])
def index2():
    if request.method == "POST" and "uploads" in request.files:
        file = request.files["uploads"]
        if file:
            # Ensure the upload directory exists
            ensure_upload_directory()

            # Save the file locally
            filename = os.path.join(app.config["UPLOADED_UPLOADS_DEST"], file.filename)
            file.save(filename)

            # Get the selected columns from the form
            selected_columns = request.form.getlist("selected_columns")

            # Save the selected columns to a text file
            save_columns_to_file(selected_columns)

            # Upload the file to WebDAV
            success = upload_to_webdav(filename, webdav_url, webdav_path, webdav_user, webdav_password)

            # Remove the local file after uploading
            os.remove(filename)

            # Check if the upload was successful
            if success:
                # Redirect to the comparison page with the uploaded file name
                return redirect(url_for("compare", filename=file.filename))

    return render_template("index2.html")

def load_columns_from_file(filename='columns.txt'):
    with open(filename, 'r') as file:
        columns = [line.strip() for line in file]
    return columns

@app.route("/compare/<filename>", methods=["GET", "POST"])
def compare(filename):
    # Load the selected columns from the text file
    selected_columns = load_columns_from_file()

    # Construct the WebDAV path for the uploaded file
    remote_file_path = os.path.join(webdav_path, filename)

    # Download the uploaded file to the Documents folder
    download_path_uploaded = os.path.join(documents_path, filename)
    download_from_webdav(filename, webdav_url, webdav_path, webdav_user, webdav_password, download_path_uploaded)

    # Load the uploaded Excel file
    df_uploaded = pd.read_excel(download_path_uploaded)

    # Get the column names for the uploaded file dropdown
    column_names_uploaded = df_uploaded.columns.tolist()

    # Load the entities Excel file for column selection
    entities_file_path = 'entities.xlsx'
    df_entities = pd.read_excel(entities_file_path)

    # Get the column names for the entities file dropdown
    column_names_entities = df_entities.columns.tolist()

    if request.method == "POST":
        # Get selected columns from the form
        selected_column_uploaded = request.form["selected_column"]
        selected_column_entities = request.form["selected_column_entities"]

        # Add the selected columns to the list
        selected_columns.extend([selected_column_uploaded, selected_column_entities])

        # Save the updated columns to the text file
        save_columns_to_file(selected_columns)

        # Upload the updated columns file to WebDAV
        upload_to_webdav('columns.txt', webdav_url, webdav_path, webdav_user, webdav_password)


    return render_template("compare.html", filename=filename, column_names=column_names_uploaded, column_names_entities=column_names_entities)


if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
