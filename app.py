from flask import Flask, render_template, request
from instagrapi import Client
import gspread
from google.oauth2.service_account import Credentials
import os
import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Instagram login credentials
IG_USERNAME = 'dinosaur.819513'
IG_PASSWORD = 'Rahul@9899'

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'insta_logger.json'
SPREADSHEET_ID = '1ZKnxcXDZeKuhD-I_s-JWJY67qldmGB7pdUQ74CRrvHU'

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gs_client = gspread.authorize(creds)
sheet = gs_client.open_by_key(SPREADSHEET_ID).sheet1

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
            # Instagram login
            cl = Client()
            cl.login(IG_USERNAME, IG_PASSWORD)

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

            # Log text only
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [now, IG_USERNAME, target_username, message]
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
