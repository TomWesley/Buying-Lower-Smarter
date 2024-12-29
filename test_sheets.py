import gspread
from oauth2client.service_account import ServiceAccountCredentials

# PATH TO YOUR DOWNLOADED JSON KEY
SERVICE_ACCOUNT_FILE = r"C:\Users\ioana\projects\bigloserkey\stock-analysis-sheets-export-b83325cfadb5.json"

# Google Sheet
SHEET_NAME = 'Biggest Loser Results'

def main():
    # 1) Define the OAuth scopes
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",  # Read/write access to spreadsheets
        "https://www.googleapis.com/auth/drive"          # Optional: needed if you want to do drive-level tasks
    ]

    # 2) Create credentials object from your JSON key
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        SERVICE_ACCOUNT_FILE, 
        scopes
    )

    # 3) Authorize gspread
    gc = gspread.authorize(credentials)

    # 4) Open the Google Sheet by name
    #    (Alternatively, you can open by URL or by key)
    try:
        sheet = gc.open(SHEET_NAME)
    except Exception as e:
        print("Could not open the sheet. Check name and sharing settings.")
        print(e)
        return

    # 5) Select the first worksheet (Sheet1) or by name
    worksheet = sheet.sheet1  # or sheet.worksheet("Sheet1")

    # 6) Test reading/writing
    #    Let's write something into cell A1, for example:
    worksheet.update_acell('A1', 'Hello from Python!')

    # 7) Print a success message
    print("Updated A1 with a test message successfully.")

if __name__ == '__main__':
    main()
