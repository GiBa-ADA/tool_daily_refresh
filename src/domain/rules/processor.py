from pathlib import Path
from typing import List

import pandas as pd

class DataProcessor:
    """Process and export extracted data"""
    @staticmethod
    def merge_dataframes(dataframes: List[pd.DataFrame]) -> pd.DataFrame:
        """Merge multiple dataframes into one"""
        if not dataframes:
            raise ValueError("No dataframes to merge")

        return pd.concat(dataframes, ignore_index=True)


    @staticmethod
    def normalize_schema(df: pd.DataFrame, expected_columns) -> pd.DataFrame:
        """Ensure dataframe has expected schema"""
        for col in expected_columns:
            if col not in df.columns:
                df[col] = pd.NA

        return df[expected_columns]


    @staticmethod
    def get_metric_summary(df: pd.DataFrame) -> dict:
        """Calculate metric statistics"""
        return {
            "total_rows": len(df),
            "metric1_rows": df.get("s_monitor_metric_1", pd.Series()).notna().sum(),
            "metric2_rows": df.get("s_monitor_metric_2", pd.Series()).notna().sum()
        }


    @staticmethod
    def export_csv(df: pd.DataFrame, output_path: Path):
        """Export dataframe to CSV"""
        df.to_csv(output_path, index=False)