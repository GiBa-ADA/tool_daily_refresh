import logging
import os
from pathlib import Path
import pandas as pd
from datetime import date

from src.infrastructure.spreadsheet.google_sheet import GoogleSheetClient
from src.utils.date_formatter import DateFormater

def log_config():
    base_dir = Path("logs")
    base_dir.mkdir(exist_ok=True, parents=True)  # was missing in the original — would crash on a fresh checkout
    log_file = os.path.join(base_dir, "upload_gsheet_daily_raw.log")

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(task)s | %(message)s"
    )


def push_excel_dynamic(
        credential_path: Path,
        output_path: Path,
        spreadsheet_id: str,
        worksheet_name: str,
        client_name: str,
        pos_clear_content: str,
        pos_update_content: str,
    ):
    log_config()

    df = pd.read_csv(output_path).fillna('')

    client = GoogleSheetClient(credential_path)
    # print(f'[DEBUG] {spreadsheet_id}')
    ws = client.get_or_create_worksheet(spreadsheet_id, worksheet_name)

    print(f"\033[94m[PROCESS]\033[0m [{client_name}] Uploading to Google Sheet...")

    try:
        ws.batch_clear([pos_clear_content])
        ws.update(pos_update_content, df.values.tolist(), value_input_option="USER_ENTERED")

        logging.info(f"[{client_name}] sheet {worksheet_name} successfully updated", extra={"task": "PUSH_SHEET"})
        print(f"\033[92m[SUCCESS]\033[0m [{client_name}] Sheet {worksheet_name} updated")

    except Exception as e:
        logging.error(f"[{client_name}] failed to update sheet {worksheet_name}: {e}", extra={"task": "PUSH_SHEET"})
        print(f"\033[91m[ERROR]\033[0m [{client_name}] Sheet {worksheet_name} failed: {e}")
        raise



def push_excel_product(
        credential_path: Path,
        output_path: Path,
        spreadsheet_id: str,
        worksheet_name: str,
        client_name: str,
        pos_clear_content: str = None,
        pos_update_content: str = "B3",
    ):

    log_config()
    _ = pos_clear_content

    client = GoogleSheetClient(credential_path)
    ws = client.get_or_create_worksheet(spreadsheet_id, worksheet_name)

    df = pd.read_csv(output_path)
    df = df.fillna("")

    if "day" not in df.columns:
        raise ValueError("Product CSV is missing required key column 'day'")

    today = date.today()
    df["_day_key"] = df["day"].map(DateFormater._to_date)
    today_df = df[df["_day_key"] == today].drop(columns=["_day_key"]).copy()
    today_df["day"] = today.strftime("%Y-%m-%d")

    print(f"\033[94m[PROCESS]\033[0m [{client_name}] Uploading product (today={today}) to Google Sheet...")

    if today_df.empty:
        logging.info(
            f"[{client_name}] sheet {worksheet_name} skipped: no rows for {today}",
            extra={"task": "PUSH_SHEET"}
        )
        print(f"\033[93m[WARNING]\033[0m [{client_name}] No product rows for today ({today}); sheet unchanged")
        return

    start_cell = pos_update_content or "B3"
    start_col = start_cell[:1]
    start_row = int(start_cell[1:])
    day_col_index = list(today_df.columns).index("day")
    end_col = DateFormater._col_letter(start_col, len(today_df.columns) - 1)
    data_range = f"{start_col}{start_row}:{end_col}"

    try:
        existing = ws.get(data_range)
        today_sheet_rows = []

        for offset, row in enumerate(existing or []):
            cell_value = row[day_col_index] if len(row) > day_col_index else None
            if DateFormater._to_date(cell_value) == today:
                today_sheet_rows.append(start_row + offset)

        for block_start, block_end in reversed(DateFormater._consecutive_blocks(today_sheet_rows)):
            ws.delete_rows(block_start, block_end)

        remaining = ws.get(data_range)
        last_row = start_row - 1
        if remaining:
            last_row = start_row + len(remaining) - 1

        next_row = last_row + 1
        values = today_df.values.tolist()
        needed_rows = next_row + len(values) - 1
        if needed_rows > ws.row_count:
            ws.add_rows(needed_rows - ws.row_count)

        ws.update(f"{start_col}{next_row}", values, value_input_option="USER_ENTERED")

        logging.info(
            f"[{client_name}] sheet {worksheet_name} product upserted {len(values)} rows for {today} at {start_col}{next_row}",
            extra={"task": "PUSH_SHEET"}
        )
        print(
            f"\033[92m[SUCCESS]\033[0m [{client_name}] Sheet {worksheet_name} "
            f"product updated ({len(today_sheet_rows)} old rows removed, "
            f"{len(values)} rows appended at {start_col}{next_row})"
        )

    except Exception as e:
        logging.error(f"[{client_name}] failed to update sheet {worksheet_name}: {e}", extra={"task": "PUSH_SHEET"})
        print(f"\033[91m[ERROR]\033[0m [{client_name}] Sheet {worksheet_name} failed: {e}")
        raise
