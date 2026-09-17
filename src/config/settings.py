from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SheetConfig:
    """Per-domain sheet/SQL configuration.

    One instance of this replaces the 9 repeated fields that used to
    live directly on Config for each of sales_traffic / media / content.
    """
    sql_folder_path: Path
    sql_folder_path_ui: Path
    spreadsheet_id: str
    worksheet_name: str
    worksheet_name_ui: str
    pos_clear_content: str
    pos_update_content: str
    pos_clear_content_ui: str
    pos_update_content_ui: str

    @classmethod
    def build(
        cls,
        base_dir: Path,
        domain: str,
        spreadsheet_id: str,
        worksheet_name: str,
        worksheet_name_ui: str,
        pos_clear_content: str,
        pos_update_content: str,
        pos_clear_content_ui: str,
        pos_update_content_ui: str,
    ) -> "SheetConfig":
        """Build a SheetConfig for a given domain, deriving the two
        sql folder paths from base_dir + domain so callers don't repeat
        the folder-path pattern."""
        return cls(
            sql_folder_path=base_dir / "sql" / "database" / domain,
            sql_folder_path_ui=base_dir / "sql" / "ui" / domain,
            spreadsheet_id=spreadsheet_id,
            worksheet_name=worksheet_name,
            worksheet_name_ui=worksheet_name_ui,
            pos_clear_content=pos_clear_content,
            pos_update_content=pos_update_content,
            pos_clear_content_ui=pos_clear_content_ui,
            pos_update_content_ui=pos_update_content_ui,
        )


@dataclass
class Config:
    """Application configuration"""
    base_dir: Path
    yaml_path: Path
    sql_path: Path
    client_key_path: Path
    credential_path: Path

    output_dir: Path
    output_csv: Path
    run_dt: datetime

    # One SheetConfig per domain instead of 27 flat fields.
    sheets: dict[str, SheetConfig] = field(default_factory=dict)

    max_concurrent: int = 3
    max_retries: int = 10
    connection_timeout: int = 300
    query_timeout: int = 60000

    def sheet(self, domain: str) -> SheetConfig:
        """Convenience accessor, e.g. config.sheet('media').spreadsheet_id"""
        return self.sheets[domain]

    @classmethod
    def from_defaults(cls) -> "Config":
        """Create config from default paths"""
        # settings.py is stored at <project-root>/src/config/settings.py.
        base_dir = Path(__file__).resolve().parents[2]
        run_dt = datetime.now()
        run_date = run_dt.strftime("%Y-%m-%d")
        run_time = run_dt.strftime("%H%M%S")

        output_dir = base_dir / "extracted"
        output_dir.mkdir(exist_ok=True, parents=True)

        sheets = {
            "media": SheetConfig.build(
                base_dir, "media",
                spreadsheet_id="media_spreadsheet_id",
                worksheet_name="[media] database",
                worksheet_name_ui="[media] automated_input",
                pos_clear_content="B2:I",
                pos_update_content="B3",
                pos_clear_content_ui="C4:J",
                pos_update_content_ui="C5",
            ),
            "sales_traffic": SheetConfig.build(
                base_dir, "sales_traffic",
                spreadsheet_id="sales_traffic_spreadsheet_id",
                worksheet_name="[sales_traffic] database",
                worksheet_name_ui="[sales_traffic] automated_input",
                pos_clear_content="B3:I",
                pos_update_content="B3",
                pos_clear_content_ui="C5:I",
                pos_update_content_ui="C5",
            ),
            "content": SheetConfig.build(
                base_dir, "content",
                spreadsheet_id="content_spreadsheet_id",
                worksheet_name="[content] database",
                worksheet_name_ui="[content] automated_input",
                pos_clear_content="B3:I",
                pos_update_content="B3",
                pos_clear_content_ui="C5:I",
                pos_update_content_ui="C5",
            ),
            "sales_affiliate": SheetConfig.build(
                base_dir, "sales_affiliate",
                spreadsheet_id="sales_traffic_spreadsheet_id",
                worksheet_name="[sales_affiliate] database",
                worksheet_name_ui="[sales_affiliate] automated_input",
                pos_clear_content="B3:I",
                pos_update_content="B3",
                pos_clear_content_ui="C5:I",
                pos_update_content_ui="C5",
            ),
            "product": SheetConfig.build(
                base_dir, "product",
                spreadsheet_id="sales_traffic_spreadsheet_id",
                worksheet_name="[product] database",
                worksheet_name_ui="",
                pos_clear_content=None,
                pos_update_content="B3",
                pos_clear_content_ui=None,
                pos_update_content_ui="C5",
            ),
        }

        return cls(
            base_dir=base_dir,
            yaml_path=base_dir / "db_connection.yaml",
            sql_path=base_dir / "sql" / "data_monitoring.sql",
            credential_path=base_dir / "src" / "config" / "api_key" / "ada-data-monitoring-85e75cf7cf3f.json",
            client_key_path=base_dir / "src" / "config" / "client_key",
            output_dir=output_dir,
            output_csv=output_dir / f"data_monitoring_export_{run_date}_{run_time}.csv",
            run_dt=run_dt,
            sheets=sheets,
        )


@dataclass
class FetchResult:
    """Result from database fetch operation"""
    success_clients: list[str]
    empty_clients: list[str]
    failed_clients: list[str]
    dataframes: list
    duration: float