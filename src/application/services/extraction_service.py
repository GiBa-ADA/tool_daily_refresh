import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional
import pandas as pd

from src.config.settings import Config
from src.domain.rules.extractor import DataExtractor
from src.domain.rules.processor import DataProcessor
from src.utils.reporter import Reporter
from src.utils.file_handler import FileLoader
from src.infrastructure.logging.logger import Logger
from src.application.services.publishing_service import push_excel_dynamic, push_excel_product


class DataMonitoringService:
    """Service for data monitoring extraction and processing"""

    def __init__(self, config: Config):
        self.config = config
        self.extractor = DataExtractor()
        self.processor = DataProcessor()
        self.reporter = Reporter()

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    """ FUNCTION REFRESH SPECIFIC CLIENT """
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    def extract_and_push_specific_client(
        self,
        target_client: str,
        progress_callback: Optional[Callable[[str, str], None]] = None,
        credential_path: Optional[Path] = None,
        sql_folder_path: str | Path | None = None,
        worksheet_path: str | None = None,
        spreadsheet_path: str | None = None,
        expect_columns: Optional[list[str]] = None,
        pos_clear_content: Optional[str] = None,
        pos_update_content: Optional[str] = None,
    ) -> None:
        """
        Extract and push data for a specific client only

        Args:
            target_client: Name of the client to process
        """
        Logger.setup()

        yaml_config = FileLoader.load_yaml(self.config.yaml_path)
        databases = yaml_config.get("databases", [])
        credential_path=self.config.credential_path

        if not databases:
            print("\033[91m[ERROR]\033[0m No databases configured")
            return

        # Find the target client
        db_conf = None
        for db in databases:
            if db.get('client', '').lower() == target_client.lower():
                db_conf = db
                break

        if not db_conf:
            available = [db.get('client', 'unknown') for db in databases]
            print(f"\033[91m[ERROR]\033[0m Client '{target_client}' not found.")
            print(f"Available clients: {', '.join(available)}")
            raise ValueError(f"Client '{target_client}' not found in configuration")

        queries = FileLoader.load_all_sql(sql_folder_path)
        spreadsheet_id = db_conf.get(spreadsheet_path)
        client_name = db_conf.get('client', 'unknown')
        client_key_csv = f"{self.config.client_key_path}/{client_name.lower()}.csv"
        seller_ids = FileLoader.load_seller_ids_from_csv(client_key_csv)

        print(f"\n{'='*50}")
        print(f"\033[94m[PROCESS]\033[0m Processing Client: {client_name}")
        print(f"\033[94m[PROCESS]\033[0m Total Queries: {len(queries)}")
        print(f"\033[94m[PROCESS]\033[0m Seller IDs: {seller_ids[:1]}, etc...")
        print(f"{'='*50}")

        start_time = datetime.now()
        
        result = asyncio.run(
            self.extractor.fetch_all_queries(
                db_conf=db_conf, 
                queries=queries,
                seller_ids=seller_ids,
                progress_callback=progress_callback,
            )
        )

        if not result.dataframes:
            print(f"\033[91m[ERROR]\033[0m No data fetched for {client_name}.")
            raise ValueError(f"No data fetched for {client_name}")

        final_df = self.processor.merge_dataframes(result.dataframes)
        final_df = self.processor.normalize_schema(final_df, expected_columns=expect_columns)

        base_output = Path(self.config.output_csv)
        client_csv_path = FileLoader.save_extracted_file(client_name, base_output.name, final_df)
        self.processor.export_csv(final_df, client_csv_path)

        # print(f'[DEBUG] {worksheet_path}')

        try:
            push_fn = push_excel_product if pos_clear_content is None else push_excel_dynamic
            push_fn(
                credential_path=credential_path,
                output_path=client_csv_path,
                spreadsheet_id=spreadsheet_id,
                worksheet_name=worksheet_path,
                client_name=client_name,
                pos_clear_content=pos_clear_content,
                pos_update_content=pos_update_content,
            )
            total_duration = (datetime.now() - start_time).total_seconds()
            print(f"\n\033[92m[SUCCESS]\033[0m Completed processing {client_name} in {total_duration:.2f}s")
        except Exception as e:
            print(f"\033[91m[ERROR]\033[0m Failed to push {client_name}: {e}")
            raise


# For backward compatibility - export function at module level
def extract_data_monitoring() -> Optional[Path]:
    """
    Standalone function for backward compatibility

    Usage:
        from services.data_monitoring_service import extract_data_monitoring
        output_path = extract_data_monitoring()
    """
    service = DataMonitoringService()
    return service.extract_data_monitoring()
