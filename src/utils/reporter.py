from pathlib import Path

from src.config.settings import FetchResult


class Reporter:
    """Generate and display reports"""

    @staticmethod
    def print_section(title: str):
        """Print section header"""
        print("\n" + "%" * 50)
        print(title)
        print("%" * 50)

    @staticmethod
    def print_fetch_summary(result: FetchResult, total_clients: int):
        """Print summary of fetch operation"""
        Reporter.print_section("FETCH SUMMARY")
        print(f"Total clients configured : {total_clients}")
        print(f"Clients with data        : {len(result.success_clients)}")
        print(f"Clients with EMPTY data  : {len(result.empty_clients)}")
        print(f"Clients FAILED           : {len(result.failed_clients)}")
        print(f"Fetch duration           : {result.duration:.2f}s")

        if result.success_clients:
            print(f"\n\033[92m[SUCCESS]\033[0m: {', '.join(result.success_clients)}")
        if result.empty_clients:
            print(f"\033[93m[EMPTY]\033[0m: {', '.join(result.empty_clients)}")
        if result.failed_clients:
            print(f"\033[91m[FAILED]\033[0m: {', '.join(result.failed_clients)}")

        print("%" * 50)

    @staticmethod
    def print_metric_summary(metrics: dict):
        """Print metric statistics"""
        Reporter.print_section("METRIC SUMMARY")
        print(f"Total rows                 : {metrics['total_rows']:,}")
        print(f"Rows with metric_1         : {metrics['metric1_rows']:,}")
        print(f"Rows with metric_2         : {metrics['metric2_rows']:,}")
        print("%" * 50)

    @staticmethod
    def print_completion(output_path: Path, row_count: int, duration: float):
        """Print completion message"""
        print(f"\nExport completed: {output_path}")
        print(f"Final rows: {row_count:,}")
        print(f"Total duration: {duration:.1f}s\n")