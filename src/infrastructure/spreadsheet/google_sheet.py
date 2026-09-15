from pathlib import Path

import gspread
from gspread import WorksheetNotFound
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GoogleSheetClient:
    def __init__(self, credential_path: Path):
        creds = Credentials.from_service_account_file(credential_path, scopes=SCOPES)
        self._gc = gspread.authorize(creds)

    def get_or_create_worksheet(
        self,
        spreadsheet_id: str,
        worksheet_name: str,
        rows: int = 2000,
        cols: int = 50,
    ) -> gspread.Worksheet:
        """Open a worksheet by name, creating it if it doesn't exist yet."""
        sheet = self._gc.open_by_key(spreadsheet_id)
        try:
            return sheet.worksheet(worksheet_name)
        except WorksheetNotFound:
            return sheet.add_worksheet(title=worksheet_name, rows=rows, cols=cols)