from flask import Flask, render_template, request
from flask_uploads import UploadSet, configure_uploads, IMAGES
from ftplib import FTP
import os

app = Flask(__name__)

# Configure file uploads
uploads = UploadSet("uploads", IMAGES)
app.config["UPLOADED_UPLOADS_DEST"] = "uploads"
configure_uploads(app, uploads)

ftp_directory = "/public_html/assets"
ftp_host = "trinicoding.com"
ftp_user = "admin2@trinicoding.com"
ftp_password = "Rabbit12"

def ensure_upload_directory():
    upload_path = app.config["UPLOADED_UPLOADS_DEST"]
    if not os.path.exists(upload_path):
        os.makedirs(upload_path)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST" and "uploads" in request.files:
        file = request.files["uploads"]
        if file:
            # Ensure the upload directory exists
            ensure_upload_directory()

            # Save the file locally
            filename = os.path.join(app.config["UPLOADED_UPLOADS_DEST"], file.filename)
            file.save(filename)

            # Upload the file to FTP
            upload_to_ftp(filename, ftp_host, ftp_directory, ftp_user, ftp_password)

            # Remove the local file after uploading
            os.remove(filename)

    return render_template("index.html")

def upload_to_ftp(local_file, ftp_server, ftp_path, username, password):
    with FTP(ftp_server) as ftp:
        ftp.login(username, password)
        ftp.cwd(ftp_path)
        with open(local_file, "rb") as file:
            ftp.storbinary("STOR " + os.path.basename(local_file), file)

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
