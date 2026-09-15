from pathlib import Path
import pandas as pd
from typing import List
import datetime
import yaml
from dotenv import load_dotenv


class FileLoader:
    """Handle file loading operations"""

    @staticmethod
    def load_yaml(path: Path) -> dict:
        """
            Purpose: This function loads a yaml file.
            Args:
                :param path: Path to the yaml file.
            Created at: 2026-01-23 | Ehg
        """
        load_dotenv()
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @staticmethod
    def load_sql(path: Path) -> str:
        """
            Purpose: This function loads a sql file.
            Args:
                :param path: path to the sql file.
            Created at: 2026-01-23 | Ehg
        """
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
        
    @staticmethod
    def load_all_sql(folder_path: str) -> list:
        """Load all file .sql trong folder"""
        folder = Path(folder_path)

        if not folder.exists():
            raise ValueError(f"\033[91m[ERROR]\033[0m SQL folder not found: {folder_path}")

        sql_files = sorted(folder.glob("*.sql"))

        queries = []
        for file in Path(folder_path).glob("*.sql"):
            with open(file, "r", encoding="utf-8") as f:
                sql = f.read()
                name = file.stem

                queries.append((name, sql))

        return queries
    
    @staticmethod
    def load_seller_ids_from_csv(csv_path: str) -> List[str]:
        """Load seller IDs from client_key CSV file"""
        df = pd.read_csv(csv_path)
        return df.iloc[:, 0].tolist()
    
    @staticmethod
    def save_extracted_file(client_name: str, output_file: str, data) -> Path:
        """Lưu file vào extracted/client_name/run_date/output_file"""
        run_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        dir_path = Path("extracted") / client_name / run_date / "database"
        dir_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dir_path / output_file
        data.to_csv(file_path, index=False)  # nếu là pandas df
        
        return file_path
    
    @staticmethod
    def save_extracted_file_ui(client_name: str, output_file: str, data) -> Path:
        """Lưu file vào extracted/client_name/run_date/output_file"""
        run_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        dir_path = Path("extracted") / client_name / run_date / "ui"
        dir_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dir_path / output_file
        data.to_csv(file_path, index=False)  # nếu là pandas df
        
        return file_path