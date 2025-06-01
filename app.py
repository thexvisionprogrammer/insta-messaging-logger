from flask import Flask, render_template, request
from instagrapi import Client
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import datetime
import pickle

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder=os.path.dirname(os.path.abspath(__file__)))
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Load credentials from environment variables
IG_USERNAME = os.getenv('IG_USERNAME')
IG_PASSWORD = os.getenv('IG_PASSWORD')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gs_client = gspread.authorize(creds)
sheet = gs_client.open_by_key(SPREADSHEET_ID).sheet1

# Session file path
SESSION_FILE = 'instagram_session.pkl'

def save_session(cl):
    with open(SESSION_FILE, 'wb') as f:
        pickle.dump(cl.get_settings(), f)

def load_session():
    if os.path.exists(SESSION_FILE):
        cl = Client()
        with open(SESSION_FILE, 'rb') as f:
            cl.set_settings(pickle.load(f))
        return cl
    return None

@app.route('/', methods=['GET', 'POST'])
def home():
    status_message = ""
    if request.method == 'POST':
        target_username = request.form.get('target_username')
        message = request.form.get('message')
        images = request.files.getlist('images')

        if not target_username or not message:
            status_message = "Please enter both target username and message."
            return render_template('index.html', status=status_message)

        try:
            # Load session or login
            cl = load_session()
            if not cl or not cl.get_settings():
                cl = Client()
                cl.login(IG_USERNAME, IG_PASSWORD)
                save_session(cl)

            # Get user ID
            user_id = cl.user_id_from_username(target_username)

            # Send text message
            cl.direct_send(message, [user_id])

            # Handle images (send only, do not log)
            for img in images[:10]:  # Limit to 10 images
                if img and img.filename:
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
                    img.save(filepath)
                    cl.direct_send_photo(filepath, [user_id])

            # Log text only with status indicator
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [now, IG_USERNAME, target_username, message, "✅"]
            sheet.append_row(row)

            status_message = f"✅ Message and up to 10 images sent successfully."
        except Exception as e:
            print("Exception occurred:", e)
            status_message = f"❌ Error: {str(e)}"

    return render_template('index.html', status=status_message)

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
