import argparse
from typing import Iterable

from src.config.settings import Config
from src.application.services.extraction_service import DataMonitoringService
from src.utils.file_handler import FileLoader
from src.domain.models.metric import MetricRegistry

class DailyPipeline:
    """Application-level orchestration for the daily refresh."""

    def __init__(self, config: Config, service: DataMonitoringService | None = None):
        self.config = config
        self.service = service or DataMonitoringService(config)
        self.registry = MetricRegistry(config)


    def get_clients(self) -> list[str]:
        databases = FileLoader.load_yaml(self.config.yaml_path).get("databases", [])
        return [db["client"] for db in databases if db.get("client")]


    def run(self, client: str | None = None, metric: str | None = None) -> None:
        metrics = (metric,) if metric else self.registry.metrics
        for selected_metric in metrics:
            self.registry.jobs_for(selected_metric)  # validate before doing work

        clients = [client] if client else self.get_clients()
        failures: list[str] = []
        for target_client in clients:
            for selected_metric in metrics:
                try:
                    self.run_metric(target_client, selected_metric)
                except Exception as exc:
                    failures.append(f"{target_client}/{selected_metric}: {exc}")
                    print(
                        f"\033[91m[ERROR]\033[0m "
                        f"Metric '{selected_metric}' failed for '{target_client}': {exc}"
                    )

        if failures:
            raise RuntimeError("Daily pipeline completed with failures: " + "; ".join(failures))


    def run_metric(self, client: str, metric: str) -> None:
        database = self._database_for(client)
        for index, job in enumerate(self.registry.jobs_for(metric), start=1):
            spreadsheet_id = database.get(job.spreadsheet_config_key)
            if not spreadsheet_id or not str(spreadsheet_id).strip():
                print(
                    f"\033[93m[SKIP]\033[0m {client} | {job.name}: "
                    f"'{job.spreadsheet_config_key}' is empty"
                )
                continue

            print(f"\n\033[94m[STEP {index}]\033[0m {job.name} for {client}")
            self.service.extract_and_push_specific_client(
                target_client=client,
                sql_folder_path=job.sql_folder_path,
                worksheet_path=job.worksheet_config_key,
                spreadsheet_path=job.spreadsheet_config_key,
                expect_columns=job.expected_columns,
                pos_clear_content=job.clear_range,
                pos_update_content=job.update_range,
            )


    def _database_for(self, client: str) -> dict:
        normalized = client.casefold()
        database = next(
            (
                item for item in FileLoader.load_yaml(self.config.yaml_path).get("databases", [])
                if item.get("client", "").casefold() == normalized
            ),
            None,
        )
        if database is None:
            raise ValueError(f"Client '{client}' not found in configuration")
        return database


def get_available_clients(config: Config) -> list[str]:
    return DailyPipeline(config).clients()


def get_available_sheets(config: Config) -> list[str]:
    return [
        metric.replace("_", " ").title()
        for metric in MetricRegistry(config).metrics
    ]


def refresh_specific_client_metric(
    service: DataMonitoringService,
    config: Config,
    client: str,
    metric: str,
) -> None:
    DailyPipeline(config, service).run_metric(client, metric)


def build_parser(metrics: Iterable[str]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Daily data monitoring refresh")
    parser.add_argument("--client", help="Process one client; default: all clients")
    parser.add_argument("--metric", choices=tuple(metrics), help="Process one metric; default: all metrics")
    parser.add_argument("--list", action="store_true", help="List configured clients and metrics")
    return parser


def run() -> None:
    config = Config.from_defaults()
    pipeline = DailyPipeline(config)
    args = build_parser(pipeline.registry.metrics).parse_args()

    if args.list:
        print("Clients:")
        print("\n".join(f"  - {client}" for client in pipeline.get_clients()))
        print("Metrics:")
        print("\n".join(f"  - {metric}" for metric in pipeline.registry.metrics))
        return

    pipeline.run(client=args.client, metric=args.metric)
