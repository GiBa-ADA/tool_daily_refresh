from datetime import date, datetime
import pandas as pd

class DateFormater:

    @staticmethod
    def _to_date(value):
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(text[:10], fmt).date()
            except ValueError:
                continue

        parsed = pd.to_datetime(text, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.date()


    @staticmethod
    def _col_letter(start_col: str, offset: int) -> str:
        return chr(ord(start_col.upper()) + offset)


    @staticmethod
    def _consecutive_blocks(row_numbers: list[int]) -> list[tuple[int, int]]:
        if not row_numbers:
            return []

        ordered = sorted(set(row_numbers))
        blocks = []
        start = prev = ordered[0]

        for row in ordered[1:]:
            if row == prev + 1:
                prev = row
                continue
            blocks.append((start, prev))
            start = prev = row

        blocks.append((start, prev))
        return blocks