import asyncio
import time
from typing import Callable, List, Optional

from src.config.settings import Config, FetchResult
from src.infrastructure.database.connection import DatabaseClient


class DataExtractor:
    """Orchestrate data extraction from multiple clients"""

    def __init__(self):
        self.config = Config
        self.db_client = DatabaseClient(self.config)

    async def fetch_all_queries(
        self,
        db_conf: dict,
        queries: List,
        seller_ids: List[str] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> FetchResult:
        """
        Fetch data from multiple queries in a single database (async)

        Args:
            db_conf: Database config (chỉ 1 DB)
            queries: List of (name, sql)

        Returns:
            FetchResult
        """
        print(f"\n\033[94m[PROCESS]\033[0m Running {len(queries)} queries (async)...\n")
        
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        start_time = time.time()
        await self.db_client.init_pool(db_conf)
        
        try:
            async def fetch_query_with_progress(name: str, sql: str):
                if progress_callback:
                    progress_callback(name, "running")

                try:
                    result = await self.db_client.fetch_query(
                        db_conf,
                        sql=sql,
                        name=name,
                        semaphore=semaphore,
                    )
                except Exception:
                    if progress_callback:
                        progress_callback(name, "failed")
                    raise

                if progress_callback:
                    progress_callback(name, "empty" if result is None or result.empty else "success")

                return result

            tasks = [
                (name, fetch_query_with_progress(name, sql))
                for name, sql in queries
            ]

            results = await asyncio.gather(
                *[task for _, task in tasks],
                return_exceptions=True
            )

            duration = time.time() - start_time

            dataframes = []
            success = []
            empty = []
            failed = []

            for (name, _), result in zip(tasks, results):

                if isinstance(result, Exception):
                    failed.append(name)

                elif result is None or result.empty:
                    empty.append(name)

                else:
                    result["table_name"] = name 
                    dataframes.append(result)
                    success.append(name)

            return FetchResult(
                success_clients=success,
                empty_clients=empty,
                failed_clients=failed,
                dataframes=dataframes,
                duration=duration
            )
        
        finally:
            await self.db_client.close_pool()


    async def fetch_all_clients(
            self,
            databases: List[dict],
            sql: str
    ) -> FetchResult:
        """
        Fetch data from all configured database clients

        Args:
            databases: List of database configurations
            sql: SQL query to execute

        Returns:
            FetchResult containing all results and metadata
        """
        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        # Create tasks
        tasks = [
            (db.get("client", "unknown"), self.db_client.fetch_data(db, sql, semaphore))
            for db in databases
        ]

        print(f"\n\033[94m[PROCESS]\033[0m Starting async fetch for {len(tasks)} clients (max {self.config.max_concurrent} concurrent)...\n")

        start_time = time.time()

        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[task for _, task in tasks],
            return_exceptions=True
        )

        duration = time.time() - start_time

        # Categorize results
        dataframes = []
        success_clients = []
        empty_clients = []
        failed_clients = []

        for (client, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                failed_clients.append(client)
                print(f"\033[91m[ERROR]\033[0m [{client}] FAILED: {result}")
            elif result is None:
                empty_clients.append(client)
            else:
                dataframes.append(result)
                success_clients.append(client)

        return FetchResult(
            success_clients=success_clients,
            empty_clients=empty_clients,
            failed_clients=failed_clients,
            dataframes=dataframes,
            duration=duration
        )
