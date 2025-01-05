# gsheets_helper.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def upload_df_to_sheets(df, sheet_name, creds_file, worksheet_name='Export_sheet'):
    # 1) Set the scopes
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    # 2) Authorize
    credentials = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scopes)
    gc = gspread.authorize(credentials)

    # 3) Open Google Sheet
    sheet = gc.open(sheet_name)  
    worksheet = sheet.worksheet(worksheet_name)

    # 4) Convert df to list of lists
    rows = [df.columns.tolist()] + df.values.tolist()

    # 5) (Optionally) Clear existing data before upload
    worksheet.clear()

    # 6) Upload
    worksheet.update(rows)
    print("DataFrame successfully uploaded to Google Sheets!")
