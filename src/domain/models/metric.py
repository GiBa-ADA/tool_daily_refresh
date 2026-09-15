from dataclasses import dataclass
from src.config.settings import Config, SheetConfig
from src.infrastructure.database import schema


@dataclass(frozen=True)
class MetricJob:
    """One extract-and-publish operation for a metric."""

    name: str
    sheet: SheetConfig
    expected_columns: list[str]
    ui: bool = False

    @property
    def sql_folder_path(self):
        return self.sheet.sql_folder_path_ui if self.ui else self.sheet.sql_folder_path

    @property
    def worksheet_config_key(self):
        return self.sheet.worksheet_name_ui if self.ui else self.sheet.worksheet_name

    @property
    def spreadsheet_config_key(self):
        return self.sheet.spreadsheet_id

    @property
    def clear_range(self):
        return self.sheet.pos_clear_content_ui if self.ui else self.sheet.pos_clear_content

    @property
    def update_range(self):
        return self.sheet.pos_update_content_ui if self.ui else self.sheet.pos_update_content


class MetricRegistry:
    """Builds metric jobs from configuration instead of duplicating workflows."""

    def __init__(self, config: Config):
        self._jobs = {
            "sales_traffic": (
                MetricJob("SALES_TRAFFIC_DB", config.sheet("sales_traffic"),
                        schema.SALES_TRAFFIC_EXPECTED_COLUMNS),
                MetricJob("SALES_TRAFFIC_AUTOMATED", config.sheet("sales_traffic"),
                        schema.SALES_TRAFFIC_EXPECTED_COLUMNS_UI, ui=True),
            ),
            "sales_affiliate": (
                MetricJob("SALES_AFFILIATE_DB", config.sheet("sales_affiliate"),
                        schema.AFFILIATE_EXPECTED_COLUMNS),
            ),
            "product": (
                MetricJob("PRODUCT_DB", config.sheet("product"),
                        schema.PRODUCT_EXPECTED_COLUMNS),
            ),
            "media": (
                MetricJob("MEDIA_DB", config.sheet("media"),
                        schema.MEDIA_EXPECTED_COLUMNS),
                MetricJob("MEDIA_AUTOMATED", config.sheet("media"),
                        schema.MEDIA_EXPECTED_COLUMNS_UI, ui=True),
            ),
            "content": (
                MetricJob("CONTENT_DB", config.sheet("content"),
                        schema.CONTENT_EXPECTED_COLUMNS),
            ),
        }

    @property
    def metrics(self) -> tuple[str, ...]:
        return tuple(self._jobs)

    def jobs_for(self, metric: str) -> tuple[MetricJob, ...]:
        try:
            return self._jobs[metric]
        except KeyError as exc:
            raise ValueError(
                f"Unavailable metric '{metric}'. "
                f"Available metrics: {', '.join(self.metrics)}"
            ) from exc